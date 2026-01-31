import boto3, os, time, subprocess, datetime, pytz, croniter, asyncio, logging, uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json
from enum import Enum
from dataclasses import dataclass, field
import threading
from contextlib import asynccontextmanager

# Enhanced structured logging configuration
import logging.config

def configure_structured_logging():
    """Configure enhanced structured logging with context"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(message)s'
    )
    
    # Configure structlog with enhanced processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_correlation_id,
            add_service_context,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries"""
    # Try to get correlation ID from context or generate one
    correlation_id = event_dict.get('correlation_id')
    if not correlation_id:
        # Check if we're in a scaling operation context
        import threading
        thread_local = getattr(threading.current_thread(), 'correlation_id', None)
        if thread_local:
            correlation_id = thread_local
        else:
            correlation_id = str(uuid.uuid4())[:8]  # Short correlation ID
    
    event_dict['correlation_id'] = correlation_id
    return event_dict

def add_service_context(logger, method_name, event_dict):
    """Add service context information to log entries"""
    event_dict.update({
        'service': 'namespace-controller',
        'version': os.environ.get('SERVICE_VERSION', '1.0.0'),
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'cluster': os.environ.get('CLUSTER_NAME', 'unknown'),
        'node': os.environ.get('NODE_NAME', 'unknown')
    })
    return event_dict

# Configure logging at module level
logger = configure_structured_logging()

class ContextualLogger:
    """Enhanced logger with context management"""
    
    def __init__(self, base_logger=None):
        self.base_logger = base_logger or logger
        self.context = {}
        
    def bind(self, **kwargs):
        """Bind context to logger"""
        new_logger = ContextualLogger(self.base_logger)
        new_logger.context = {**self.context, **kwargs}
        return new_logger
        
    def _log(self, level, message, **kwargs):
        """Internal logging method with context"""
        combined_context = {**self.context, **kwargs}
        getattr(self.base_logger, level)(message, **combined_context)
        
    def debug(self, message, **kwargs):
        self._log('debug', message, **kwargs)
        
    def info(self, message, **kwargs):
        self._log('info', message, **kwargs)
        
    def warning(self, message, **kwargs):
        self._log('warning', message, **kwargs)
        
    def error(self, message, **kwargs):
        self._log('error', message, **kwargs)
        
    def critical(self, message, **kwargs):
        self._log('critical', message, **kwargs)

class OperationLogger:
    """Logger for tracking operations with automatic timing and context"""
    
    def __init__(self, operation_name: str, namespace: str = None, **context):
        self.operation_name = operation_name
        self.namespace = namespace
        self.context = context
        self.start_time = None
        self.correlation_id = str(uuid.uuid4())
        self.logger = ContextualLogger().bind(
            operation=operation_name,
            namespace=namespace,
            correlation_id=self.correlation_id,
            **context
        )
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation_name}")
        
        # Set correlation ID in thread local for other log entries
        import threading
        threading.current_thread().correlation_id = self.correlation_id
        
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed {self.operation_name}", 
                           duration=duration, 
                           status="success")
        else:
            self.logger.error(f"Failed {self.operation_name}", 
                            duration=duration, 
                            status="error",
                            error_type=exc_type.__name__,
                            error_message=str(exc_val))
        
        # Clear correlation ID from thread local
        import threading
        if hasattr(threading.current_thread(), 'correlation_id'):
            delattr(threading.current_thread(), 'correlation_id')
        
        return False  # Don't suppress exceptions

# Enhanced Prometheus Metrics
scaling_operations = Counter(
    'namespace_scaling_operations_total',
    'Total namespace scaling operations',
    ['namespace', 'operation', 'status']
)

scaling_duration = Histogram(
    'namespace_scaling_duration_seconds',
    'Time spent scaling namespaces',
    ['namespace', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

active_namespaces = Gauge(
    'namespace_active_count',
    'Number of active namespaces'
)

controller_errors = Counter(
    'controller_errors_total',
    'Total controller errors',
    ['error_type']
)

# New comprehensive metrics
dynamodb_operations = Counter(
    'dynamodb_operations_total',
    'Total DynamoDB operations',
    ['operation', 'status', 'table']
)

dynamodb_latency = Histogram(
    'dynamodb_operation_duration_seconds',
    'DynamoDB operation latency',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

kubernetes_api_calls = Counter(
    'kubernetes_api_calls_total',
    'Total Kubernetes API calls',
    ['operation', 'status', 'resource']
)

kubernetes_api_latency = Histogram(
    'kubernetes_api_duration_seconds',
    'Kubernetes API call latency',
    ['operation', 'resource'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)',
    ['service']
)

circuit_breaker_failures = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['service']
)

rollback_operations = Counter(
    'rollback_operations_total',
    'Total rollback operations',
    ['namespace', 'status', 'trigger']
)

cost_savings_estimate = Gauge(
    'cost_savings_estimate_usd_monthly',
    'Estimated monthly cost savings in USD',
    ['namespace', 'business_unit']
)

deployment_replicas = Gauge(
    'deployment_replicas_current',
    'Current number of replicas per deployment',
    ['namespace', 'deployment']
)

deployment_replicas_original = Gauge(
    'deployment_replicas_original',
    'Original number of replicas before scaling',
    ['namespace', 'deployment']
)

schedule_execution_time = Histogram(
    'schedule_execution_duration_seconds',
    'Time spent executing scheduled operations',
    ['namespace'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

health_check_status = Gauge(
    'health_check_status',
    'Health check status (1=healthy, 0=unhealthy)',
    ['component']
)

memory_usage = Gauge(
    'controller_memory_usage_bytes',
    'Controller memory usage in bytes'
)

cpu_usage = Gauge(
    'controller_cpu_usage_percent',
    'Controller CPU usage percentage'
)

cache_operations = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status']
)

pending_operations = Gauge(
    'pending_operations_count',
    'Number of pending operations in queue'
)

# Configuración
aws_region = os.environ.get('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'NamespaceSchedules'))
tz = pytz.timezone(os.environ.get('TIMEZONE', 'UTC'))

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout: int = 60
    half_open_max_calls: int = 3

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        self.half_open_calls = 0
        self._lock = threading.Lock()
        
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if time.time() - self.last_failure_time > self.config.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")
                    
            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError("Circuit breaker HALF_OPEN call limit exceeded")
                self.half_open_calls += 1
                
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
            
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self.failure_count = 0
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                logger.info("Circuit breaker closed after successful recovery")
            
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                logger.error("Circuit breaker opened during half-open state")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                
    @property
    def is_open(self) -> bool:
        return self.state == CircuitBreakerState.OPEN
        
    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitBreakerState.HALF_OPEN

@dataclass
class DeploymentState:
    name: str
    replicas: int
    namespace: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class RollbackData:
    namespace: str
    deployments: List[DeploymentState]
    timestamp: str
    operation_id: str

@dataclass
class RollbackTrigger:
    trigger_type: str  # "repeated_failures", "health_check_failure", "manual"
    threshold: int = 0
    description: str = ""

class EnhancedRollbackManager(RollbackManager):
    """Enhanced rollback manager with automatic triggers and notifications"""
    
    def __init__(self):
        super().__init__()
        self.rollback_triggers = {
            'repeated_failures': RollbackTrigger(
                trigger_type='repeated_failures',
                threshold=2,
                description='Multiple consecutive scaling failures'
            ),
            'health_check_failure': RollbackTrigger(
                trigger_type='health_check_failure', 
                threshold=3,
                description='Health check failures after scaling'
            )
        }
        self.health_check_failures = {}
        self.rollback_in_progress = set()
        self.notification_channels = []
        
    def add_notification_channel(self, channel_func):
        """Add a notification channel for rollback events"""
        self.notification_channels.append(channel_func)
        
    def notify_rollback_event(self, namespace: str, event_type: str, details: Dict):
        """Send notifications about rollback events"""
        message = {
            'namespace': namespace,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details
        }
        
        for channel in self.notification_channels:
            try:
                channel(message)
            except Exception as e:
                self.logger.warning("Failed to send rollback notification", 
                                  channel=str(channel), error=str(e))
    
    def check_health_after_scaling(self, namespace: str, operation_id: str) -> bool:
        """Check namespace health after scaling operation"""
        with OperationLogger("health_check_after_scaling", namespace=namespace) as op_logger:
            try:
                # Wait a bit for deployments to stabilize
                time.sleep(30)
                
                # Check if deployments are ready
                result = subprocess.check_output([
                    "kubectl", "get", "deploy", "-n", namespace,
                    "-o", "jsonpath={range .items[*]}{.metadata.name},{.status.readyReplicas},{.spec.replicas}{\"\\n\"}{end}"
                ], timeout=30)
                
                deployments_healthy = True
                total_deployments = 0
                ready_deployments = 0
                
                for dep_info in result.decode().strip().split('\n'):
                    if dep_info:
                        parts = dep_info.split(',')
                        if len(parts) >= 3:
                            name, ready_str, desired_str = parts[:3]
                            ready = int(ready_str) if ready_str else 0
                            desired = int(desired_str) if desired_str else 0
                            
                            total_deployments += 1
                            if ready == desired and desired > 0:
                                ready_deployments += 1
                            elif desired > 0:  # Only consider unhealthy if we expect replicas
                                deployments_healthy = False
                                op_logger.warning("Deployment not ready", 
                                                deployment=name, 
                                                ready=ready, 
                                                desired=desired)
                
                op_logger.info("Health check completed", 
                             healthy=deployments_healthy,
                             ready_deployments=ready_deployments,
                             total_deployments=total_deployments)
                
                if not deployments_healthy:
                    self.health_check_failures[namespace] = self.health_check_failures.get(namespace, 0) + 1
                    
                    # Check if we should trigger rollback
                    if self.health_check_failures[namespace] >= self.rollback_triggers['health_check_failure'].threshold:
                        op_logger.warning("Health check failure threshold reached, triggering rollback",
                                        failure_count=self.health_check_failures[namespace])
                        
                        self.trigger_automatic_rollback(
                            namespace, 
                            'health_check_failure',
                            {
                                'operation_id': operation_id,
                                'failure_count': self.health_check_failures[namespace],
                                'ready_deployments': ready_deployments,
                                'total_deployments': total_deployments
                            }
                        )
                else:
                    # Reset failure count on success
                    self.health_check_failures[namespace] = 0
                
                return deployments_healthy
                
            except Exception as e:
                op_logger.error("Health check failed", error_details=str(e))
                return False
    
    def trigger_automatic_rollback(self, namespace: str, trigger_type: str, context: Dict) -> bool:
        """Trigger automatic rollback with notifications"""
        if namespace in self.rollback_in_progress:
            self.logger.warning("Rollback already in progress", namespace=namespace)
            return False
            
        self.rollback_in_progress.add(namespace)
        
        try:
            # Send pre-rollback notification
            self.notify_rollback_event(namespace, 'rollback_triggered', {
                'trigger_type': trigger_type,
                'trigger_description': self.rollback_triggers[trigger_type].description,
                'context': context
            })
            
            # Perform rollback
            rollback_success = self.rollback(namespace)
            
            # Send post-rollback notification
            self.notify_rollback_event(namespace, 'rollback_completed', {
                'success': rollback_success,
                'trigger_type': trigger_type,
                'context': context
            })
            
            if rollback_success:
                # Block new operations temporarily
                self.block_operations(namespace, duration_minutes=10)
                
            return rollback_success
            
        finally:
            self.rollback_in_progress.discard(namespace)
    
    def block_operations(self, namespace: str, duration_minutes: int = 10):
        """Block new scaling operations for a namespace temporarily"""
        # This would integrate with the main controller to prevent operations
        # For now, we'll just log the intent
        self.logger.info("Blocking operations temporarily", 
                        namespace=namespace, 
                        duration_minutes=duration_minutes)
        
        # In a real implementation, this would set a flag that the controller checks
        # before performing scaling operations
    
    def is_rollback_in_progress(self, namespace: str) -> bool:
        """Check if rollback is currently in progress for a namespace"""
        return namespace in self.rollback_in_progress
    
    def get_rollback_statistics(self) -> Dict:
        """Get rollback statistics for monitoring"""
        return {
            'total_rollbacks': len(self.rollback_history),
            'rollbacks_in_progress': len(self.rollback_in_progress),
            'health_check_failures': dict(self.health_check_failures),
            'notification_channels': len(self.notification_channels)
        }
    def __init__(self):
        self.rollback_history: Dict[str, RollbackData] = {}
        self._lock = threading.Lock()
        self.logger = ContextualLogger().bind(component="rollback_manager")
        
    def save_state(self, namespace: str, deployments: List[Dict]) -> str:
        """Save deployment state before scaling operation"""
        operation_id = str(uuid.uuid4())
        
        deployment_states = [
            DeploymentState(
                name=dep['name'],
                replicas=dep['replicas'],
                namespace=namespace
            ) for dep in deployments
        ]
        
        rollback_data = RollbackData(
            namespace=namespace,
            deployments=deployment_states,
            timestamp=datetime.utcnow().isoformat(),
            operation_id=operation_id
        )
        
        with self._lock:
            self.rollback_history[namespace] = rollback_data
            
        self.logger.info("State saved for rollback", 
                        namespace=namespace, 
                        deployments_count=len(deployments),
                        operation_id=operation_id,
                        total_replicas=sum(dep['replicas'] for dep in deployments))
        return operation_id
        
    def rollback(self, namespace: str) -> bool:
        """Restore previous deployment state"""
        with OperationLogger("rollback_namespace", namespace=namespace) as op_logger:
            with self._lock:
                rollback_data = self.rollback_history.get(namespace)
                
            if not rollback_data:
                op_logger.error("No rollback data available")
                return False
                
            try:
                op_logger.info("Starting rollback operation", 
                             operation_id=rollback_data.operation_id,
                             deployments_count=len(rollback_data.deployments),
                             saved_at=rollback_data.timestamp)
                
                for deployment in rollback_data.deployments:
                    op_logger.debug("Restoring deployment", 
                                  deployment_name=deployment.name,
                                  target_replicas=deployment.replicas)
                    
                    subprocess.run([
                        "kubectl", "scale", "deploy", deployment.name, 
                        "-n", namespace, f"--replicas={deployment.replicas}"
                    ], check=True, timeout=30)
                    
                op_logger.info("Rollback completed successfully", 
                             operation_id=rollback_data.operation_id)
                return True
                
            except subprocess.TimeoutExpired:
                op_logger.error("Rollback timed out")
                return False
            except subprocess.CalledProcessError as e:
                op_logger.error("Rollback command failed", 
                              error_details=str(e),
                              return_code=e.returncode)
                return False
            except Exception as e:
                op_logger.error("Unexpected rollback error", 
                              error_details=str(e))
                return False
            
    def get_rollback_history(self, namespace: str) -> Optional[RollbackData]:
        """Get rollback history for a namespace"""
        with self._lock:
            return self.rollback_history.get(namespace)
            
    def clear_history(self, namespace: str) -> bool:
        """Clear rollback history for a namespace"""
        with self._lock:
            if namespace in self.rollback_history:
                del self.rollback_history[namespace]
                self.logger.info("Rollback history cleared", namespace=namespace)
                return True
            return False

class PrometheusMetrics:
    """Comprehensive Prometheus metrics management"""
    
    def __init__(self):
        self.scaling_operations = scaling_operations
        self.scaling_duration = scaling_duration
        self.active_namespaces = active_namespaces
        self.controller_errors = controller_errors
        self.dynamodb_operations = dynamodb_operations
        self.dynamodb_latency = dynamodb_latency
        self.kubernetes_api_calls = kubernetes_api_calls
        self.kubernetes_api_latency = kubernetes_api_latency
        self.circuit_breaker_state = circuit_breaker_state
        self.circuit_breaker_failures = circuit_breaker_failures
        self.rollback_operations = rollback_operations
        self.cost_savings_estimate = cost_savings_estimate
        self.deployment_replicas = deployment_replicas
        self.deployment_replicas_original = deployment_replicas_original
        self.schedule_execution_time = schedule_execution_time
        self.health_check_status = health_check_status
        self.memory_usage = memory_usage
        self.cpu_usage = cpu_usage
        self.cache_operations = cache_operations
        self.pending_operations = pending_operations
        
        # Initialize health check metrics
        self._initialize_health_metrics()
        
    def _initialize_health_metrics(self):
        """Initialize health check metrics"""
        components = ['dynamodb', 'kubernetes', 'controller', 'circuit_breaker']
        for component in components:
            self.health_check_status.labels(component=component).set(1)
    
    def record_scaling_operation(self, namespace: str, operation: str, status: str, duration: float):
        """Record scaling operation metrics"""
        self.scaling_operations.labels(
            namespace=namespace, 
            operation=operation, 
            status=status
        ).inc()
        
        if status == "success":
            self.scaling_duration.labels(
                namespace=namespace, 
                operation=operation
            ).observe(duration)
    
    def record_dynamodb_operation(self, operation: str, table: str, status: str, duration: float):
        """Record DynamoDB operation metrics"""
        self.dynamodb_operations.labels(
            operation=operation,
            status=status,
            table=table
        ).inc()
        
        if status == "success":
            self.dynamodb_latency.labels(
                operation=operation,
                table=table
            ).observe(duration)
    
    def record_kubernetes_operation(self, operation: str, resource: str, status: str, duration: float):
        """Record Kubernetes API operation metrics"""
        self.kubernetes_api_calls.labels(
            operation=operation,
            status=status,
            resource=resource
        ).inc()
        
        if status == "success":
            self.kubernetes_api_latency.labels(
                operation=operation,
                resource=resource
            ).observe(duration)
    
    def update_circuit_breaker_state(self, service: str, state: CircuitBreakerState):
        """Update circuit breaker state metrics"""
        state_value = {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.HALF_OPEN: 1,
            CircuitBreakerState.OPEN: 2
        }
        self.circuit_breaker_state.labels(service=service).set(state_value[state])
    
    def record_circuit_breaker_failure(self, service: str):
        """Record circuit breaker failure"""
        self.circuit_breaker_failures.labels(service=service).inc()
    
    def record_rollback_operation(self, namespace: str, status: str, trigger: str):
        """Record rollback operation"""
        self.rollback_operations.labels(
            namespace=namespace,
            status=status,
            trigger=trigger
        ).inc()
    
    def update_cost_savings(self, namespace: str, business_unit: str, savings: float):
        """Update cost savings estimate"""
        self.cost_savings_estimate.labels(
            namespace=namespace,
            business_unit=business_unit or "unknown"
        ).set(savings)
    
    def update_deployment_replicas(self, namespace: str, deployment: str, 
                                 current_replicas: int, original_replicas: int = None):
        """Update deployment replica metrics"""
        self.deployment_replicas.labels(
            namespace=namespace,
            deployment=deployment
        ).set(current_replicas)
        
        if original_replicas is not None:
            self.deployment_replicas_original.labels(
                namespace=namespace,
                deployment=deployment
            ).set(original_replicas)
    
    def record_schedule_execution(self, namespace: str, duration: float):
        """Record schedule execution time"""
        self.schedule_execution_time.labels(namespace=namespace).observe(duration)
    
    def update_health_status(self, component: str, is_healthy: bool):
        """Update component health status"""
        self.health_check_status.labels(component=component).set(1 if is_healthy else 0)
    
    def update_resource_usage(self, memory_bytes: int, cpu_percent: float):
        """Update resource usage metrics"""
        self.memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
    
    def record_cache_operation(self, operation: str, status: str):
        """Record cache operation"""
        self.cache_operations.labels(operation=operation, status=status).inc()
    
    def update_pending_operations(self, count: int):
        """Update pending operations count"""
        self.pending_operations.set(count)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics for debugging"""
        return {
            'scaling_operations': self.scaling_operations._value._value,
            'active_namespaces': self.active_namespaces._value._value,
            'controller_errors': self.controller_errors._value._value,
            'circuit_breaker_states': {
                family.name: {sample.labels['service']: sample.value 
                            for sample in family.samples}
                for family in [self.circuit_breaker_state]
            }
        }

@dataclass
class RetryConfig:
    max_attempts: int = 3
    min_wait: int = 1
    max_wait: int = 10
    multiplier: int = 2

class GracefulDegradationManager:
    def __init__(self):
        self.fallback_strategies = {
            'dynamodb': self._dynamodb_fallback,
            'kubernetes': self._kubernetes_fallback,
            'prometheus': self._prometheus_fallback
        }
        self.local_cache = {}
        
    def _dynamodb_fallback(self, operation: str, *args, **kwargs):
        """Fallback strategy for DynamoDB failures"""
        logger.warning("Using DynamoDB fallback strategy", operation=operation)
        
        if operation == 'scan':
            # Return cached schedules if available
            cached_schedules = self.local_cache.get('schedules', [])
            logger.info("Using cached schedules", count=len(cached_schedules))
            return {'Items': cached_schedules}
        elif operation == 'put_item':
            # Cache the item locally for later sync
            item = kwargs.get('Item', {})
            if 'schedules' not in self.local_cache:
                self.local_cache['schedules'] = []
            self.local_cache['schedules'].append(item)
            logger.info("Cached schedule locally", namespace=item.get('namespace'))
            return True
        
        return None
        
    def _kubernetes_fallback(self, operation: str, *args, **kwargs):
        """Fallback strategy for Kubernetes API failures"""
        logger.warning("Using Kubernetes fallback strategy", operation=operation)
        
        if operation == 'get_namespaces':
            # Return cached namespaces
            cached_namespaces = self.local_cache.get('namespaces', [])
            logger.info("Using cached namespaces", count=len(cached_namespaces))
            return cached_namespaces
        elif operation == 'scale_deployment':
            # Queue operation for later execution
            if 'pending_operations' not in self.local_cache:
                self.local_cache['pending_operations'] = []
            
            operation_data = {
                'type': 'scale',
                'namespace': args[0] if args else kwargs.get('namespace'),
                'replicas': args[1] if len(args) > 1 else kwargs.get('replicas'),
                'timestamp': datetime.utcnow().isoformat()
            }
            self.local_cache['pending_operations'].append(operation_data)
            logger.info("Queued scaling operation", **operation_data)
            return True
            
        return None
        
    def _prometheus_fallback(self, operation: str, *args, **kwargs):
        """Fallback strategy for Prometheus failures"""
        logger.warning("Using Prometheus fallback strategy", operation=operation)
        # Continue without metrics collection
        return True

def slack_notification_channel(message: Dict):
    """Send rollback notification to Slack"""
    try:
        slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
        if not slack_webhook:
            return
            
        import requests
        
        color = "danger" if message['event_type'] == 'rollback_triggered' else "good"
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"Namespace Rollback: {message['namespace']}",
                "fields": [
                    {
                        "title": "Event",
                        "value": message['event_type'].replace('_', ' ').title(),
                        "short": True
                    },
                    {
                        "title": "Timestamp", 
                        "value": message['timestamp'],
                        "short": True
                    },
                    {
                        "title": "Details",
                        "value": str(message['details']),
                        "short": False
                    }
                ]
            }]
        }
        
        response = requests.post(slack_webhook, json=payload, timeout=10)
        response.raise_for_status()
        
    except Exception as e:
        logger.warning("Failed to send Slack notification", error=str(e))

def email_notification_channel(message: Dict):
    """Send rollback notification via email"""
    try:
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        notification_email = os.environ.get('NOTIFICATION_EMAIL')
        
        if not all([smtp_server, smtp_user, smtp_password, notification_email]):
            return
            
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = notification_email
        msg['Subject'] = f"Namespace Rollback Alert: {message['namespace']}"
        
        body = f"""
        Namespace: {message['namespace']}
        Event: {message['event_type'].replace('_', ' ').title()}
        Timestamp: {message['timestamp']}
        
        Details:
        {message['details']}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
    except Exception as e:
        logger.warning("Failed to send email notification", error=str(e))

def kubernetes_event_notification_channel(message: Dict):
    """Create Kubernetes event for rollback"""
    try:
        subprocess.run([
            "kubectl", "create", "event", "-n", message['namespace'],
            "--type=Warning", "--reason=AutoRollback",
            f"Automatic rollback: {message['event_type']} - {message['details']}"
        ], check=True, timeout=15)
        
    except Exception as e:
        logger.warning("Failed to create Kubernetes event", error=str(e))

class NamespaceController:
    def __init__(self, 
                 circuit_breaker_config: CircuitBreakerConfig = None,
                 retry_config: RetryConfig = None):
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
        self.rollback_manager = EnhancedRollbackManager()
        self.degradation_manager = GracefulDegradationManager()
        self.retry_config = retry_config or RetryConfig()
        self.metrics = PrometheusMetrics()
        
        # Enhanced logging
        self.logger = ContextualLogger().bind(component="namespace_controller")
        
        # AWS and Kubernetes clients
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.table = self.dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'NamespaceSchedules'))
        
        # Configuration
        self.timezone = pytz.timezone(os.environ.get('TIMEZONE', 'UTC'))
        self.system_namespaces = set(os.environ.get(
            'SYSTEM_NAMESPACES', 
            'kube-system,kube-public,kube-node-lease,default,argocd,kyverno,encendido-eks,karpenter'
        ).split(','))
        
        # State tracking
        self.last_successful_operation = {}
        self.failure_counts = {}
        self.blocked_operations = {}  # Track temporarily blocked namespaces
        
        # Setup notification channels
        self._setup_notification_channels()
        
        self.logger.info("NamespaceController initialized", 
                        timezone=str(self.timezone),
                        system_namespaces=list(self.system_namespaces),
                        aws_region=self.aws_region,
                        table_name=self.table.name)
    
    def _setup_notification_channels(self):
        """Setup rollback notification channels"""
        self.rollback_manager.add_notification_channel(slack_notification_channel)
        self.rollback_manager.add_notification_channel(email_notification_channel)
        self.rollback_manager.add_notification_channel(kubernetes_event_notification_channel)
        
        self.logger.info("Notification channels configured", 
                        channels=['slack', 'email', 'kubernetes_events'])
    
    def is_operation_blocked(self, namespace: str) -> bool:
        """Check if operations are temporarily blocked for a namespace"""
        if namespace not in self.blocked_operations:
            return False
            
        block_until = self.blocked_operations[namespace]
        if datetime.utcnow() > block_until:
            del self.blocked_operations[namespace]
            self.logger.info("Operation block expired", namespace=namespace)
            return False
            
        return True
    
    def block_operations_temporarily(self, namespace: str, duration_minutes: int = 10):
        """Block operations for a namespace temporarily"""
        block_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.blocked_operations[namespace] = block_until
        
        self.logger.warning("Operations blocked temporarily", 
                          namespace=namespace, 
                          duration_minutes=duration_minutes,
                          blocked_until=block_until.isoformat())
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((subprocess.CalledProcessError, subprocess.TimeoutExpired))
    )
    def get_namespaces(self) -> List[str]:
        """Get list of namespaces excluding system namespaces"""
        with OperationLogger("get_namespaces") as op_logger:
            try:
                result = self.circuit_breaker.call(
                    subprocess.check_output,
                    ["kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"],
                    timeout=30
                )
                
                namespaces = [ns for ns in result.decode().split() if ns not in self.system_namespaces]
                
                # Record successful operation
                duration = time.time() - op_logger.start_time
                self.metrics.record_kubernetes_operation("get_namespaces", "namespace", "success", duration)
                
                # Cache successful result
                self.degradation_manager.local_cache['namespaces'] = namespaces
                self.metrics.active_namespaces.set(len(namespaces))
                
                # Update health status
                self.metrics.update_health_status("kubernetes", True)
                
                op_logger.info("Retrieved namespaces successfully", 
                             count=len(namespaces),
                             namespaces=namespaces[:5])  # Log first 5 for brevity
                return namespaces
                
            except CircuitBreakerOpenError:
                op_logger.warning("Circuit breaker open, using fallback")
                self.metrics.record_kubernetes_operation("get_namespaces", "namespace", "circuit_breaker_open", 0)
                self.metrics.update_health_status("kubernetes", False)
                return self.degradation_manager._kubernetes_fallback('get_namespaces')
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                duration = time.time() - op_logger.start_time
                op_logger.error("Failed to get namespaces", 
                              error_details=str(e),
                              command_timeout=30)
                self.metrics.record_kubernetes_operation("get_namespaces", "namespace", "error", duration)
                self.metrics.update_health_status("kubernetes", False)
                
                # Try fallback
                fallback_result = self.degradation_manager._kubernetes_fallback('get_namespaces')
                if fallback_result is not None:
                    op_logger.info("Using fallback result", count=len(fallback_result))
                    return fallback_result
                raise
    
    def get_deployment_state(self, namespace: str) -> List[Dict]:
        """Get current deployment state in a namespace"""
        with OperationLogger("get_deployment_state", namespace=namespace) as op_logger:
            try:
                result = self.circuit_breaker.call(
                    subprocess.check_output,
                    ["kubectl", "get", "deploy", "-n", namespace, 
                     "-o", "jsonpath={range .items[*]}{.metadata.name},{.spec.replicas}{\"\\n\"}{end}"],
                    timeout=30
                )
                
                deployments = []
                for dep_info in result.decode().strip().split('\n'):
                    if dep_info:
                        name, replicas = dep_info.split(',')
                        replica_count = int(replicas) if replicas else 0
                        deployments.append({
                            'name': name,
                            'replicas': replica_count
                        })
                        
                        # Update deployment replica metrics
                        self.metrics.update_deployment_replicas(namespace, name, replica_count)
                
                # Record successful operation
                duration = time.time() - op_logger.start_time
                self.metrics.record_kubernetes_operation("get_deployments", "deployment", "success", duration)
                
                op_logger.info("Retrieved deployment state successfully", 
                             deployments_count=len(deployments),
                             total_replicas=sum(d['replicas'] for d in deployments))
                return deployments
                
            except CircuitBreakerOpenError:
                op_logger.warning("Circuit breaker open for deployment state")
                self.metrics.record_kubernetes_operation("get_deployments", "deployment", "circuit_breaker_open", 0)
                return []
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                duration = time.time() - op_logger.start_time
                op_logger.error("Failed to get deployment state", 
                              error_details=str(e),
                              command_timeout=30)
                self.metrics.record_kubernetes_operation("get_deployments", "deployment", "error", duration)
                return []
            except Exception as e:
                duration = time.time() - op_logger.start_time
                op_logger.error("Unexpected error getting deployment state", 
                              error_details=str(e))
                self.metrics.record_kubernetes_operation("get_deployments", "deployment", "error", duration)
                return []
    
    def scale_namespace(self, namespace: str, to_zero: bool) -> bool:
        """Scale all deployments in a namespace"""
        action = "shutdown" if to_zero else "startup"
        
        # Check if operations are blocked for this namespace
        if self.is_operation_blocked(namespace):
            self.logger.warning("Scaling operation blocked", 
                              namespace=namespace, 
                              action=action,
                              reason="temporary_block_after_rollback")
            return False
        
        # Check if rollback is in progress
        if self.rollback_manager.is_rollback_in_progress(namespace):
            self.logger.warning("Scaling operation blocked", 
                              namespace=namespace, 
                              action=action,
                              reason="rollback_in_progress")
            return False
        
        with OperationLogger("scale_namespace", namespace=namespace, action=action) as op_logger:
            try:
                # Save state before scaling down
                operation_id = None
                if to_zero:
                    current_state = self.get_deployment_state(namespace)
                    if current_state:
                        operation_id = self.rollback_manager.save_state(namespace, current_state)
                        op_logger.info("State saved for rollback", 
                                     operation_id=operation_id,
                                     deployments_count=len(current_state))
                
                # Perform scaling operation with circuit breaker
                success = self.circuit_breaker.call(
                    self._perform_scaling_operation, 
                    namespace, 
                    to_zero, 
                    op_logger.correlation_id
                )
                
                if success:
                    # Record successful metrics
                    duration = time.time() - op_logger.start_time
                    self.metrics.record_scaling_operation(namespace, action, "success", duration)
                    
                    self.last_successful_operation[namespace] = {
                        'action': action,
                        'timestamp': datetime.utcnow().isoformat(),
                        'correlation_id': op_logger.correlation_id
                    }
                    # Reset failure count on success
                    self.failure_counts[namespace] = 0
                    
                    # Update circuit breaker state metric
                    self.metrics.update_circuit_breaker_state("scaling", self.circuit_breaker.state)
                    
                    # Perform health check after scaling (especially for startup operations)
                    if not to_zero and operation_id:
                        op_logger.info("Scheduling post-scaling health check")
                        # Schedule health check in background
                        threading.Thread(
                            target=self.rollback_manager.check_health_after_scaling,
                            args=(namespace, operation_id),
                            daemon=True
                        ).start()
                    
                    op_logger.info("Scaling operation completed successfully")
                    return True
                else:
                    raise Exception("Scaling operation returned False")
                    
            except CircuitBreakerOpenError:
                op_logger.error("Circuit breaker open, scaling operation blocked")
                self.metrics.record_scaling_operation(namespace, action, "circuit_breaker_open", 0)
                self.metrics.record_circuit_breaker_failure("scaling")
                return False
                
            except Exception as e:
                # Track failures
                self.failure_counts[namespace] = self.failure_counts.get(namespace, 0) + 1
                
                # Record failure metrics
                duration = time.time() - op_logger.start_time
                self.metrics.record_scaling_operation(namespace, action, "error", duration)
                
                op_logger.error("Scaling operation failed", 
                              failure_count=self.failure_counts[namespace],
                              error_details=str(e))
                
                # Attempt rollback if this was a shutdown operation and we have multiple failures
                if to_zero and self.failure_counts[namespace] >= 2:
                    op_logger.warning("Multiple failures detected, triggering automatic rollback", 
                                    failure_count=self.failure_counts[namespace])
                    
                    rollback_success = self.rollback_manager.trigger_automatic_rollback(
                        namespace, 
                        'repeated_failures',
                        {
                            'failure_count': self.failure_counts[namespace],
                            'last_error': str(e),
                            'correlation_id': op_logger.correlation_id
                        }
                    )
                    
                    if rollback_success:
                        # Block operations temporarily after rollback
                        self.block_operations_temporarily(namespace, duration_minutes=10)
                        
                return False
    
    def _perform_scaling_operation(self, namespace: str, to_zero: bool, correlation_id: str) -> bool:
        """Perform the actual scaling operation"""
        action = "Apagado" if to_zero else "Encendido"
        
        try:
            # Get deployments in namespace
            deps_start = time.time()
            deps_result = subprocess.check_output([
                "kubectl", "get", "deploy", "-n", namespace, 
                "-o", "custom-columns=NAME:.metadata.name", "--no-headers"
            ], timeout=30)
            
            deps_duration = time.time() - deps_start
            self.metrics.record_kubernetes_operation("list_deployments", "deployment", "success", deps_duration)
            
            deployments = deps_result.decode().split()
            
            if not deployments:
                logger.info("No deployments found in namespace", namespace=namespace)
                return True
            
            for dep in deployments:
                if to_zero:
                    # Get current replicas
                    get_start = time.time()
                    current_result = subprocess.check_output([
                        "kubectl", "get", "deploy", dep, "-n", namespace, 
                        "-o", "jsonpath={.spec.replicas}"
                    ], timeout=15)
                    
                    get_duration = time.time() - get_start
                    self.metrics.record_kubernetes_operation("get_deployment", "deployment", "success", get_duration)
                    
                    current = current_result.decode().strip()
                    
                    if current and int(current) > 0:
                        original_replicas = int(current)
                        
                        # Annotate with original replicas
                        annotate_start = time.time()
                        subprocess.run([
                            "kubectl", "annotate", "deploy", dep, "-n", namespace, 
                            f"original-replicas={current}", "--overwrite"
                        ], check=True, timeout=15)
                        
                        annotate_duration = time.time() - annotate_start
                        self.metrics.record_kubernetes_operation("annotate_deployment", "deployment", "success", annotate_duration)
                        
                        # Scale to zero
                        scale_start = time.time()
                        subprocess.run([
                            "kubectl", "scale", "deploy", dep, "-n", namespace, "--replicas=0"
                        ], check=True, timeout=30)
                        
                        scale_duration = time.time() - scale_start
                        self.metrics.record_kubernetes_operation("scale_deployment", "deployment", "success", scale_duration)
                        
                        # Update metrics with original and current replicas
                        self.metrics.update_deployment_replicas(namespace, dep, 0, original_replicas)
                        
                        logger.debug("Scaled deployment to zero", 
                                   namespace=namespace, 
                                   deployment=dep, 
                                   original_replicas=current)
                else:
                    # Get original replicas from annotation
                    get_start = time.time()
                    orig_result = subprocess.check_output([
                        "kubectl", "get", "deploy", dep, "-n", namespace, 
                        "-o", "jsonpath={.metadata.annotations.original-replicas}"
                    ], timeout=15)
                    
                    get_duration = time.time() - get_start
                    self.metrics.record_kubernetes_operation("get_deployment", "deployment", "success", get_duration)
                    
                    orig = orig_result.decode().strip()
                    
                    if orig:
                        original_replicas = int(orig)
                        
                        # Scale back to original
                        scale_start = time.time()
                        subprocess.run([
                            "kubectl", "scale", "deploy", dep, "-n", namespace, f"--replicas={orig}"
                        ], check=True, timeout=30)
                        
                        scale_duration = time.time() - scale_start
                        self.metrics.record_kubernetes_operation("scale_deployment", "deployment", "success", scale_duration)
                        
                        # Remove annotation
                        annotate_start = time.time()
                        subprocess.run([
                            "kubectl", "annotate", "deploy", dep, "-n", namespace, "original-replicas-"
                        ], check=True, timeout=15)
                        
                        annotate_duration = time.time() - annotate_start
                        self.metrics.record_kubernetes_operation("annotate_deployment", "deployment", "success", annotate_duration)
                        
                        # Update metrics
                        self.metrics.update_deployment_replicas(namespace, dep, original_replicas)
                        
                        logger.debug("Scaled deployment back to original", 
                                   namespace=namespace, 
                                   deployment=dep, 
                                   replicas=orig)
            
            # Create Kubernetes event
            event_start = time.time()
            subprocess.run([
                "kubectl", "create", "event", "-n", namespace, "--type=Normal", 
                f"--reason=Auto{action}", f"{action} automático - {correlation_id}"
            ], check=True, timeout=15)
            
            event_duration = time.time() - event_start
            self.metrics.record_kubernetes_operation("create_event", "event", "success", event_duration)
            
            return True
            
        except subprocess.TimeoutExpired as e:
            logger.error("Scaling operation timed out", 
                        namespace=namespace, 
                        action=action, 
                        error=str(e))
            self.metrics.record_kubernetes_operation("scale_deployment", "deployment", "timeout", 0)
            return False
            
        except subprocess.CalledProcessError as e:
            logger.error("Kubectl command failed during scaling", 
                        namespace=namespace, 
                        action=action, 
                        error=str(e))
            self.metrics.record_kubernetes_operation("scale_deployment", "deployment", "error", 0)
            return False

# Global controller instance
namespace_controller = NamespaceController()

def scale(ns, to_zero):
    """Legacy wrapper for backward compatibility"""
    return namespace_controller.scale_namespace(ns, to_zero)

def health_check():
    """Health check endpoint"""
    try:
        # Verificar conectividad a DynamoDB
        namespace_controller.table.meta.client.describe_table(TableName=namespace_controller.table.name)
        
        # Verificar conectividad a Kubernetes
        subprocess.check_output(["kubectl", "version", "--client"], timeout=5)
        
        # Verificar estado del circuit breaker
        circuit_breaker_status = {
            'state': namespace_controller.circuit_breaker.state.value,
            'failure_count': namespace_controller.circuit_breaker.failure_count,
            'is_open': namespace_controller.circuit_breaker.is_open
        }
        
        return {
            "status": "healthy", 
            "timestamp": datetime.utcnow().isoformat(),
            "circuit_breaker": circuit_breaker_status,
            "last_successful_operations": namespace_controller.last_successful_operation
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy", 
            "error": str(e), 
            "timestamp": datetime.utcnow().isoformat()
        }

def get_schedules():
    """Obtener todos los horarios configurados"""
    operation_start = time.time()
    
    try:
        response = namespace_controller.table.scan()
        
        # Record successful DynamoDB operation
        duration = time.time() - operation_start
        namespace_controller.metrics.record_dynamodb_operation(
            "scan", namespace_controller.table.name, "success", duration
        )
        namespace_controller.metrics.update_health_status("dynamodb", True)
        
        schedules = []
        
        for item in response['Items']:
            schedule = {
                'id': item.get('schedule_id', item['namespace']),
                'namespace': item['namespace'],
                'enabled': item.get('enabled', True),
                'timezone': item.get('timezone', 'UTC'),
                'startup_time': item.get('startup_time', '08:00'),
                'shutdown_time': item.get('shutdown_time', '17:00'),
                'days_of_week': item.get('days_of_week', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']),
                'metadata': item.get('metadata', {}),
                'created_at': item.get('created_at', ''),
                'updated_at': item.get('updated_at', '')
            }
            schedules.append(schedule)
            
            # Update cost savings metrics if available
            metadata = item.get('metadata', {})
            if 'cost_savings_target' in metadata:
                namespace_controller.metrics.update_cost_savings(
                    item['namespace'],
                    metadata.get('business_unit', 'unknown'),
                    float(metadata['cost_savings_target'])
                )
            
        return schedules
    except Exception as e:
        duration = time.time() - operation_start
        logger.error("Error getting schedules", error=str(e))
        namespace_controller.metrics.record_dynamodb_operation(
            "scan", namespace_controller.table.name, "error", duration
        )
        namespace_controller.metrics.update_health_status("dynamodb", False)
        return []

def create_schedule(schedule_data):
    """Crear un nuevo horario"""
    operation_start = time.time()
    
    try:
        schedule_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        item = {
            'namespace': schedule_data['namespace'],
            'schedule_id': schedule_id,
            'enabled': schedule_data.get('enabled', True),
            'timezone': schedule_data.get('timezone', 'UTC'),
            'startup_time': schedule_data['startup_time'],
            'shutdown_time': schedule_data['shutdown_time'],
            'days_of_week': schedule_data['days_of_week'],
            'metadata': schedule_data.get('metadata', {}),
            'created_at': now,
            'updated_at': now
        }
        
        namespace_controller.table.put_item(Item=item)
        
        # Record successful DynamoDB operation
        duration = time.time() - operation_start
        namespace_controller.metrics.record_dynamodb_operation(
            "put_item", namespace_controller.table.name, "success", duration
        )
        
        # Update cost savings metrics if provided
        metadata = schedule_data.get('metadata', {})
        if 'cost_savings_target' in metadata:
            namespace_controller.metrics.update_cost_savings(
                schedule_data['namespace'],
                metadata.get('business_unit', 'unknown'),
                float(metadata['cost_savings_target'])
            )
        
        logger.info("Schedule created", namespace=schedule_data['namespace'], schedule_id=schedule_id)
        
        return {**item, 'id': schedule_id}
    except Exception as e:
        duration = time.time() - operation_start
        logger.error("Error creating schedule", error=str(e))
        namespace_controller.metrics.record_dynamodb_operation(
            "put_item", namespace_controller.table.name, "error", duration
        )
        raise e

def get_namespaces_list():
    """Obtener lista de namespaces disponibles"""
    try:
        return namespace_controller.get_namespaces()
    except Exception as e:
        logger.error("Error getting namespaces", error=str(e))
        return []

def update_resource_metrics():
    """Update controller resource usage metrics"""
    try:
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Memory usage in bytes
        memory_info = process.memory_info()
        namespace_controller.metrics.update_resource_usage(
            memory_info.rss,  # Resident Set Size
            process.cpu_percent()
        )
        
    except ImportError:
        # psutil not available, skip resource monitoring
        pass
    except Exception as e:
        logger.warning("Failed to update resource metrics", error=str(e))

def main():
    """Función principal del controlador"""
    # Iniciar servidor de métricas
    start_http_server(8080)
    logger.info("Started Prometheus metrics server on port 8080")
    
    # Agregar endpoint de health check
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    import json
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                health = health_check()
                self.send_response(200 if health["status"] == "healthy" else 503)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(health).encode())
            elif self.path == '/api/schedules':
                schedules = get_schedules()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(schedules).encode())
            elif self.path == '/api/namespaces':
                namespaces = get_namespaces_list()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(namespaces).encode())
            elif self.path == '/metrics':
                # Prometheus metrics ya están en el puerto 8080
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'# Metrics available on port 8080')
            elif self.path == '/' or self.path == '/frontend':
                # Servir la página del frontend
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html_content = self.get_frontend_html()
                self.wfile.write(html_content.encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_POST(self):
            if self.path == '/api/schedules':
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    schedule_data = json.loads(post_data.decode('utf-8'))
                    
                    new_schedule = create_schedule(schedule_data)
                    
                    self.send_response(201)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(new_schedule).encode())
                except Exception as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_response = {"error": str(e)}
                    self.wfile.write(json.dumps(error_response).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_OPTIONS(self):
            # Manejar preflight requests para CORS
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        
        def get_frontend_html(self):
            return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Namespace Encendido EKS</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Roboto', sans-serif; background-color: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1976d2, #42a5f5); color: white; padding: 30px 20px; border-radius: 12px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h2 { color: #1976d2; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1976d2; }
        .stat-number { font-size: 2.5rem; font-weight: bold; color: #1976d2; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9rem; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; color: #333; }
        .form-group input, .form-group select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; transition: border-color 0.3s; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #1976d2; }
        .days-selector { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
        .day-chip { padding: 8px 16px; border: 2px solid #e0e0e0; border-radius: 20px; cursor: pointer; transition: all 0.3s; font-size: 0.9rem; }
        .day-chip.active { background-color: #1976d2; color: white; border-color: #1976d2; }
        .day-chip:hover { border-color: #1976d2; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background-color: #1976d2; color: white; }
        .btn-primary:hover { background-color: #1565c0; }
        .schedule-list { margin-top: 20px; }
        .schedule-item { background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #1976d2; }
        .schedule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .schedule-title { font-weight: 500; font-size: 1.1rem; }
        .schedule-status { padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 500; }
        .status-active { background-color: #e8f5e8; color: #2e7d32; }
        .status-inactive { background-color: #ffebee; color: #d32f2f; }
        .status-paused { background-color: #fff3e0; color: #f57c00; }
        .schedule-details { color: #666; font-size: 0.9rem; line-height: 1.4; }
        .material-icons { font-size: 1.2rem; }
        .alert { padding: 16px; border-radius: 8px; margin-bottom: 20px; }
        .alert-success { background-color: #e8f5e8; color: #2e7d32; border-left: 4px solid #2e7d32; }
        .alert-error { background-color: #ffebee; color: #d32f2f; border-left: 4px solid #d32f2f; }
        @media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } .stats-grid { grid-template-columns: 1fr; } .header h1 { font-size: 2rem; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎛️ Namespace Encendido EKS</h1>
            <p>Sistema de apagado automático de namespaces para optimización de costos</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-schedules">0</div>
                <div class="stat-label">Horarios Configurados</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-schedules">0</div>
                <div class="stat-label">Horarios Activos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="running-namespaces">0</div>
                <div class="stat-label">Namespaces Encendidos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="estimated-savings">$0</div>
                <div class="stat-label">Ahorro Estimado/mes</div>
            </div>
        </div>

        <div class="form-grid">
            <div class="card">
                <h2><span class="material-icons">schedule</span> Crear Nuevo Horario</h2>
                <div id="alert-container"></div>
                <form id="schedule-form">
                    <div class="form-group">
                        <label for="namespace">Namespace</label>
                        <select id="namespace" required>
                            <option value="">Seleccionar namespace...</option>
                            <option value="production-app">production-app</option>
                            <option value="staging-app">staging-app</option>
                            <option value="development-app">development-app</option>
                            <option value="testing-app">testing-app</option>
                            <option value="demo-app">demo-app</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="timezone">Zona Horaria</label>
                        <select id="timezone">
                            <option value="America/Bogota">Colombia (UTC-5)</option>
                            <option value="UTC">UTC</option>
                            <option value="America/New_York">New York (UTC-5)</option>
                            <option value="Europe/Madrid">Madrid (UTC+1)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="startup-time">🟢 Hora de Encendido</label>
                        <input type="time" id="startup-time" value="08:00" required>
                    </div>
                    <div class="form-group">
                        <label for="shutdown-time">🔴 Hora de Apagado</label>
                        <input type="time" id="shutdown-time" value="17:00" required>
                    </div>
                    <div class="form-group">
                        <label>📅 Días de la Semana</label>
                        <div class="days-selector">
                            <div class="day-chip active" data-day="monday">L - Lunes</div>
                            <div class="day-chip active" data-day="tuesday">M - Martes</div>
                            <div class="day-chip active" data-day="wednesday">X - Miércoles</div>
                            <div class="day-chip active" data-day="thursday">J - Jueves</div>
                            <div class="day-chip active" data-day="friday">V - Viernes</div>
                            <div class="day-chip" data-day="saturday">S - Sábado</div>
                            <div class="day-chip" data-day="sunday">D - Domingo</div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="business-unit">Unidad de Negocio</label>
                        <input type="text" id="business-unit" placeholder="Ej: Engineering, Marketing">
                    </div>
                    <div class="form-group">
                        <label for="cost-target">Meta de Ahorro (USD/mes)</label>
                        <input type="number" id="cost-target" placeholder="1000">
                    </div>
                    <button type="submit" class="btn btn-primary">
                        <span class="material-icons">add</span> Crear Horario
                    </button>
                </form>
            </div>

            <div class="card">
                <h2><span class="material-icons">list</span> Horarios Configurados</h2>
                <div class="schedule-list" id="schedule-list">
                    <p style="text-align: center; color: #666; padding: 20px;">
                        No hay horarios configurados aún.<br>
                        <small>Crea tu primer horario usando el formulario de la izquierda.</small>
                    </p>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>
                <span class="material-icons">refresh</span> Estado en Tiempo Real
                <span style="margin-left: auto; font-size: 0.9rem; font-weight: normal; color: #666;">
                    <span id="current-time"></span> COT
                </span>
            </h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" style="color: #2e7d32;">0</div>
                    <div class="stat-label">Namespaces Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #1976d2;">0</div>
                    <div class="stat-label">Réplicas Totales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #f57c00;">0</div>
                    <div class="stat-label">Horarios Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #d32f2f;">0</div>
                    <div class="stat-label">Namespaces Apagados</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let schedules = [];
        
        // Cargar datos iniciales
        async function loadData() {
            try {
                // Cargar horarios
                const schedulesResponse = await fetch('/api/schedules');
                schedules = await schedulesResponse.json();
                updateSchedulesList();
                updateStats();
                
                // Cargar namespaces
                const namespacesResponse = await fetch('/api/namespaces');
                const namespaces = await namespacesResponse.json();
                updateNamespaceOptions(namespaces);
                
            } catch (error) {
                console.error('Error loading data:', error);
                showAlert('Error cargando datos del servidor', 'error');
            }
        }
        
        function updateNamespaceOptions(namespaces) {
            const select = document.getElementById('namespace');
            select.innerHTML = '<option value="">Seleccionar namespace...</option>';
            
            namespaces.forEach(ns => {
                const option = document.createElement('option');
                option.value = ns;
                option.textContent = ns;
                select.appendChild(option);
            });
        }
        
        function updateSchedulesList() {
            const container = document.getElementById('schedule-list');
            
            if (schedules.length === 0) {
                container.innerHTML = `
                    <p style="text-align: center; color: #666; padding: 20px;">
                        No hay horarios configurados aún.<br>
                        <small>Crea tu primer horario usando el formulario de la izquierda.</small>
                    </p>
                `;
                return;
            }
            
            container.innerHTML = schedules.map(schedule => {
                const status = getScheduleStatus(schedule);
                const daysText = formatDays(schedule.days_of_week);
                
                return `
                    <div class="schedule-item">
                        <div class="schedule-header">
                            <div class="schedule-title">📦 ${schedule.namespace}</div>
                            <div class="schedule-status ${status.class}">${status.text}</div>
                        </div>
                        <div class="schedule-details">
                            🕐 ${schedule.startup_time} - ${schedule.shutdown_time} (${schedule.timezone})<br>
                            📅 ${daysText}<br>
                            ${schedule.metadata.business_unit ? `🏢 ${schedule.metadata.business_unit}<br>` : ''}
                            ${schedule.metadata.cost_savings_target ? `💰 Meta de ahorro: $${schedule.metadata.cost_savings_target}/mes` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats() {
            document.getElementById('total-schedules').textContent = schedules.length;
            document.getElementById('active-schedules').textContent = schedules.filter(s => s.enabled).length;
            document.getElementById('running-namespaces').textContent = schedules.filter(s => getScheduleStatus(s).active).length;
            
            const totalSavings = schedules.reduce((sum, s) => sum + (parseInt(s.metadata?.cost_savings_target) || 0), 0);
            document.getElementById('estimated-savings').textContent = `$${totalSavings}`;
        }
        
        function getScheduleStatus(schedule) {
            if (!schedule.enabled) {
                return { text: '⏸️ Pausado', class: 'status-paused', active: false };
            }
            
            const now = new Date();
            const currentDay = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
            const currentTime = now.toTimeString().slice(0, 5);
            
            if (!schedule.days_of_week.includes(currentDay)) {
                return { text: '📅 Fuera de horario', class: 'status-inactive', active: false };
            }
            
            if (currentTime >= schedule.startup_time && currentTime < schedule.shutdown_time) {
                return { text: '🟢 Activo', class: 'status-active', active: true };
            } else {
                return { text: '🔴 Inactivo', class: 'status-inactive', active: false };
            }
        }
        
        function formatDays(days) {
            const dayMap = {
                'monday': 'L', 'tuesday': 'M', 'wednesday': 'X', 
                'thursday': 'J', 'friday': 'V', 'saturday': 'S', 'sunday': 'D'
            };
            return days.map(day => dayMap[day]).join(', ');
        }
        
        function updateTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('es-CO', {
                timeZone: 'America/Bogota',
                hour: '2-digit',
                minute: '2-digit'
            });
            document.getElementById('current-time').textContent = timeString;
        }
        
        updateTime();
        setInterval(updateTime, 60000);
        
        document.querySelectorAll('.day-chip').forEach(chip => {
            chip.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        });
        
        document.getElementById('schedule-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                namespace: document.getElementById('namespace').value,
                timezone: document.getElementById('timezone').value,
                startup_time: document.getElementById('startup-time').value,
                shutdown_time: document.getElementById('shutdown-time').value,
                days_of_week: Array.from(document.querySelectorAll('.day-chip.active')).map(chip => chip.dataset.day),
                metadata: {
                    business_unit: document.getElementById('business-unit').value,
                    cost_savings_target: document.getElementById('cost-target').value
                }
            };
            
            try {
                const response = await fetch('/api/schedules', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    const newSchedule = await response.json();
                    schedules.push(newSchedule);
                    updateSchedulesList();
                    updateStats();
                    showAlert('Horario creado exitosamente', 'success');
                    
                    // Reset form
                    this.reset();
                    document.querySelectorAll('.day-chip').forEach(chip => {
                        chip.classList.remove('active');
                    });
                    ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].forEach(day => {
                        document.querySelector(`[data-day="${day}"]`).classList.add('active');
                    });
                } else {
                    const error = await response.json();
                    showAlert(`Error creando horario: ${error.error}`, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error de conexión con el servidor', 'error');
            }
        });
        
        function showAlert(message, type) {
            const alertContainer = document.getElementById('alert-container');
            const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
            
            alertContainer.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
            
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 4000);
        }
        
        // Cargar datos al iniciar
        loadData();
        
        // Recargar datos cada 30 segundos
        setInterval(loadData, 30000);
    </script>
</body>
</html>'''
    
    # Iniciar servidor de health check en puerto diferente
    health_server = HTTPServer(('0.0.0.0', 8081), HealthHandler)
    health_thread = threading.Thread(target=health_server.serve_forever)
    health_thread.daemon = True
    health_thread.start()
    logger.info("Started health check server on port 8081")
    
    main_logger = ContextualLogger().bind(component="main_loop")
    main_logger.info("Starting namespace controller", 
                     timezone=str(namespace_controller.timezone), 
                     system_namespaces=list(namespace_controller.system_namespaces))
    
    # Start resource monitoring thread
    def resource_monitor():
        resource_logger = ContextualLogger().bind(component="resource_monitor")
        while True:
            try:
                update_resource_metrics()
                resource_logger.debug("Resource metrics updated")
            except Exception as e:
                resource_logger.warning("Failed to update resource metrics", error=str(e))
            time.sleep(60)  # Update every minute
    
    resource_thread = threading.Thread(target=resource_monitor, daemon=True)
    resource_thread.start()
    main_logger.info("Resource monitoring thread started")
    
    while True:
        with OperationLogger("main_loop_iteration") as loop_logger:
            try:
                now = datetime.now(namespace_controller.timezone)
                
                # Get schedules with DynamoDB metrics
                scan_start = time.time()
                items = namespace_controller.table.scan()['Items']
                scan_duration = time.time() - scan_start
                namespace_controller.metrics.record_dynamodb_operation(
                    "scan", namespace_controller.table.name, "success", scan_duration
                )
                
                processed_namespaces = 0
                
                loop_logger.info("Processing schedules", 
                               total_schedules=len(items),
                               current_time=now.strftime("%H:%M:%S"),
                               current_day=now.strftime("%A").lower())
                
                for item in items:
                    ns = item['namespace']
                    namespace_start = time.time()
                    
                    if ns in namespace_controller.get_namespaces():
                        schedules = item.get('schedules', [])
                        today = now.date().isoformat()
                        today_sched = next((s for s in schedules if s['date'] == today), None)
                        
                        if today_sched:
                            startup = datetime.strptime(today_sched['startup'], "%H:%M").time()
                            shutdown = datetime.strptime(today_sched['shutdown'], "%H:%M").time()
                            
                            if now.time() >= startup and now.time() < shutdown:
                                namespace_controller.scale_namespace(ns, False)  # Encender
                            elif now.time() >= shutdown:
                                namespace_controller.scale_namespace(ns, True)   # Apagar
                        else:
                            # Horario por defecto: Lun-Vie 13:00-20:00 UTC (8AM-3PM -05)
                            if (now.weekday() < 5 and 
                                now.time() >= datetime.strptime("13:00", "%H:%M").time() and 
                                now.time() < datetime.strptime("20:00", "%H:%M").time()):
                                namespace_controller.scale_namespace(ns, False)  # Encender
                            elif (now.weekday() >= 5 or 
                                  now.time() >= datetime.strptime("20:00", "%H:%M").time()):
                                namespace_controller.scale_namespace(ns, True)   # Apagar
                        
                        # Record schedule execution time
                        namespace_duration = time.time() - namespace_start
                        namespace_controller.metrics.record_schedule_execution(ns, namespace_duration)
                        processed_namespaces += 1
                        
            except Exception as e:
                loop_logger.error("Main loop error", error_details=str(e))
                namespace_controller.metrics.controller_errors.labels(error_type="main_loop_error").inc()
                namespace_controller.metrics.update_health_status("controller", False)
            else:
                # Update controller health status on successful loop
                namespace_controller.metrics.update_health_status("controller", True)
                loop_logger.info("Main loop iteration completed successfully", 
                               processed_namespaces=processed_namespaces)
                
        time.sleep(300)  # Esperar 5 minutos

if __name__ == "__main__":
    main()