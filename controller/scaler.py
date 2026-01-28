import boto3, os, time, subprocess, datetime, pytz, croniter, asyncio, logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from tenacity import retry, stop_after_attempt, wait_exponential
import json

# Configurar logging estructurado
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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Métricas Prometheus
scaling_operations = Counter(
    'namespace_scaling_operations_total',
    'Total namespace scaling operations',
    ['namespace', 'operation', 'status']
)

scaling_duration = Histogram(
    'namespace_scaling_duration_seconds',
    'Time spent scaling namespaces',
    ['namespace', 'operation']
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

# Configuración
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'NamespaceSchedules'))
tz = pytz.timezone(os.environ.get('TIMEZONE', 'UTC'))
system_ns = set(os.environ.get('SYSTEM_NAMESPACES', 'kube-system,kube-public,kube-node-lease,default,argocd,kyverno,encendido-eks,karpenter').split(','))

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
            
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

class RollbackManager:
    def __init__(self):
        self.rollback_history = {}
        
    def save_state(self, namespace: str, deployments: List[Dict]):
        """Guardar estado antes de operación de escalado"""
        self.rollback_history[namespace] = {
            'timestamp': datetime.utcnow().isoformat(),
            'deployments': deployments
        }
        logger.info("State saved for rollback", namespace=namespace, deployments_count=len(deployments))
        
    def rollback(self, namespace: str):
        """Restaurar estado anterior"""
        if namespace not in self.rollback_history:
            logger.error("No rollback data available", namespace=namespace)
            return False
            
        previous_state = self.rollback_history[namespace]
        try:
            for deployment in previous_state['deployments']:
                subprocess.run([
                    "kubectl", "scale", "deploy", deployment['name'], 
                    "-n", namespace, f"--replicas={deployment['replicas']}"
                ], check=True)
            logger.info("Rollback completed successfully", namespace=namespace)
            return True
        except Exception as e:
            logger.error("Rollback failed", namespace=namespace, error=str(e))
            controller_errors.labels(error_type="rollback_failed").inc()
            return False

# Instancias globales
circuit_breaker = CircuitBreaker()
rollback_manager = RollbackManager()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_namespaces():
    """Obtener lista de namespaces excluyendo los del sistema"""
    try:
        result = subprocess.check_output([
            "kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"
        ]).decode().split()
        namespaces = [ns for ns in result if ns not in system_ns]
        active_namespaces.set(len(namespaces))
        logger.info("Retrieved namespaces", count=len(namespaces), namespaces=namespaces)
        return namespaces
    except subprocess.CalledProcessError as e:
        logger.error("Failed to get namespaces", error=str(e))
        controller_errors.labels(error_type="kubectl_error").inc()
        raise

def get_deployment_state(namespace: str) -> List[Dict]:
    """Obtener estado actual de deployments en un namespace"""
    try:
        deps = subprocess.check_output([
            "kubectl", "get", "deploy", "-n", namespace, 
            "-o", "jsonpath={range .items[*]}{.metadata.name},{.spec.replicas}{\"\\n\"}{end}"
        ]).decode().strip().split('\n')
        
        deployments = []
        for dep_info in deps:
            if dep_info:
                name, replicas = dep_info.split(',')
                deployments.append({
                    'name': name,
                    'replicas': int(replicas) if replicas else 0
                })
        return deployments
    except subprocess.CalledProcessError as e:
        logger.error("Failed to get deployment state", namespace=namespace, error=str(e))
        return []

def scale(ns, to_zero):
    """Escalar deployments en un namespace"""
    action = "shutdown" if to_zero else "startup"
    operation_start = time.time()
    
    try:
        with scaling_duration.labels(namespace=ns, operation=action).time():
            # Guardar estado antes de escalar
            if to_zero:
                current_state = get_deployment_state(ns)
                rollback_manager.save_state(ns, current_state)
            
            # Usar circuit breaker para la operación
            circuit_breaker.call(_perform_scaling, ns, to_zero)
            
        scaling_operations.labels(namespace=ns, operation=action, status="success").inc()
        logger.info("Scaling operation completed", 
                   namespace=ns, action=action, duration=time.time() - operation_start)
        
    except Exception as e:
        scaling_operations.labels(namespace=ns, operation=action, status="error").inc()
        controller_errors.labels(error_type="scaling_error").inc()
        logger.error("Scaling operation failed", 
                    namespace=ns, action=action, error=str(e))
        
        # Intentar rollback en caso de error
        if to_zero:
            logger.info("Attempting rollback due to scaling failure", namespace=ns)
            rollback_manager.rollback(ns)

def _perform_scaling(ns, to_zero):
    """Realizar la operación de escalado real"""
    action = "Apagado" if to_zero else "Encendido"
    
    deps = subprocess.check_output([
        "kubectl", "get", "deploy", "-n", ns, 
        "-o", "custom-columns=NAME:.metadata.name", "--no-headers"
    ]).decode().split()
    
    for dep in deps:
        if to_zero:
            current = subprocess.check_output([
                "kubectl", "get", "deploy", dep, "-n", ns, 
                "-o", "jsonpath={.spec.replicas}"
            ]).decode().strip()
            
            if current and int(current) > 0:
                subprocess.run([
                    "kubectl", "annotate", "deploy", dep, "-n", ns, 
                    f"original-replicas={current}", "--overwrite"
                ], check=True)
                subprocess.run([
                    "kubectl", "scale", "deploy", dep, "-n", ns, "--replicas=0"
                ], check=True)
        else:
            orig = subprocess.check_output([
                "kubectl", "get", "deploy", dep, "-n", ns, 
                "-o", "jsonpath={.metadata.annotations.original-replicas}"
            ]).decode().strip()
            
            if orig:
                subprocess.run([
                    "kubectl", "scale", "deploy", dep, "-n", ns, f"--replicas={orig}"
                ], check=True)
                subprocess.run([
                    "kubectl", "annotate", "deploy", dep, "-n", ns, "original-replicas-"
                ], check=True)
    
    # Crear evento en Kubernetes
    subprocess.run([
        "kubectl", "create", "event", "-n", ns, "--type=Normal", 
        f"--reason=Auto{action}", f"{action} automático"
    ], check=True)

def health_check():
    """Health check endpoint"""
    try:
        # Verificar conectividad a DynamoDB
        table.meta.client.describe_table(TableName=table.name)
        
        # Verificar conectividad a Kubernetes
        subprocess.check_output(["kubectl", "version", "--client"], timeout=5)
        
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

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
                self.end_headers()
                self.wfile.write(json.dumps(health).encode())
            elif self.path == '/metrics':
                # Prometheus metrics ya están en el puerto 8080
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'# Metrics available on port 8080')
            else:
                self.send_response(404)
                self.end_headers()
    
    # Iniciar servidor de health check en puerto diferente
    health_server = HTTPServer(('0.0.0.0', 8081), HealthHandler)
    health_thread = threading.Thread(target=health_server.serve_forever)
    health_thread.daemon = True
    health_thread.start()
    logger.info("Started health check server on port 8081")
    
    logger.info("Starting namespace controller", timezone=str(tz), system_namespaces=list(system_ns))
    
    while True:
        try:
            now = datetime.now(tz)
            items = table.scan()['Items']
            
            for item in items:
                ns = item['namespace']
                if ns in get_namespaces():
                    schedules = item.get('schedules', [])
                    today = now.date().isoformat()
                    today_sched = next((s for s in schedules if s['date'] == today), None)
                    
                    if today_sched:
                        startup = datetime.strptime(today_sched['startup'], "%H:%M").time()
                        shutdown = datetime.strptime(today_sched['shutdown'], "%H:%M").time()
                        
                        if now.time() >= startup and now.time() < shutdown:
                            scale(ns, False)  # Encender
                        elif now.time() >= shutdown:
                            scale(ns, True)   # Apagar
                    else:
                        # Horario por defecto: Lun-Vie 13:00-20:00 UTC (8AM-3PM -05)
                        if (now.weekday() < 5 and 
                            now.time() >= datetime.strptime("13:00", "%H:%M").time() and 
                            now.time() < datetime.strptime("20:00", "%H:%M").time()):
                            scale(ns, False)  # Encender
                        elif (now.weekday() >= 5 or 
                              now.time() >= datetime.strptime("20:00", "%H:%M").time()):
                            scale(ns, True)   # Apagar
                            
        except Exception as e:
            logger.error("Main loop error", error=str(e))
            controller_errors.labels(error_type="main_loop_error").inc()
            
        time.sleep(300)  # Esperar 5 minutos

if __name__ == "__main__":
    main()