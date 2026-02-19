#!/usr/bin/env python3
"""
kubectl Runner API Server
Provides REST API for executing kubectl commands and managing scheduled tasks
Version: 2.0.0 - Added DynamoDB integration for task scheduling
"""

import os
import json
import logging
import logging.handlers
import subprocess
import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from flask import Flask, request, jsonify, Response, g
from flask_cors import CORS
from croniter import croniter
import yaml
import boto3
from botocore.exceptions import ClientError
import uuid
import traceback

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id
        if hasattr(record, 'namespace'):
            log_data['namespace'] = record.namespace
        if hasattr(record, 'cost_center'):
            log_data['cost_center'] = record.cost_center
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        
        return json.dumps(log_data)

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_format = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'
log_file = os.getenv('LOG_FILE', '/app/logs/app.log')

# Create logs directory
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure root logger
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)

# Console handler
console_handler = logging.StreamHandler()

# Set formatters based on configuration
if log_format == 'json':
    formatter = StructuredFormatter()
else:
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

app = Flask(__name__)
CORS(app)

# Request logging middleware
@app.before_request
def before_request():
    """Add request_id and log incoming requests"""
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.start_time = time.time()
    
    logger.info(
        f"Incoming request: {request.method} {request.path}",
        extra={
            'request_id': g.request_id,
            'operation': f"{request.method} {request.path}",
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'unknown')
        }
    )

@app.after_request
def after_request(response):
    """Log request completion with duration"""
    if hasattr(g, 'start_time'):
        duration_ms = int((time.time() - g.start_time) * 1000)
        
        logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'request_id': g.request_id if hasattr(g, 'request_id') else 'unknown',
                'operation': f"{request.method} {request.path}",
                'status_code': response.status_code,
                'duration_ms': duration_ms
            }
        )
        
        # Add request_id to response headers
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
    
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Log unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {str(e)}",
        extra={
            'request_id': g.request_id if hasattr(g, 'request_id') else 'unknown',
            'operation': f"{request.method} {request.path}",
            'exception': traceback.format_exc()
        },
        exc_info=True
    )
    
    return jsonify({
        'error': 'Internal server error',
        'request_id': g.request_id if hasattr(g, 'request_id') else 'unknown'
    }), 500

# Helper function for contextual logging
def log_with_context(level, message, **context):
    """
    Log a message with additional context
    
    Args:
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        message: Log message
        **context: Additional context fields (task_id, namespace, cost_center, etc.)
    """
    extra = {}
    
    # Add request_id if available
    if hasattr(g, 'request_id'):
        extra['request_id'] = g.request_id
    
    # Add custom context
    extra.update(context)
    
    # Get logger method
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=extra)



class DynamoDBManager:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'task-scheduler-logs')
        self.permissions_table_name = os.getenv('PERMISSIONS_TABLE_NAME', 'cost-center-permissions')
        
        # Permissions cache configuration
        self.permissions_cache = {}  # {cost_center: {'data': {...}, 'timestamp': float}}
        self.cache_ttl = int(os.getenv('PERMISSIONS_CACHE_TTL', '300'))  # Default 5 minutes
        self.cache_enabled = os.getenv('PERMISSIONS_CACHE_ENABLED', 'true').lower() == 'true'
        
        self.ensure_tables_exist()

    def ensure_tables_exist(self):
        """Create DynamoDB tables if they don't exist"""
        try:
            # Create main activity logs table
            try:
                self.table = self.dynamodb.Table(self.table_name)
                self.table.load()
                logger.info(f"Table {self.table_name} already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.info(f"Creating table {self.table_name}")
                    self.table = self.dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {'AttributeName': 'namespace_name', 'KeyType': 'HASH'},
                            {'AttributeName': 'timestamp_start', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'namespace_name', 'AttributeType': 'S'},
                            {'AttributeName': 'timestamp_start', 'AttributeType': 'N'},
                            {'AttributeName': 'cost_center', 'AttributeType': 'S'},
                            {'AttributeName': 'requested_by', 'AttributeType': 'S'},
                            {'AttributeName': 'cluster_name', 'AttributeType': 'S'}
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'cost-center-index',
                                'KeySchema': [
                                    {'AttributeName': 'cost_center', 'KeyType': 'HASH'},
                                    {'AttributeName': 'timestamp_start', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'},
                                'BillingMode': 'PAY_PER_REQUEST'
                            },
                            {
                                'IndexName': 'requested-by-timestamp-index',
                                'KeySchema': [
                                    {'AttributeName': 'requested_by', 'KeyType': 'HASH'},
                                    {'AttributeName': 'timestamp_start', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'},
                                'BillingMode': 'PAY_PER_REQUEST'
                            },
                            {
                                'IndexName': 'cluster-timestamp-index',
                                'KeySchema': [
                                    {'AttributeName': 'cluster_name', 'KeyType': 'HASH'},
                                    {'AttributeName': 'timestamp_start', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'},
                                'BillingMode': 'PAY_PER_REQUEST'
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST'
                    )
                    self.table.wait_until_exists()
                    logger.info(f"Table {self.table_name} created successfully")

            # Create permissions table
            try:
                self.permissions_table = self.dynamodb.Table(self.permissions_table_name)
                self.permissions_table.load()
                logger.info(f"Table {self.permissions_table_name} already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.info(f"Creating table {self.permissions_table_name}")
                    self.permissions_table = self.dynamodb.create_table(
                        TableName=self.permissions_table_name,
                        KeySchema=[
                            {'AttributeName': 'cost_center', 'KeyType': 'HASH'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'cost_center', 'AttributeType': 'S'}
                        ],
                        BillingMode='PAY_PER_REQUEST'
                    )
                    self.permissions_table.wait_until_exists()
                    logger.info(f"Table {self.permissions_table_name} created successfully")

        except Exception as e:
            logger.error(f"Error ensuring tables exist: {e}")
            raise

    def log_namespace_activity(self, namespace_name, operation_type, cost_center, user_id=None, requested_by=None, cluster_name=None, **kwargs):
        """Log namespace activity to DynamoDB with user and cluster tracking"""
        try:
            timestamp_start = int(time.time())
            item = {
                'namespace_name': namespace_name,
                'timestamp_start': timestamp_start,
                'operation_type': operation_type,  # 'auto_shutdown', 'auto_startup', 'manual_activation', 'manual_deactivation'
                'cost_center': cost_center,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'id': str(uuid.uuid4())
            }
            
            # Capture user information - requested_by is the primary field for user tracking
            # user_id is kept for backward compatibility
            if requested_by:
                item['requested_by'] = requested_by
                item['user_id'] = requested_by  # Also set user_id for consistency
            elif user_id:
                item['user_id'] = user_id
                item['requested_by'] = user_id  # Set requested_by from user_id
            else:
                # Default to 'system' if no user provided
                item['requested_by'] = 'system'
                item['user_id'] = 'system'
            
            # Capture cluster information
            if cluster_name:
                item['cluster_name'] = cluster_name
            else:
                # Default to environment variable or 'unknown-cluster'
                item['cluster_name'] = os.getenv('EKS_CLUSTER_NAME', 'unknown-cluster')
            
            # Add any additional fields
            item.update(kwargs)
            
            self.table.put_item(Item=item)
            logger.info(f"Logged activity for namespace {namespace_name}: {operation_type} by {item['requested_by']} on cluster {item['cluster_name']}")
            return item
            
        except Exception as e:
            logger.error(f"Error logging namespace activity: {e}")
            # Retry logic
            for attempt in range(3):
                try:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    self.table.put_item(Item=item)
                    logger.info(f"Logged activity for namespace {namespace_name} on retry {attempt + 1}")
                    return item
                except Exception as retry_error:
                    logger.error(f"Retry {attempt + 1} failed: {retry_error}")
            
            raise Exception(f"Failed to log activity after 3 retries: {e}")

    def complete_namespace_activity(self, namespace_name, timestamp_start):
        """Complete a namespace activity record"""
        try:
            timestamp_end = int(time.time())
            duration_minutes = (timestamp_end - timestamp_start) // 60
            
            self.table.update_item(
                Key={
                    'namespace_name': namespace_name,
                    'timestamp_start': timestamp_start
                },
                UpdateExpression='SET #status = :status, timestamp_end = :end_time, duration_minutes = :duration',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':end_time': timestamp_end,
                    ':duration': duration_minutes
                }
            )
            logger.info(f"Completed activity for namespace {namespace_name}, duration: {duration_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error completing namespace activity: {e}")
            raise

    def get_activities_by_cost_center(self, cost_center, start_date=None, end_date=None):
        """Get activities by cost center and date range"""
        try:
            query_kwargs = {
                'IndexName': 'cost-center-index',
                'KeyConditionExpression': 'cost_center = :cc',
                'ExpressionAttributeValues': {':cc': cost_center}
            }
            
            if start_date and end_date:
                start_timestamp = int(start_date.timestamp())
                end_timestamp = int(end_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start BETWEEN :start AND :end'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':start': start_timestamp,
                    ':end': end_timestamp
                })
            
            response = self.table.query(**query_kwargs)
            return response['Items']
            
        except Exception as e:
            logger.error(f"Error getting activities by cost center: {e}")
            return []

    def get_activities_by_user(self, requested_by, start_date=None, end_date=None, limit=100):
        """Get activities by user (requested_by) and date range"""
        try:
            query_kwargs = {
                'IndexName': 'requested-by-timestamp-index',
                'KeyConditionExpression': 'requested_by = :user',
                'ExpressionAttributeValues': {':user': requested_by},
                'Limit': limit,
                'ScanIndexForward': False  # Sort by timestamp descending (newest first)
            }
            
            if start_date and end_date:
                start_timestamp = int(start_date.timestamp())
                end_timestamp = int(end_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start BETWEEN :start AND :end'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':start': start_timestamp,
                    ':end': end_timestamp
                })
            elif start_date:
                start_timestamp = int(start_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start >= :start'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':start': start_timestamp
                })
            elif end_date:
                end_timestamp = int(end_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start <= :end'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':end': end_timestamp
                })
            
            response = self.table.query(**query_kwargs)
            return response['Items']
            
        except Exception as e:
            logger.error(f"Error getting activities by user: {e}")
            return []

    def get_activities_by_cluster(self, cluster_name, start_date=None, end_date=None, limit=100):
        """Get activities by cluster and date range"""
        try:
            query_kwargs = {
                'IndexName': 'cluster-timestamp-index',
                'KeyConditionExpression': 'cluster_name = :cluster',
                'ExpressionAttributeValues': {':cluster': cluster_name},
                'Limit': limit,
                'ScanIndexForward': False  # Sort by timestamp descending (newest first)
            }
            
            if start_date and end_date:
                start_timestamp = int(start_date.timestamp())
                end_timestamp = int(end_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start BETWEEN :start AND :end'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':start': start_timestamp,
                    ':end': end_timestamp
                })
            elif start_date:
                start_timestamp = int(start_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start >= :start'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':start': start_timestamp
                })
            elif end_date:
                end_timestamp = int(end_date.timestamp())
                query_kwargs['KeyConditionExpression'] += ' AND timestamp_start <= :end'
                query_kwargs['ExpressionAttributeValues'].update({
                    ':end': end_timestamp
                })
            
            response = self.table.query(**query_kwargs)
            return response['Items']
            
        except Exception as e:
            logger.error(f"Error getting activities by cluster: {e}")
            return []

    def validate_cost_center_permissions(self, cost_center, user_id=None, requested_by=None, operation_type=None, namespace=None, cluster_name=None):
        """Validate if cost center has permissions (with caching and audit logging)"""
        validation_result = False
        validation_source = 'unknown'
        error_message = None
        
        # Determine the user for logging
        user_for_logging = requested_by or user_id
        
        try:
            # Check cache first if enabled
            if self.cache_enabled:
                cached_data = self._get_from_cache(cost_center)
                if cached_data is not None:
                    logger.debug(f"Cache hit for cost center {cost_center}")
                    validation_result = cached_data.get('is_authorized', False)
                    validation_source = 'cache'
                    
                    # Log validation audit event
                    self._log_validation_audit(
                        validation_type='cost_center_permission',
                        cost_center=cost_center,
                        user_id=user_id,
                        requested_by=requested_by,
                        operation_type=operation_type,
                        namespace=namespace,
                        cluster_name=cluster_name,
                        validation_result=validation_result,
                        validation_source=validation_source
                    )
                    
                    return validation_result
            
            # Cache miss or disabled - fetch from DynamoDB
            logger.debug(f"Cache miss for cost center {cost_center}, fetching from DynamoDB")
            response = self.permissions_table.get_item(
                Key={'cost_center': cost_center}
            )
            
            if 'Item' in response:
                # Store in cache
                if self.cache_enabled:
                    self._put_in_cache(cost_center, response['Item'])
                validation_result = response['Item'].get('is_authorized', False)
                validation_source = 'dynamodb'
            else:
                # If not found, cache the negative result to avoid repeated lookups
                if self.cache_enabled:
                    self._put_in_cache(cost_center, {'is_authorized': False, 'not_found': True})
                validation_result = False
                validation_source = 'dynamodb'
                error_message = 'Cost center not found'
            
            # Log validation audit event
            self._log_validation_audit(
                validation_type='cost_center_permission',
                cost_center=cost_center,
                user_id=user_id,
                requested_by=requested_by,
                operation_type=operation_type,
                namespace=namespace,
                cluster_name=cluster_name,
                validation_result=validation_result,
                validation_source=validation_source,
                error_message=error_message
            )
            
            return validation_result
                
        except Exception as e:
            logger.error(f"Error validating cost center permissions: {e}")
            error_message = str(e)
            
            # Log validation failure audit event
            self._log_validation_audit(
                validation_type='cost_center_permission',
                cost_center=cost_center,
                user_id=user_id,
                requested_by=requested_by,
                operation_type=operation_type,
                namespace=namespace,
                cluster_name=cluster_name,
                validation_result=False,
                validation_source='error',
                error_message=error_message
            )
            
            return False

    def _get_from_cache(self, cost_center):
        """Get cost center permissions from cache"""
        if cost_center in self.permissions_cache:
            cache_entry = self.permissions_cache[cost_center]
            # Check if cache entry is still valid
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                return cache_entry['data']
            else:
                # Cache expired, remove it
                logger.debug(f"Cache expired for cost center {cost_center}")
                del self.permissions_cache[cost_center]
        return None

    def _put_in_cache(self, cost_center, data):
        """Put cost center permissions in cache"""
        self.permissions_cache[cost_center] = {
            'data': data,
            'timestamp': time.time()
        }
        logger.debug(f"Cached permissions for cost center {cost_center}")

    def _log_validation_audit(self, validation_type, cost_center, validation_result, 
                              validation_source, user_id=None, requested_by=None, operation_type=None, 
                              namespace=None, cluster_name=None, error_message=None, **kwargs):
        """Log validation audit events to DynamoDB with user and cluster tracking"""
        try:
            timestamp = int(time.time())
            audit_item = {
                'namespace_name': namespace or 'N/A',
                'timestamp_start': timestamp,
                'operation_type': f'validation_{validation_type}',
                'cost_center': cost_center,
                'validation_result': 'success' if validation_result else 'failure',
                'validation_source': validation_source,
                'status': 'completed',
                'created_at': datetime.now().isoformat(),
                'id': str(uuid.uuid4())
            }
            
            # Capture user information - requested_by is the primary field
            if requested_by:
                audit_item['requested_by'] = requested_by
                audit_item['user_id'] = requested_by
            elif user_id:
                audit_item['user_id'] = user_id
                audit_item['requested_by'] = user_id
            else:
                audit_item['requested_by'] = 'system'
                audit_item['user_id'] = 'system'
            
            # Capture cluster information
            if cluster_name:
                audit_item['cluster_name'] = cluster_name
            else:
                # Default to environment variable or 'unknown-cluster'
                audit_item['cluster_name'] = os.getenv('EKS_CLUSTER_NAME', 'unknown-cluster')
            
            if operation_type:
                audit_item['requested_operation'] = operation_type
            
            if error_message:
                audit_item['error_message'] = error_message
            
            # Add any additional fields
            audit_item.update(kwargs)
            
            self.table.put_item(Item=audit_item)
            logger.info(f"Logged validation audit: {validation_type} for {cost_center} by {audit_item['requested_by']} on cluster {audit_item['cluster_name']} - Result: {validation_result}")
            
        except Exception as e:
            # Don't fail the validation if audit logging fails
            logger.error(f"Error logging validation audit: {e}")

    def invalidate_cache(self, cost_center=None):
        """Invalidate cache for a specific cost center or all cache"""
        if cost_center:
            if cost_center in self.permissions_cache:
                del self.permissions_cache[cost_center]
                logger.info(f"Invalidated cache for cost center {cost_center}")
        else:
            self.permissions_cache.clear()
            logger.info("Invalidated all permissions cache")

    def get_cache_stats(self):
        """Get cache statistics"""
        return {
            'enabled': self.cache_enabled,
            'ttl_seconds': self.cache_ttl,
            'cached_entries': len(self.permissions_cache),
            'entries': list(self.permissions_cache.keys())
        }

    def set_cost_center_permissions(self, cost_center, is_authorized, max_concurrent_namespaces=5, authorized_namespaces=None):
        """Set permissions for a cost center"""
        try:
            item = {
                'cost_center': cost_center,
                'is_authorized': is_authorized,
                'max_concurrent_namespaces': max_concurrent_namespaces,
                'authorized_namespaces': authorized_namespaces or [],
                'created_at': int(time.time()),
                'updated_at': int(time.time())
            }
            
            self.permissions_table.put_item(Item=item)
            
            # Invalidate cache for this cost center
            self.invalidate_cache(cost_center)
            
            logger.info(f"Set permissions for cost center {cost_center}: {is_authorized}")
            
        except Exception as e:
            logger.error(f"Error setting cost center permissions: {e}")
            raise

class TaskScheduler:
    def __init__(self):
        self.tasks = {}
        self.running_tasks = {}
        self.task_history = []
        # Remove manual counter - we'll calculate it dynamically
        self.dynamodb_manager = DynamoDBManager()
        self.cluster_name = os.getenv('EKS_CLUSTER_NAME', 'unknown-cluster')  # Capture cluster name
        
        # Thread pool configuration
        self.max_workers = int(os.getenv('MAX_TASK_WORKERS', '5'))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='task-worker')
        
        # Task execution configuration
        self.task_timeout = int(os.getenv('TASK_TIMEOUT_SECONDS', '300'))  # 5 minutes default
        self.max_retries = int(os.getenv('TASK_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('TASK_RETRY_DELAY_SECONDS', '10'))
        
        # Task execution tracking
        self.task_futures = {}  # Maps task_id to Future object
        self.task_locks = {}  # Maps task_id to Lock for thread-safe operations
        
        # Weekly schedule cache
        self.weekly_cache = {}  # Maps week_start_date to cached data
        self.weekly_cache_ttl = int(os.getenv('WEEKLY_CACHE_TTL', '300'))  # Default 5 minutes
        self.weekly_cache_enabled = os.getenv('WEEKLY_CACHE_ENABLED', 'true').lower() == 'true'
        
        # Protected namespaces configuration
        self.protected_namespaces = self.load_protected_namespaces()
        
        # Default namespace management
        self.default_validation_enabled = os.getenv('DEFAULT_VALIDATION_ENABLED', 'true').lower() == 'true'
        self.default_validation_interval = int(os.getenv('DEFAULT_VALIDATION_INTERVAL', '900'))  # 15 minutes default
        
        # Persistence configuration
        self.auto_save_enabled = os.getenv('AUTO_SAVE_ENABLED', 'true').lower() == 'true'
        self.auto_save_interval = int(os.getenv('AUTO_SAVE_INTERVAL_SECONDS', '300'))  # 5 minutes default
        
        self.load_tasks()
        self.start_scheduler()
        
        # Start auto-save if enabled
        if self.auto_save_enabled:
            self.start_auto_save(self.auto_save_interval)
        
        # Run initial default state validation in background (non-blocking)
        if self.default_validation_enabled:
            threading.Thread(target=self.ensure_default_namespace_state, daemon=True).start()
        
        logger.info(f"TaskScheduler initialized with {self.max_workers} workers, "
                   f"{self.task_timeout}s timeout, {self.max_retries} max retries, "
                   f"auto-save: {self.auto_save_enabled}")

    def load_protected_namespaces(self):
        """Load protected namespaces from ConfigMap (preferred) or configuration file (fallback)"""
        try:
            # First, try to load from ConfigMap (Kubernetes-native approach)
            result = self.execute_kubectl_command('get configmap protected-namespaces-config -n task-scheduler -o json')
            
            if result['success']:
                configmap_data = json.loads(result['stdout'])
                config_json = configmap_data.get('data', {}).get('protected-namespaces.json', '')
                
                if config_json:
                    config = json.loads(config_json)
                    protected_list = config.get('protected_namespaces', [])
                    logger.info(f"Loaded {len(protected_list)} protected namespaces from ConfigMap")
                    return set(protected_list)
            
            # Fallback to local file
            config_path = '/app/config/protected-namespaces.json'
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    protected_list = config.get('protected_namespaces', [])
                    logger.info(f"Loaded {len(protected_list)} protected namespaces from local config file")
                    return set(protected_list)
            else:
                # Default protected namespaces if neither ConfigMap nor config file exists
                default_protected = {
                    'kube-system', 'kube-public', 'kube-node-lease', 'default',
                    'karpenter', 'kyverno', 'argocd', 'istio-system', 
                    'monitoring', 'task-scheduler', 'cert-manager', 'ingress-nginx',
                    'amazon-cloudwatch', 'calico-system', 'tigera-operator'
                }
                logger.warning(f"Neither ConfigMap nor config file found, using defaults: {len(default_protected)} namespaces")
                return default_protected
                
        except Exception as e:
            logger.error(f"Error loading protected namespaces: {e}")
            # Return minimal default set
            return {'kube-system', 'kube-public', 'kube-node-lease', 'default', 'task-scheduler'}

    def is_protected_namespace(self, namespace_name):
        """Check if a namespace is protected (never gets turned off)"""
        return namespace_name in self.protected_namespaces

    def get_schedulable_namespaces(self):
        """Get list of namespaces that can be scheduled (non-protected)"""
        try:
            result = self.execute_kubectl_command('get namespaces -o json')
            if not result['success']:
                logger.error(f"Failed to get namespaces: {result['stderr']}")
                return []
            
            namespaces_data = json.loads(result['stdout'])
            schedulable_namespaces = []
            
            for item in namespaces_data['items']:
                namespace_name = item['metadata']['name']
                
                # Skip protected namespaces
                if not self.is_protected_namespace(namespace_name):
                    schedulable_namespaces.append(namespace_name)
            
            logger.debug(f"Found {len(schedulable_namespaces)} schedulable namespaces")
            return schedulable_namespaces
            
        except Exception as e:
            logger.error(f"Error getting schedulable namespaces: {e}")
            return []

    def ensure_default_namespace_state(self):
        """Ensure default state: protected namespaces ON, others based on business hours"""
        try:
            logger.info("Starting default namespace state validation")
            
            # Check if we're in business hours
            is_business_hours = not self.is_non_business_hours()
            
            # Get all namespaces
            result = self.execute_kubectl_command('get namespaces -o json')
            if not result['success']:
                logger.error(f"Failed to get namespaces for default state validation: {result['stderr']}")
                return False
            
            namespaces_data = json.loads(result['stdout'])
            actions_taken = []
            
            for item in namespaces_data['items']:
                namespace_name = item['metadata']['name']
                
                if self.is_protected_namespace(namespace_name):
                    # Protected namespaces should always be active
                    if not self.is_namespace_active(namespace_name):
                        logger.info(f"Activating protected namespace: {namespace_name}")
                        result = self.scale_namespace_resources(namespace_name, 1, enable_rollback=False)
                        if result.get('success'):
                            actions_taken.append(f"Activated protected namespace: {namespace_name}")
                            # Log activity for protected namespace activation
                            self.dynamodb_manager.log_namespace_activity(
                                namespace_name=namespace_name,
                                operation_type='auto_startup_protected',
                                cost_center='system',
                                requested_by='system',
                                cluster_name=self.cluster_name
                            )
                        else:
                            logger.error(f"Failed to activate protected namespace {namespace_name}: {result.get('error')}")
                else:
                    # Non-protected namespaces: active during business hours, inactive otherwise
                    current_active = self.is_namespace_active(namespace_name)
                    has_scheduled_tasks = self.has_active_scheduled_tasks(namespace_name)
                    
                    if is_business_hours:
                        # During business hours: activate all non-protected namespaces
                        if not current_active:
                            logger.info(f"Activating namespace for business hours: {namespace_name}")
                            result = self.scale_namespace_resources(namespace_name, 1, enable_rollback=False)
                            if result.get('success'):
                                actions_taken.append(f"Activated namespace for business hours: {namespace_name}")
                                # Log activity for business hours activation
                                self.dynamodb_manager.log_namespace_activity(
                                    namespace_name=namespace_name,
                                    operation_type='auto_startup_business_hours',
                                    cost_center='system',
                                    requested_by='system',
                                    cluster_name=self.cluster_name
                                )
                            else:
                                logger.error(f"Failed to activate namespace {namespace_name} for business hours: {result.get('error')}")
                    else:
                        # Outside business hours: deactivate unless they have active scheduled tasks
                        if current_active and not has_scheduled_tasks:
                            logger.info(f"Deactivating namespace outside business hours: {namespace_name}")
                            result = self.scale_namespace_resources(namespace_name, 0, enable_rollback=False)
                            if result.get('success'):
                                actions_taken.append(f"Deactivated namespace outside business hours: {namespace_name}")
                                # Log activity for business hours deactivation
                                self.dynamodb_manager.log_namespace_activity(
                                    namespace_name=namespace_name,
                                    operation_type='auto_shutdown_business_hours',
                                    cost_center='system',
                                    requested_by='system',
                                    cluster_name=self.cluster_name
                                )
                            else:
                                logger.error(f"Failed to deactivate namespace {namespace_name} outside business hours: {result.get('error')}")
            
            if actions_taken:
                business_status = "business hours" if is_business_hours else "non-business hours"
                logger.info(f"Default state validation completed during {business_status}. Actions taken: {len(actions_taken)}")
                for action in actions_taken:
                    logger.info(f"  - {action}")
            else:
                business_status = "business hours" if is_business_hours else "non-business hours"
                logger.debug(f"Default state validation completed during {business_status}. No actions needed.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring default namespace state: {e}")
            return False

    def has_active_scheduled_tasks(self, namespace_name):
        """Check if a namespace has active scheduled tasks that should keep it running"""
        try:
            current_time = datetime.now()
            
            for task_id, task in self.tasks.items():
                if (task.get('namespace') == namespace_name and 
                    task.get('status') in ['pending', 'running'] and
                    task.get('schedule')):
                    
                    # Check if this task should be running now
                    if self.should_task_be_running_now(task, current_time):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking active scheduled tasks for {namespace_name}: {e}")
            return False

    def should_task_be_running_now(self, task, current_time):
        """Check if a task should be running at the current time"""
        try:
            schedule = task.get('schedule')
            if not schedule:
                return False
            
            # Use croniter to check if we're in an active period
            # This is a simplified check - you might want to make it more sophisticated
            cron = croniter(schedule, current_time)
            
            # Check if the last occurrence was recent (within the last hour)
            last_occurrence = cron.get_prev(datetime)
            time_since_last = (current_time - last_occurrence).total_seconds()
            
            # If the task is an activation task and it ran recently, namespace should be active
            if task.get('operation_type') == 'activate' and time_since_last < 3600:  # 1 hour
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if task should be running: {e}")
            return False

    def activate_namespace_with_kyverno(self, namespace, cost_center='default', user_id='system', requested_by=None):
        """Activate a namespace using Kyverno labels instead of direct scaling"""
        try:
            # Set namespace label to active
            result = self.execute_kubectl_command(
                f'label namespace {namespace} scheduler.pocarqnube.com/status=active --overwrite'
            )
            
            if not result['success']:
                logger.error(f"Failed to label namespace {namespace} as active: {result['stderr']}")
                return {
                    'success': False,
                    'error': f'Failed to activate namespace: {result["stderr"]}',
                    'method': 'kyverno_label'
                }
            
            # Log the activation
            self.dynamodb_manager.log_namespace_activity(
                namespace_name=namespace,
                operation_type='kyverno_activation',
                cost_center=cost_center,
                requested_by=requested_by or user_id,
                cluster_name=self.cluster_name
            )
            
            logger.info(f"Activated namespace {namespace} using Kyverno label")
            
            return {
                'success': True,
                'message': f'Namespace {namespace} activated using Kyverno policies',
                'method': 'kyverno_label',
                'namespace': namespace,
                'status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Error activating namespace {namespace} with Kyverno: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'kyverno_label'
            }

    def deactivate_namespace_with_kyverno(self, namespace, cost_center='default', user_id='system', requested_by=None):
        """Deactivate a namespace using Kyverno labels instead of direct scaling"""
        try:
            # Set namespace label to inactive
            result = self.execute_kubectl_command(
                f'label namespace {namespace} scheduler.pocarqnube.com/status=inactive --overwrite'
            )
            
            if not result['success']:
                logger.error(f"Failed to label namespace {namespace} as inactive: {result['stderr']}")
                return {
                    'success': False,
                    'error': f'Failed to deactivate namespace: {result["stderr"]}',
                    'method': 'kyverno_label'
                }
            
            # Log the deactivation
            self.dynamodb_manager.log_namespace_activity(
                namespace_name=namespace,
                operation_type='kyverno_deactivation',
                cost_center=cost_center,
                requested_by=requested_by or user_id,
                cluster_name=self.cluster_name
            )
            
            logger.info(f"Deactivated namespace {namespace} using Kyverno label")
            
            return {
                'success': True,
                'message': f'Namespace {namespace} deactivated using Kyverno policies',
                'method': 'kyverno_label',
                'namespace': namespace,
                'status': 'inactive'
            }
            
        except Exception as e:
            logger.error(f"Error deactivating namespace {namespace} with Kyverno: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'kyverno_label'
            }

    def get_namespace_status_kyverno(self, namespace):
        """Get namespace status from Kyverno label"""
        try:
            result = self.execute_kubectl_command(f'get namespace {namespace} -o json')
            
            if not result['success']:
                logger.error(f"Failed to get namespace {namespace}: {result['stderr']}")
                return 'unknown'
            
            namespace_data = json.loads(result['stdout'])
            labels = namespace_data.get('metadata', {}).get('labels', {})
            status = labels.get('scheduler.pocarqnube.com/status', 'active')  # Default to active
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting namespace status for {namespace}: {e}")
            return 'unknown'

    def is_namespace_active_kyverno(self, namespace):
        """Check if namespace is active using Kyverno label"""
        status = self.get_namespace_status_kyverno(namespace)
        return status == 'active'

    def ensure_default_namespace_state_kyverno(self):
        """Ensure default state using Kyverno labels: protected namespaces ON, others based on business hours"""
        try:
            logger.info("Starting default namespace state validation with Kyverno")
            
            # Check if we're in business hours
            is_business_hours = not self.is_non_business_hours()
            
            # Get all namespaces
            result = self.execute_kubectl_command('get namespaces -o json')
            if not result['success']:
                logger.error(f"Failed to get namespaces for default state validation: {result['stderr']}")
                return False
            
            namespaces_data = json.loads(result['stdout'])
            actions_taken = []
            
            for item in namespaces_data['items']:
                namespace_name = item['metadata']['name']
                
                if self.is_protected_namespace(namespace_name):
                    # Protected namespaces should always be active
                    current_status = self.get_namespace_status_kyverno(namespace_name)
                    if current_status != 'active':
                        logger.info(f"Activating protected namespace with Kyverno: {namespace_name}")
                        result = self.activate_namespace_with_kyverno(
                            namespace_name, 
                            cost_center='system',
                            requested_by='system'
                        )
                        if result.get('success'):
                            actions_taken.append(f"Activated protected namespace (Kyverno): {namespace_name}")
                        else:
                            logger.error(f"Failed to activate protected namespace {namespace_name}: {result.get('error')}")
                else:
                    # Non-protected namespaces: active during business hours, inactive otherwise
                    current_status = self.get_namespace_status_kyverno(namespace_name)
                    has_scheduled_tasks = self.has_active_scheduled_tasks(namespace_name)
                    
                    if is_business_hours:
                        # During business hours: activate all non-protected namespaces
                        if current_status != 'active':
                            logger.info(f"Activating namespace for business hours with Kyverno: {namespace_name}")
                            result = self.activate_namespace_with_kyverno(
                                namespace_name,
                                cost_center='system',
                                requested_by='system'
                            )
                            if result.get('success'):
                                actions_taken.append(f"Activated namespace for business hours (Kyverno): {namespace_name}")
                            else:
                                logger.error(f"Failed to activate namespace {namespace_name} for business hours: {result.get('error')}")
                    else:
                        # Outside business hours: deactivate unless they have active scheduled tasks
                        if current_status == 'active' and not has_scheduled_tasks:
                            logger.info(f"Deactivating namespace outside business hours with Kyverno: {namespace_name}")
                            result = self.deactivate_namespace_with_kyverno(
                                namespace_name,
                                cost_center='system',
                                requested_by='system'
                            )
                            if result.get('success'):
                                actions_taken.append(f"Deactivated namespace outside business hours (Kyverno): {namespace_name}")
                            else:
                                logger.error(f"Failed to deactivate namespace {namespace_name} outside business hours: {result.get('error')}")
            
            if actions_taken:
                business_status = "business hours" if is_business_hours else "non-business hours"
                logger.info(f"Default state validation with Kyverno completed during {business_status}. Actions taken: {len(actions_taken)}")
                for action in actions_taken:
                    logger.info(f"  - {action}")
            else:
                business_status = "business hours" if is_business_hours else "non-business hours"
                logger.debug(f"Default state validation with Kyverno completed during {business_status}. No actions needed.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring default namespace state with Kyverno: {e}")
            return False

    def get_active_namespaces_count(self):
        try:
            # Get all namespaces
            result = self.execute_kubectl_command('get namespaces -o json')
            if not result['success']:
                logger.error(f"Failed to get namespaces: {result['stderr']}")
                return 0
            
            namespaces_data = json.loads(result['stdout'])
            active_count = 0
            
            for item in namespaces_data['items']:
                namespace_name = item['metadata']['name']
                
                # Skip system namespaces
                if self.is_system_namespace(namespace_name):
                    continue
                
                # Check if namespace has active resources (running pods)
                if self.is_namespace_active(namespace_name):
                    active_count += 1
            
            return active_count
            
        except Exception as e:
            logger.error(f"Error getting active namespaces count: {e}")
            return 0

    def is_system_namespace(self, namespace_name):
        """Check if a namespace is a system namespace that should be excluded from counts"""
        system_namespaces = [
            'kube-system', 
            'kube-public', 
            'kube-node-lease', 
            'default',
            'kube-apiserver',
            'kube-controller-manager',
            'kube-scheduler',
            'kube-proxy',
            'coredns',
            'calico-system',
            'tigera-operator',
            'amazon-cloudwatch',
            'aws-node',
            'cert-manager',
            'ingress-nginx',
            'monitoring',
            'logging',
            'argocd',
            'task-scheduler'  # Our own namespace
        ]
        return namespace_name in system_namespaces

    def is_protected_namespace(self, namespace_name):
        """Check if a namespace is protected and cannot be activated/deactivated"""
        protected_namespaces = [
            'karpenter',     # Critical for cluster autoscaling
            'kyverno',       # Critical for policy enforcement
            'argocd',        # Critical for CI/CD operations
            'kube-system',   # Core Kubernetes system
            'istio-system',  # Service mesh - critical for networking
            'monitoring',    # Critical for observability
            'task-scheduler' # This application itself
        ]
        return namespace_name in protected_namespaces

    def is_namespace_active(self, namespace_name):
        """Check if a namespace is active (has running pods or scaled deployments)"""
        try:
            # Method 1: Check for running pods
            pods_result = self.execute_kubectl_command(
                f'get pods -n {namespace_name} --field-selector=status.phase=Running -o json'
            )
            
            if pods_result['success']:
                pods_data = json.loads(pods_result['stdout'])
                if len(pods_data.get('items', [])) > 0:
                    return True
            
            # Method 2: Check for deployments with replicas > 0
            deployments_result = self.execute_kubectl_command(
                f'get deployments -n {namespace_name} -o json'
            )
            
            if deployments_result['success']:
                deployments_data = json.loads(deployments_result['stdout'])
                for deployment in deployments_data.get('items', []):
                    replicas = deployment.get('spec', {}).get('replicas', 0)
                    if replicas > 0:
                        return True
            
            # Method 3: Check for statefulsets with replicas > 0
            statefulsets_result = self.execute_kubectl_command(
                f'get statefulsets -n {namespace_name} -o json'
            )
            
            if statefulsets_result['success']:
                statefulsets_data = json.loads(statefulsets_result['stdout'])
                for statefulset in statefulsets_data.get('items', []):
                    replicas = statefulset.get('spec', {}).get('replicas', 0)
                    if replicas > 0:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if namespace {namespace_name} is active: {e}")
            return False

    def get_namespace_details(self, namespace_name):
        """Get detailed information about a namespace's active resources"""
        try:
            details = {
                'name': namespace_name,
                'is_active': False,
                'is_system': self.is_system_namespace(namespace_name),
                'active_pods': 0,
                'deployments': [],
                'statefulsets': [],
                'daemonsets': []
            }
            
            # Get running pods count
            pods_result = self.execute_kubectl_command(
                f'get pods -n {namespace_name} --field-selector=status.phase=Running -o json'
            )
            
            if pods_result['success']:
                pods_data = json.loads(pods_result['stdout'])
                details['active_pods'] = len(pods_data.get('items', []))
            
            # Get deployments info
            deployments_result = self.execute_kubectl_command(
                f'get deployments -n {namespace_name} -o json'
            )
            
            if deployments_result['success']:
                deployments_data = json.loads(deployments_result['stdout'])
                for deployment in deployments_data.get('items', []):
                    name = deployment['metadata']['name']
                    replicas = deployment.get('spec', {}).get('replicas', 0)
                    ready_replicas = deployment.get('status', {}).get('readyReplicas', 0)
                    details['deployments'].append({
                        'name': name,
                        'replicas': replicas,
                        'ready_replicas': ready_replicas
                    })
            
            # Get statefulsets info
            statefulsets_result = self.execute_kubectl_command(
                f'get statefulsets -n {namespace_name} -o json'
            )
            
            if statefulsets_result['success']:
                statefulsets_data = json.loads(statefulsets_result['stdout'])
                for statefulset in statefulsets_data.get('items', []):
                    name = statefulset['metadata']['name']
                    replicas = statefulset.get('spec', {}).get('replicas', 0)
                    ready_replicas = statefulset.get('status', {}).get('readyReplicas', 0)
                    details['statefulsets'].append({
                        'name': name,
                        'replicas': replicas,
                        'ready_replicas': ready_replicas
                    })
            
            # Get daemonsets info
            daemonsets_result = self.execute_kubectl_command(
                f'get daemonsets -n {namespace_name} -o json'
            )
            
            if daemonsets_result['success']:
                daemonsets_data = json.loads(daemonsets_result['stdout'])
                for daemonset in daemonsets_data.get('items', []):
                    name = daemonset['metadata']['name']
                    desired = daemonset.get('status', {}).get('desiredNumberScheduled', 0)
                    ready = daemonset.get('status', {}).get('numberReady', 0)
                    details['daemonsets'].append({
                        'name': name,
                        'desired': desired,
                        'ready': ready
                    })
            
            # Determine if namespace is active
            details['is_active'] = self.is_namespace_active(namespace_name)
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting namespace details for {namespace_name}: {e}")
            return {
                'name': namespace_name,
                'is_active': False,
                'is_system': self.is_system_namespace(namespace_name),
                'active_pods': 0,
                'deployments': [],
                'statefulsets': [],
                'daemonsets': [],
                'error': str(e)
            }

    def load_tasks(self):
        """Load tasks from file with validation and error recovery"""
        try:
            tasks_file = '/app/config/tasks.json'
            backup_file = '/app/config/tasks.json.backup'
            
            # Try to load from main file
            if os.path.exists(tasks_file):
                try:
                    with open(tasks_file, 'r') as f:
                        loaded_tasks = json.load(f)
                    
                    # Validate loaded tasks
                    if self._validate_tasks(loaded_tasks):
                        self.tasks = loaded_tasks
                        logger.info(f"Loaded {len(self.tasks)} tasks from {tasks_file}")
                        return
                    else:
                        logger.warning(f"Tasks file {tasks_file} failed validation, trying backup")
                
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in {tasks_file}: {e}, trying backup")
                except Exception as e:
                    logger.error(f"Error loading tasks from {tasks_file}: {e}, trying backup")
            
            # Try to load from backup if main file failed
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r') as f:
                        loaded_tasks = json.load(f)
                    
                    if self._validate_tasks(loaded_tasks):
                        self.tasks = loaded_tasks
                        logger.info(f"Loaded {len(self.tasks)} tasks from backup {backup_file}")
                        # Restore main file from backup
                        self.save_tasks()
                        return
                    else:
                        logger.error(f"Backup file {backup_file} also failed validation")
                
                except Exception as e:
                    logger.error(f"Error loading tasks from backup {backup_file}: {e}")
            
            # If both failed, start with empty tasks
            logger.warning("Could not load tasks from file or backup, starting with empty task list")
            self.tasks = {}
            
        except Exception as e:
            logger.error(f"Critical error loading tasks: {e}")
            self.tasks = {}

    def _validate_tasks(self, tasks):
        """Validate tasks data structure"""
        try:
            if not isinstance(tasks, dict):
                logger.error("Tasks must be a dictionary")
                return False
            
            # Validate each task
            for task_id, task in tasks.items():
                if not isinstance(task, dict):
                    logger.error(f"Task {task_id} is not a dictionary")
                    return False
                
                # Check required fields
                required_fields = ['title', 'status']
                for field in required_fields:
                    if field not in task:
                        logger.error(f"Task {task_id} missing required field: {field}")
                        return False
                
                # Validate status values
                valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
                if task.get('status') not in valid_statuses:
                    logger.warning(f"Task {task_id} has invalid status: {task.get('status')}, setting to pending")
                    task['status'] = 'pending'
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating tasks: {e}")
            return False

    def save_tasks(self):
        """Save tasks to file with atomic write and backup"""
        try:
            os.makedirs('/app/config', exist_ok=True)
            
            tasks_file = '/app/config/tasks.json'
            temp_file = '/app/config/tasks.json.tmp'
            backup_file = '/app/config/tasks.json.backup'
            
            # Create backup of existing file
            if os.path.exists(tasks_file):
                try:
                    import shutil
                    shutil.copy2(tasks_file, backup_file)
                    logger.debug(f"Created backup: {backup_file}")
                except Exception as e:
                    logger.warning(f"Could not create backup: {e}")
            
            # Write to temporary file first (atomic write)
            with open(temp_file, 'w') as f:
                json.dump(self.tasks, f, indent=2, sort_keys=True)
            
            # Verify the temporary file is valid JSON
            with open(temp_file, 'r') as f:
                json.load(f)
            
            # Rename temporary file to actual file (atomic operation)
            os.replace(temp_file, tasks_file)
            
            logger.debug(f"Saved {len(self.tasks)} tasks to {tasks_file}")
            
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
            # Clean up temporary file if it exists
            if os.path.exists('/app/config/tasks.json.tmp'):
                try:
                    os.remove('/app/config/tasks.json.tmp')
                except:
                    pass

    def export_tasks(self, export_path=None):
        """Export tasks to a file with metadata"""
        try:
            if export_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_path = f'/app/config/tasks_export_{timestamp}.json'
            
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'task_count': len(self.tasks),
                'cluster_name': self.cluster_name,
                'tasks': self.tasks
            }
            
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, sort_keys=True)
            
            logger.info(f"Exported {len(self.tasks)} tasks to {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Error exporting tasks: {e}")
            return None

    def import_tasks(self, import_path, merge=False):
        """
        Import tasks from a file
        
        Args:
            import_path: Path to the import file
            merge: If True, merge with existing tasks. If False, replace all tasks.
        
        Returns:
            Number of tasks imported, or None on error
        """
        try:
            if not os.path.exists(import_path):
                logger.error(f"Import file not found: {import_path}")
                return None
            
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Handle both old format (direct tasks dict) and new format (with metadata)
            if 'tasks' in import_data:
                imported_tasks = import_data['tasks']
                logger.info(f"Importing from export version {import_data.get('version', 'unknown')}")
            else:
                imported_tasks = import_data
            
            # Validate imported tasks
            if not self._validate_tasks(imported_tasks):
                logger.error("Imported tasks failed validation")
                return None
            
            if merge:
                # Merge with existing tasks
                original_count = len(self.tasks)
                self.tasks.update(imported_tasks)
                imported_count = len(self.tasks) - original_count
                logger.info(f"Merged {imported_count} new tasks (total: {len(self.tasks)})")
            else:
                # Replace all tasks
                self.tasks = imported_tasks
                imported_count = len(self.tasks)
                logger.info(f"Replaced all tasks with {imported_count} imported tasks")
            
            self.save_tasks()
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing tasks: {e}")
            return None

    def get_task_statistics(self):
        """Get statistics about tasks"""
        try:
            stats = {
                'total': len(self.tasks),
                'by_status': {},
                'by_operation_type': {},
                'by_cost_center': {},
                'scheduled': 0,
                'one_time': 0,
                'total_runs': 0,
                'total_successes': 0,
                'total_failures': 0
            }
            
            for task in self.tasks.values():
                # Count by status
                status = task.get('status', 'unknown')
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # Count by operation type
                op_type = task.get('operation_type', 'unknown')
                stats['by_operation_type'][op_type] = stats['by_operation_type'].get(op_type, 0) + 1
                
                # Count by cost center
                cost_center = task.get('cost_center', 'unknown')
                stats['by_cost_center'][cost_center] = stats['by_cost_center'].get(cost_center, 0) + 1
                
                # Count scheduled vs one-time
                if task.get('schedule'):
                    stats['scheduled'] += 1
                else:
                    stats['one_time'] += 1
                
                # Aggregate run statistics
                stats['total_runs'] += task.get('run_count', 0)
                stats['total_successes'] += task.get('success_count', 0)
                stats['total_failures'] += task.get('error_count', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            return None

    def cleanup_old_tasks(self, days=30):
        """
        Clean up old completed/failed tasks
        
        Args:
            days: Remove tasks completed/failed more than this many days ago
        
        Returns:
            Number of tasks removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                # Only clean up completed or failed tasks
                if task.get('status') not in ['completed', 'failed']:
                    continue
                
                # Check last_run date
                last_run = task.get('last_run')
                if last_run:
                    try:
                        last_run_date = datetime.fromisoformat(last_run)
                        if last_run_date < cutoff_date:
                            tasks_to_remove.append(task_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid last_run date for task {task_id}: {last_run}")
            
            # Remove old tasks
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                self.save_tasks()
                logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks (older than {days} days)")
            
            return len(tasks_to_remove)
            
        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")
            return 0

    def start_auto_save(self, interval_seconds=300):
        """
        Start automatic periodic saving of tasks
        
        Args:
            interval_seconds: How often to auto-save (default: 300 seconds / 5 minutes)
        """
        def auto_save_loop():
            while True:
                try:
                    time.sleep(interval_seconds)
                    self.save_tasks()
                    logger.debug(f"Auto-saved tasks (interval: {interval_seconds}s)")
                except Exception as e:
                    logger.error(f"Error in auto-save: {e}")
        
        auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        auto_save_thread.start()
        logger.info(f"Started auto-save thread (interval: {interval_seconds}s)")


    def is_non_business_hours(self, timestamp=None):
        """Check if current time is non-business hours with proper timezone handling"""
        import pytz
        from datetime import datetime, time
        
        # Get timezone configuration (default to UTC if not specified)
        timezone_name = os.getenv('BUSINESS_HOURS_TIMEZONE', 'UTC')
        try:
            business_timezone = pytz.timezone(timezone_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{timezone_name}', falling back to UTC")
            business_timezone = pytz.UTC
        
        # Get current time in business timezone
        if timestamp is None:
            # Use current time in business timezone
            current_time = datetime.now(business_timezone)
        elif isinstance(timestamp, (int, float)):
            # Convert Unix timestamp to business timezone
            current_time = datetime.fromtimestamp(timestamp, tz=business_timezone)
        elif isinstance(timestamp, datetime):
            # Convert datetime to business timezone
            if timestamp.tzinfo is None:
                # Assume UTC if no timezone info
                current_time = pytz.UTC.localize(timestamp).astimezone(business_timezone)
            else:
                current_time = timestamp.astimezone(business_timezone)
        else:
            logger.error(f"Invalid timestamp type: {type(timestamp)}")
            current_time = datetime.now(business_timezone)
        
        # Get configurable business hours (default: 7 AM - 8 PM)
        business_start_hour = int(os.getenv('BUSINESS_START_HOUR', '7'))
        business_end_hour = int(os.getenv('BUSINESS_END_HOUR', '20'))  # 8 PM in 24-hour format
        
        # Validate business hours configuration
        if not (0 <= business_start_hour <= 23) or not (0 <= business_end_hour <= 23):
            logger.error(f"Invalid business hours: {business_start_hour}-{business_end_hour}, using defaults")
            business_start_hour, business_end_hour = 7, 20
        
        if business_start_hour >= business_end_hour:
            logger.error(f"Business start hour ({business_start_hour}) must be before end hour ({business_end_hour})")
            business_start_hour, business_end_hour = 7, 20
        
        # Check if it's weekend (Saturday=5, Sunday=6)
        is_weekend = current_time.weekday() >= 5
        
        # Check if it's outside business hours
        current_hour = current_time.hour
        is_outside_hours = current_hour < business_start_hour or current_hour >= business_end_hour
        
        # Check for holidays (if configured)
        is_holiday = self._is_holiday(current_time)
        
        result = is_weekend or is_outside_hours or is_holiday
        
        # Log the decision for debugging
        logger.debug(f"Business hours check: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                    f"(weekday={current_time.weekday()}, hour={current_hour}) "
                    f"-> weekend={is_weekend}, outside_hours={is_outside_hours}, holiday={is_holiday} "
                    f"-> non_business={result}")
        
        return result

    def _is_holiday(self, current_time):
        """Check if the current date is a configured holiday"""
        current_date = current_time.date()
        
        # Method 1: Check manual holidays from environment
        manual_holidays = self._get_manual_holidays()
        if current_date in manual_holidays:
            logger.info(f"Current date {current_date} is a manually configured holiday")
            return True
        
        # Method 2: Check automatic holidays using holidays library
        if self._is_automatic_holiday(current_date):
            return True
        
        return False

    def _get_manual_holidays(self):
        """Get manually configured holidays from environment"""
        holidays_str = os.getenv('BUSINESS_HOLIDAYS', '')
        holiday_dates = []
        
        if not holidays_str:
            return holiday_dates
        
        try:
            for date_str in holidays_str.split(','):
                date_str = date_str.strip()
                if date_str:
                    try:
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        holiday_dates.append(holiday_date)
                    except ValueError:
                        logger.warning(f"Invalid holiday date format: {date_str}")
        except Exception as e:
            logger.error(f"Error parsing manual holidays: {e}")
        
        return holiday_dates

    def _is_automatic_holiday(self, current_date):
        """Check if date is an automatic holiday using holidays library"""
        try:
            import holidays
            
            # Get country and subdivision from environment
            country = os.getenv('BUSINESS_HOLIDAYS_COUNTRY', '')
            subdivision = os.getenv('BUSINESS_HOLIDAYS_SUBDIVISION', '')
            
            if not country:
                return False
            
            # Get the year for the current date
            year = current_date.year
            
            # Create holidays object for the country/subdivision
            if subdivision:
                country_holidays = holidays.country_holidays(country, subdiv=subdivision, years=year)
            else:
                country_holidays = holidays.country_holidays(country, years=year)
            
            is_holiday = current_date in country_holidays
            
            if is_holiday:
                holiday_name = country_holidays.get(current_date, 'Unknown Holiday')
                logger.info(f"Current date {current_date} is an automatic holiday: {holiday_name} ({country})")
            
            return is_holiday
            
        except ImportError:
            logger.debug("holidays library not available, skipping automatic holiday check")
            return False
        except Exception as e:
            logger.error(f"Error checking automatic holidays: {e}")
            return False

    def get_business_hours_info(self):
        """Get current business hours configuration and status"""
        import pytz
        
        # Get configuration
        timezone_name = os.getenv('BUSINESS_HOURS_TIMEZONE', 'UTC')
        business_start_hour = int(os.getenv('BUSINESS_START_HOUR', '7'))
        business_end_hour = int(os.getenv('BUSINESS_END_HOUR', '20'))
        
        try:
            business_timezone = pytz.timezone(timezone_name)
            current_time = datetime.now(business_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            business_timezone = pytz.UTC
            current_time = datetime.now(business_timezone)
        
        # Get manual holidays
        manual_holidays = []
        holidays_str = os.getenv('BUSINESS_HOLIDAYS', '')
        if holidays_str:
            for date_str in holidays_str.split(','):
                date_str = date_str.strip()
                if date_str:
                    try:
                        datetime.strptime(date_str, '%Y-%m-%d')  # Validate format
                        manual_holidays.append(date_str)
                    except ValueError:
                        pass
        
        # Get automatic holidays info
        automatic_holidays_info = self._get_automatic_holidays_info(current_time.year)
        
        is_non_business = self.is_non_business_hours()
        
        return {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'timezone': timezone_name,
            'business_hours': f"{business_start_hour:02d}:00 - {business_end_hour:02d}:00",
            'business_days': 'Monday - Friday',
            'manual_holidays': manual_holidays,
            'automatic_holidays': automatic_holidays_info,
            'is_non_business_hours': is_non_business,
            'current_weekday': current_time.strftime('%A'),
            'current_hour': current_time.hour,
            'limit_active': is_non_business
        }

    def _get_automatic_holidays_info(self, year):
        """Get information about automatic holidays configuration"""
        try:
            import holidays
            
            country = os.getenv('BUSINESS_HOLIDAYS_COUNTRY', '')
            subdivision = os.getenv('BUSINESS_HOLIDAYS_SUBDIVISION', '')
            
            if not country:
                return {
                    'enabled': False,
                    'country': None,
                    'subdivision': None,
                    'holidays_count': 0,
                    'holidays': []
                }
            
            # Get holidays for the year
            if subdivision:
                country_holidays = holidays.country_holidays(country, subdiv=subdivision, years=year)
            else:
                country_holidays = holidays.country_holidays(country, years=year)
            
            # Convert to list of dictionaries with names
            holidays_list = []
            for date, name in sorted(country_holidays.items()):
                holidays_list.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'name': name
                })
            
            return {
                'enabled': True,
                'country': country,
                'subdivision': subdivision,
                'holidays_count': len(holidays_list),
                'holidays': holidays_list
            }
            
        except ImportError:
            return {
                'enabled': False,
                'error': 'holidays library not installed',
                'country': None,
                'subdivision': None,
                'holidays_count': 0,
                'holidays': []
            }
        except Exception as e:
            return {
                'enabled': False,
                'error': str(e),
                'country': os.getenv('BUSINESS_HOLIDAYS_COUNTRY', ''),
                'subdivision': os.getenv('BUSINESS_HOLIDAYS_SUBDIVISION', ''),
                'holidays_count': 0,
                'holidays': []
            }

    def validate_namespace_activation(self, cost_center, namespace, user_id=None, requested_by=None):
        """Validate if namespace can be activated with robust error handling
        
        Args:
            cost_center: Cost center identifier
            namespace: Namespace name to validate
            user_id: User identifier (optional)
            requested_by: User who requested the operation (optional)
        
        Returns:
            tuple: (is_valid: bool, message: str, details: dict)
        """
        try:
            # Input validation
            if not namespace or not isinstance(namespace, str):
                return False, "Invalid namespace name", {'error_type': 'validation_error'}
            
            if not cost_center or not isinstance(cost_center, str):
                return False, "Invalid cost center", {'error_type': 'validation_error'}
            
            # Check if namespace exists
            try:
                result = self.execute_kubectl_command(f'get namespace {namespace} -o json')
                if not result['success']:
                    return False, f"Namespace '{namespace}' does not exist", {'error_type': 'namespace_not_found'}
            except Exception as e:
                logger.error(f"Error checking namespace existence: {e}")
                return False, f"Failed to verify namespace existence: {str(e)}", {'error_type': 'kubectl_error'}
            
            # Check cost center permissions
            try:
                if not self.dynamodb_manager.validate_cost_center_permissions(
                    cost_center, 
                    user_id=user_id,
                    requested_by=requested_by,
                    operation_type='namespace_activation',
                    namespace=namespace,
                    cluster_name=self.cluster_name
                ):
                    return False, f"Cost center '{cost_center}' is not authorized", {'error_type': 'authorization_error'}
            except Exception as e:
                logger.error(f"Error validating cost center permissions: {e}")
                return False, f"Failed to validate permissions: {str(e)}", {'error_type': 'permission_check_error'}
            
            # Check if it's non-business hours
            try:
                is_non_business = self.is_non_business_hours()
            except Exception as e:
                logger.error(f"Error checking business hours: {e}")
                # Default to business hours if check fails (safer)
                is_non_business = False
            
            if not is_non_business:
                return True, "Business hours - no limit", {'limit_applies': False}
            
            # Check namespace limit during non-business hours
            try:
                current_active_count = self.get_active_namespaces_count()
            except Exception as e:
                logger.error(f"Error getting active namespace count: {e}")
                return False, f"Failed to check namespace limits: {str(e)}", {'error_type': 'count_error'}
            
            # If the namespace is already active, don't count it against the limit
            try:
                if self.is_namespace_active(namespace):
                    return True, f"Namespace already active (current active: {current_active_count})", {
                        'already_active': True,
                        'current_active_count': current_active_count
                    }
            except Exception as e:
                logger.error(f"Error checking if namespace is active: {e}")
                # Continue with validation even if this check fails
            
            # Check if we would exceed the limit by activating this namespace
            max_allowed = 5
            if current_active_count >= max_allowed:
                return False, f"Maximum {max_allowed} namespaces allowed during non-business hours (current active: {current_active_count})", {
                    'error_type': 'limit_exceeded',
                    'current_active_count': current_active_count,
                    'max_allowed': max_allowed
                }
            
            return True, f"Validation passed (current active: {current_active_count})", {
                'current_active_count': current_active_count,
                'max_allowed': max_allowed,
                'limit_applies': True
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in validate_namespace_activation: {e}", exc_info=True)
            return False, f"Validation failed due to unexpected error: {str(e)}", {'error_type': 'unexpected_error'}

    def activate_namespace(self, namespace, cost_center, user_id=None, requested_by=None):
        """Activate a namespace with robust error handling
        
        Args:
            namespace: Namespace name to activate
            cost_center: Cost center identifier
            user_id: User identifier (optional)
            requested_by: User who requested the operation (optional)
        
        Returns:
            dict: Result with success status, message, and details
        """
        operation_start_time = time.time()
        user_identifier = requested_by or user_id or 'anonymous'
        
        try:
            # Input validation
            if not namespace or not isinstance(namespace, str):
                logger.warning(f"Invalid namespace parameter: {namespace}")
                return {
                    'success': False, 
                    'error': 'Invalid namespace name',
                    'error_type': 'validation_error'
                }
            
            if not cost_center or not isinstance(cost_center, str):
                logger.warning(f"Invalid cost_center parameter: {cost_center}")
                return {
                    'success': False, 
                    'error': 'Invalid cost center',
                    'error_type': 'validation_error'
                }
            
            logger.info(f"Activating namespace '{namespace}' for cost center '{cost_center}' by user '{user_identifier}'")
            
            # Validate activation
            validation_result = self.validate_namespace_activation(cost_center, namespace, user_id, requested_by)
            
            # Handle both old (2-tuple) and new (3-tuple) return formats
            if len(validation_result) == 3:
                is_valid, message, details = validation_result
            else:
                is_valid, message = validation_result
                details = {}
            
            if not is_valid:
                logger.warning(f"Validation failed for namespace '{namespace}': {message}")
                return {
                    'success': False, 
                    'error': message,
                    'error_type': details.get('error_type', 'validation_failed'),
                    'details': details
                }
            
            # Scale up namespace resources
            try:
                result = self.scale_namespace_resources(namespace, target_replicas=None)
            except Exception as e:
                logger.error(f"Error scaling namespace resources: {e}", exc_info=True)
                return {
                    'success': False, 
                    'error': f'Failed to scale namespace resources: {str(e)}',
                    'error_type': 'scaling_error'
                }
            
            if result['success']:
                # Log activity to DynamoDB
                try:
                    self.dynamodb_manager.log_namespace_activity(
                        namespace_name=namespace,
                        operation_type='manual_activation',
                        cost_center=cost_center,
                        user_id=user_id,
                        requested_by=user_identifier,
                        cluster_name=self.cluster_name
                    )
                except Exception as e:
                    # Log error but don't fail the operation
                    logger.error(f"Failed to log activity to DynamoDB: {e}", exc_info=True)
                
                # Get updated count for response
                try:
                    updated_count = self.get_active_namespaces_count()
                except Exception as e:
                    logger.warning(f"Failed to get updated namespace count: {e}")
                    updated_count = None
                
                operation_duration = time.time() - operation_start_time
                logger.info(f"Successfully activated namespace '{namespace}' in {operation_duration:.2f}s")
                
                response = {
                    'success': True, 
                    'message': f'Namespace {namespace} activated successfully',
                    'namespace': namespace,
                    'cost_center': cost_center,
                    'scaled_resources': result.get('scaled_resources', []),
                    'operation_duration': operation_duration
                }
                
                if updated_count is not None:
                    response['active_namespaces_count'] = updated_count
                
                return response
            else:
                error_msg = result.get('error', 'Failed to activate namespace')
                logger.error(f"Failed to activate namespace '{namespace}': {error_msg}")
                
                return {
                    'success': False, 
                    'error': error_msg,
                    'error_type': 'scaling_failed',
                    'failed_resources': result.get('failed_resources', []),
                    'errors': result.get('errors', [])
                }
                
        except KeyboardInterrupt:
            logger.warning(f"Namespace activation interrupted by user")
            raise
        except Exception as e:
            operation_duration = time.time() - operation_start_time
            logger.error(f"Unexpected error activating namespace '{namespace}' after {operation_duration:.2f}s: {e}", exc_info=True)
            return {
                'success': False, 
                'error': f'Unexpected error: {str(e)}',
                'error_type': 'unexpected_error',
                'operation_duration': operation_duration
            }

    def deactivate_namespace(self, namespace, cost_center, user_id=None, requested_by=None):
        """Deactivate a namespace with robust error handling
        
        Args:
            namespace: Namespace name to deactivate
            cost_center: Cost center identifier
            user_id: User identifier (optional)
            requested_by: User who requested the operation (optional)
        
        Returns:
            dict: Result with success status, message, and details
        """
        operation_start_time = time.time()
        user_identifier = requested_by or user_id or 'anonymous'
        
        try:
            # Input validation
            if not namespace or not isinstance(namespace, str):
                logger.warning(f"Invalid namespace parameter: {namespace}")
                return {
                    'success': False, 
                    'error': 'Invalid namespace name',
                    'error_type': 'validation_error'
                }
            
            if not cost_center or not isinstance(cost_center, str):
                logger.warning(f"Invalid cost_center parameter: {cost_center}")
                return {
                    'success': False, 
                    'error': 'Invalid cost center',
                    'error_type': 'validation_error'
                }
            
            logger.info(f"Deactivating namespace '{namespace}' for cost center '{cost_center}' by user '{user_identifier}'")
            
            # Check if namespace exists
            try:
                result = self.execute_kubectl_command(f'get namespace {namespace} -o json')
                if not result['success']:
                    logger.warning(f"Namespace '{namespace}' does not exist")
                    return {
                        'success': False, 
                        'error': f"Namespace '{namespace}' does not exist",
                        'error_type': 'namespace_not_found'
                    }
            except Exception as e:
                logger.error(f"Error checking namespace existence: {e}")
                return {
                    'success': False, 
                    'error': f"Failed to verify namespace existence: {str(e)}",
                    'error_type': 'kubectl_error'
                }
            
            # Validate cost center permissions before deactivation
            try:
                if not self.dynamodb_manager.validate_cost_center_permissions(
                    cost_center,
                    user_id=user_id,
                    requested_by=requested_by,
                    operation_type='namespace_deactivation',
                    namespace=namespace,
                    cluster_name=self.cluster_name
                ):
                    logger.warning(f"Cost center '{cost_center}' not authorized for deactivation")
                    return {
                        'success': False, 
                        'error': f"Cost center '{cost_center}' is not authorized",
                        'error_type': 'authorization_error'
                    }
            except Exception as e:
                logger.error(f"Error validating cost center permissions: {e}", exc_info=True)
                return {
                    'success': False, 
                    'error': f"Failed to validate permissions: {str(e)}",
                    'error_type': 'permission_check_error'
                }
            
            # Scale down namespace resources
            try:
                result = self.scale_namespace_resources(namespace, target_replicas=0)
            except Exception as e:
                logger.error(f"Error scaling namespace resources: {e}", exc_info=True)
                return {
                    'success': False, 
                    'error': f'Failed to scale namespace resources: {str(e)}',
                    'error_type': 'scaling_error'
                }
            
            if result['success']:
                # Log activity to DynamoDB
                try:
                    self.dynamodb_manager.log_namespace_activity(
                        namespace_name=namespace,
                        operation_type='manual_deactivation',
                        cost_center=cost_center,
                        user_id=user_id,
                        requested_by=user_identifier,
                        cluster_name=self.cluster_name
                    )
                except Exception as e:
                    # Log error but don't fail the operation
                    logger.error(f"Failed to log activity to DynamoDB: {e}", exc_info=True)
                
                # Get updated count for response
                try:
                    updated_count = self.get_active_namespaces_count()
                except Exception as e:
                    logger.warning(f"Failed to get updated namespace count: {e}")
                    updated_count = None
                
                operation_duration = time.time() - operation_start_time
                logger.info(f"Successfully deactivated namespace '{namespace}' in {operation_duration:.2f}s")
                
                response = {
                    'success': True, 
                    'message': f'Namespace {namespace} deactivated successfully',
                    'namespace': namespace,
                    'cost_center': cost_center,
                    'scaled_resources': result.get('scaled_resources', []),
                    'operation_duration': operation_duration
                }
                
                if updated_count is not None:
                    response['active_namespaces_count'] = updated_count
                
                return response
            else:
                error_msg = result.get('error', 'Failed to deactivate namespace')
                logger.error(f"Failed to deactivate namespace '{namespace}': {error_msg}")
                
                return {
                    'success': False, 
                    'error': error_msg,
                    'error_type': 'scaling_failed',
                    'failed_resources': result.get('failed_resources', []),
                    'errors': result.get('errors', [])
                }
                
        except KeyboardInterrupt:
            logger.warning(f"Namespace deactivation interrupted by user")
            raise
        except Exception as e:
            operation_duration = time.time() - operation_start_time
            logger.error(f"Unexpected error deactivating namespace '{namespace}' after {operation_duration:.2f}s: {e}", exc_info=True)
            return {
                'success': False, 
                'error': f'Unexpected error: {str(e)}',
                'error_type': 'unexpected_error',
                'operation_duration': operation_duration
            }

    def scale_namespace_resources(self, namespace, target_replicas, enable_rollback=True):
        """Scale all scalable resources in a namespace with rollback support
        
        Args:
            namespace: The namespace to scale
            target_replicas: Target replica count. Use 0 to scale down, None to restore original, or specific number
            enable_rollback: If True, rollback changes on partial failure (default: True)
        
        Returns:
            dict with success status, scaled resources info, rollback info, and any errors
        """
        try:
            # Only deployments and statefulsets can be scaled (not daemonsets)
            scalable_resources = ['deployments', 'statefulsets']
            scaled_resources = []
            failed_resources = []
            errors = []
            rollback_performed = False
            rollback_results = []
            
            for resource_type in scalable_resources:
                # Get current resources
                result = self.execute_kubectl_command(f'get {resource_type} -n {namespace} -o json')
                
                if not result['success']:
                    logger.warning(f"Failed to get {resource_type} in namespace {namespace}: {result['stderr']}")
                    continue
                
                try:
                    resources_data = json.loads(result['stdout'])
                    items = resources_data.get('items', [])
                    
                    if not items:
                        logger.debug(f"No {resource_type} found in namespace {namespace}")
                        continue
                    
                    for item in items:
                        resource_name = item['metadata']['name']
                        current_replicas = item.get('spec', {}).get('replicas', 0)
                        
                        # Determine target replicas for this resource
                        if target_replicas == 0:
                            # Scale down to 0
                            new_replicas = 0
                        elif target_replicas is None:
                            # Restore: check if we have stored original value
                            # For now, restore to 1 if it was 0, otherwise keep current
                            # TODO: Store original values in DynamoDB or ConfigMap for proper restoration
                            new_replicas = max(current_replicas, 1) if current_replicas == 0 else current_replicas
                        else:
                            # Scale to specific number
                            new_replicas = target_replicas
                        
                        # Skip if already at target
                        if current_replicas == new_replicas:
                            logger.debug(f"{resource_type}/{resource_name} already at {new_replicas} replicas")
                            scaled_resources.append({
                                'type': resource_type,
                                'name': resource_name,
                                'from_replicas': current_replicas,
                                'to_replicas': new_replicas,
                                'status': 'skipped',
                                'reason': 'already at target'
                            })
                            continue
                        
                        # Execute scale command
                        scale_result = self.execute_kubectl_command(
                            f'scale {resource_type} {resource_name} --replicas={new_replicas} -n {namespace}'
                        )
                        
                        if scale_result['success']:
                            logger.info(f"Scaled {resource_type}/{resource_name} from {current_replicas} to {new_replicas} replicas")
                            scaled_resources.append({
                                'type': resource_type,
                                'name': resource_name,
                                'from_replicas': current_replicas,
                                'to_replicas': new_replicas,
                                'status': 'success'
                            })
                        else:
                            error_msg = f"Failed to scale {resource_type}/{resource_name}: {scale_result['stderr']}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                            failed_resources.append({
                                'type': resource_type,
                                'name': resource_name,
                                'from_replicas': current_replicas,
                                'to_replicas': new_replicas,
                                'status': 'failed',
                                'error': scale_result['stderr']
                            })
                            
                            # If rollback is enabled and we have failures, perform rollback
                            if enable_rollback and len(scaled_resources) > 0:
                                logger.warning(f"Failure detected, initiating rollback of {len(scaled_resources)} successfully scaled resources")
                                rollback_results = self._rollback_scaling(namespace, scaled_resources)
                                rollback_performed = True
                                
                                # Stop processing more resources after rollback
                                break
                
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON for {resource_type} in namespace {namespace}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Rollback on JSON parse error if we have successful scales
                    if enable_rollback and len(scaled_resources) > 0:
                        logger.warning(f"JSON parse error detected, initiating rollback")
                        rollback_results = self._rollback_scaling(namespace, scaled_resources)
                        rollback_performed = True
                    break
                    
                except Exception as e:
                    error_msg = f"Error processing {resource_type} in namespace {namespace}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Rollback on unexpected error if we have successful scales
                    if enable_rollback and len(scaled_resources) > 0:
                        logger.warning(f"Unexpected error detected, initiating rollback")
                        rollback_results = self._rollback_scaling(namespace, scaled_resources)
                        rollback_performed = True
                    break
                
                # If rollback was performed, stop processing more resource types
                if rollback_performed:
                    break
            
            # Determine overall success
            has_failures = len(failed_resources) > 0
            has_successes = len(scaled_resources) > 0
            
            result = {
                'success': not has_failures and has_successes,
                'scaled_resources': scaled_resources,
                'failed_resources': failed_resources,
                'total_scaled': len(scaled_resources),
                'total_failed': len(failed_resources),
                'rollback_performed': rollback_performed
            }
            
            if rollback_performed:
                result['rollback_results'] = rollback_results
                result['success'] = False  # Operation failed if rollback was needed
                
                # Count successful rollbacks
                successful_rollbacks = sum(1 for r in rollback_results if r.get('status') == 'success')
                result['rollback_success_count'] = successful_rollbacks
                result['rollback_failed_count'] = len(rollback_results) - successful_rollbacks
            
            if errors:
                result['errors'] = errors
            
            if not has_successes and not has_failures:
                result['message'] = f'No scalable resources found in namespace {namespace}'
                result['success'] = True  # Not an error, just nothing to scale
            
            return result
            
        except Exception as e:
            error_msg = f"Error scaling namespace resources: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'scaled_resources': [],
                'failed_resources': [],
                'total_scaled': 0,
                'total_failed': 0,
                'rollback_performed': False
            }
    
    def _rollback_scaling(self, namespace, scaled_resources):
        """Rollback scaling operations by reverting to original replica counts
        
        Args:
            namespace: The namespace where scaling occurred
            scaled_resources: List of successfully scaled resources to rollback
        
        Returns:
            list: Results of rollback operations
        """
        rollback_results = []
        
        logger.info(f"Starting rollback of {len(scaled_resources)} resources in namespace {namespace}")
        
        for resource in scaled_resources:
            # Skip resources that were skipped (already at target)
            if resource.get('status') == 'skipped':
                continue
            
            resource_type = resource['type']
            resource_name = resource['name']
            original_replicas = resource['from_replicas']
            
            try:
                logger.info(f"Rolling back {resource_type}/{resource_name} to {original_replicas} replicas")
                
                # Execute rollback scale command
                rollback_result = self.execute_kubectl_command(
                    f'scale {resource_type} {resource_name} --replicas={original_replicas} -n {namespace}'
                )
                
                if rollback_result['success']:
                    logger.info(f"Successfully rolled back {resource_type}/{resource_name}")
                    rollback_results.append({
                        'type': resource_type,
                        'name': resource_name,
                        'restored_replicas': original_replicas,
                        'status': 'success'
                    })
                else:
                    logger.error(f"Failed to rollback {resource_type}/{resource_name}: {rollback_result['stderr']}")
                    rollback_results.append({
                        'type': resource_type,
                        'name': resource_name,
                        'restored_replicas': original_replicas,
                        'status': 'failed',
                        'error': rollback_result['stderr']
                    })
            
            except Exception as e:
                logger.error(f"Error during rollback of {resource_type}/{resource_name}: {e}", exc_info=True)
                rollback_results.append({
                    'type': resource_type,
                    'name': resource_name,
                    'restored_replicas': original_replicas,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Rollback completed: {len(rollback_results)} operations performed")
        return rollback_results

    def add_task(self, task_data):
        """Add a new task"""
        task_id = task_data.get('id', str(uuid.uuid4()))
        cost_center = task_data.get('cost_center', 'default')
        namespace = task_data.get('namespace', 'default')
        user_id = task_data.get('user_id', 'anonymous')
        requested_by = task_data.get('requested_by', user_id)
        
        # Validate cost center permissions before creating task
        if not self.dynamodb_manager.validate_cost_center_permissions(
            cost_center,
            user_id=user_id,
            requested_by=requested_by,
            operation_type='task_creation',
            namespace=namespace
        ):
            raise ValueError(f"Cost center '{cost_center}' is not authorized")
        
        # Enhanced task structure for namespace scheduling
        self.tasks[task_id] = {
            'id': task_id,
            'title': task_data.get('title', ''),
            'command': task_data.get('command', ''),
            'schedule': task_data.get('schedule', ''),
            'namespace': namespace,
            'cost_center': cost_center,
            'operation_type': task_data.get('operation_type', 'command'),  # 'command', 'activate', 'deactivate'
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'start': task_data.get('start') or datetime.now().isoformat(),  # Add start field for frontend calendar
            'allDay': task_data.get('allDay', False),  # Add allDay field for frontend calendar
            'created_by': requested_by,  # Track who created the task
            'last_run': None,
            'next_run': self.calculate_next_run(task_data.get('schedule', '')),
            'run_count': 0,
            'success_count': 0,
            'error_count': 0
        }
        
        # Log task creation to DynamoDB
        try:
            self.dynamodb_manager.log_namespace_activity(
                namespace_name=self.tasks[task_id]['namespace'],
                operation_type='task_created',
                cost_center=self.tasks[task_id]['cost_center'],
                user_id=user_id,
                requested_by=requested_by,
                cluster_name=self.cluster_name,
                task_id=task_id,
                task_title=self.tasks[task_id]['title']
            )
        except Exception as e:
            logger.error(f"Error logging task creation to DynamoDB: {e}")
        
        self.save_tasks()
        return self.tasks[task_id]

    def calculate_next_run(self, cron_expression, base_time=None):
        """
        Calculate next run time from cron expression
        
        Args:
            cron_expression: Cron expression string (e.g., "0 9 * * *")
            base_time: Optional base datetime to calculate from. If None, uses current time.
        
        Returns:
            ISO format string of next run time, or None if invalid
        """
        try:
            if not cron_expression:
                return None
            
            # Use provided base_time or current time
            if base_time is None:
                base_time = datetime.now()
            
            # Create croniter instance and get next occurrence
            cron = croniter(cron_expression, base_time)
            next_run = cron.get_next(datetime)
            
            return next_run.isoformat()
        except Exception as e:
            logger.error(f"Error calculating next run for expression '{cron_expression}': {e}")
            return None

    def execute_kubectl_command(self, command, namespace='default'):
        """Execute kubectl command"""
        try:
            # Check if we're running in a Kubernetes pod (service account token exists)
            in_k8s_pod = os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token')
            
            # Only try to set up kubeconfig if not in a K8s pod and kubeconfig doesn't exist
            if not in_k8s_pod and not os.path.exists('/root/.kube/config'):
                # Try to get kubeconfig from AWS EKS
                cluster_name = os.getenv('EKS_CLUSTER_NAME', 'default-cluster')
                region = os.getenv('AWS_REGION', 'us-east-1')
                subprocess.run([
                    'aws', 'eks', 'update-kubeconfig',
                    '--region', region,
                    '--name', cluster_name
                ], check=True)

            # Prepare command
            if not command.startswith('kubectl'):
                command = f'kubectl {command}'
            
            if '-n ' not in command and '--namespace' not in command and namespace != 'default':
                command += f' -n {namespace}'

            logger.info(f"Executing command: {command} (in_k8s_pod: {in_k8s_pod})")
            
            # Prepare environment
            env = os.environ.copy()
            
            # Only set KUBECONFIG if not in a K8s pod
            if not in_k8s_pod and 'KUBECONFIG' not in env:
                env['KUBECONFIG'] = os.path.expanduser('~/.kube/config')
            
            # Debug: Check if AWS credentials are present
            has_aws_creds = 'AWS_ACCESS_KEY_ID' in env and 'AWS_SECRET_ACCESS_KEY' in env
            logger.info(f"Using KUBECONFIG: {env.get('KUBECONFIG', 'service-account-token')}, AWS creds present: {has_aws_creds}")
            
            # Execute command
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env  # Pass environment variables
            )

            if result.returncode != 0:
                logger.error(f"kubectl command failed: {result.stderr}")
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out after 5 minutes',
                'return_code': -1
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }

    def run_task(self, task_id):
        """Run a specific task with improved thread management"""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return False

        # Check if task is already running
        if task_id in self.running_tasks:
            logger.warning(f"Task {task_id} is already running, skipping")
            return False

        task = self.tasks[task_id]
        
        # Create lock for this task if it doesn't exist
        if task_id not in self.task_locks:
            self.task_locks[task_id] = threading.Lock()
        
        # Update task status
        with self.task_locks[task_id]:
            task['status'] = 'running'
            task['last_run'] = datetime.now().isoformat()
            task['run_count'] += 1
            self.save_tasks()
        
        # Submit task to thread pool
        try:
            future = self.executor.submit(self._execute_task_with_retry, task_id)
            self.running_tasks[task_id] = future
            self.task_futures[task_id] = future
            
            # Add callback to clean up when task completes
            future.add_done_callback(lambda f: self._task_completion_callback(task_id, f))
            
            logger.info(f"Task {task_id} ({task.get('title', 'Untitled')}) submitted to thread pool")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting task {task_id} to thread pool: {e}")
            with self.task_locks[task_id]:
                task['status'] = 'failed'
                task['error_count'] += 1
                self.save_tasks()
            return False

    def _task_completion_callback(self, task_id, future):
        """Callback executed when a task completes"""
        try:
            # Remove from running tasks
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            # Check if task completed successfully or with error
            if future.cancelled():
                logger.warning(f"Task {task_id} was cancelled")
            elif future.exception():
                logger.error(f"Task {task_id} raised exception: {future.exception()}")
            else:
                logger.info(f"Task {task_id} completed successfully")
                
        except Exception as e:
            logger.error(f"Error in task completion callback for {task_id}: {e}")

    def _execute_task_with_retry(self, task_id):
        """Execute task with retry logic"""
        task = self.tasks[task_id]
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Executing task {task_id} (attempt {attempt + 1}/{self.max_retries})")
                
                # Execute the task with timeout
                result = self._execute_task_with_timeout(task_id)
                
                if result.get('success', False):
                    logger.info(f"Task {task_id} succeeded on attempt {attempt + 1}")
                    return result
                else:
                    last_error = result.get('error', 'Unknown error')
                    logger.warning(f"Task {task_id} failed on attempt {attempt + 1}: {last_error}")
                    
                    # Don't retry if it's the last attempt
                    if attempt < self.max_retries - 1:
                        logger.info(f"Retrying task {task_id} in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Task {task_id} raised exception on attempt {attempt + 1}: {e}")
                logger.error(traceback.format_exc())
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        # All retries failed
        logger.error(f"Task {task_id} failed after {self.max_retries} attempts")
        return {
            'success': False,
            'error': f"Failed after {self.max_retries} attempts. Last error: {last_error}",
            'stderr': last_error
        }

    def _execute_task_with_timeout(self, task_id):
        """Execute task with timeout"""
        task = self.tasks[task_id]
        
        try:
            # Create a future for the actual task execution
            execution_future = self.executor.submit(self._execute_task, task_id)
            
            # Wait for completion with timeout
            result = execution_future.result(timeout=self.task_timeout)
            return result
            
        except FuturesTimeoutError:
            logger.error(f"Task {task_id} timed out after {self.task_timeout} seconds")
            execution_future.cancel()
            return {
                'success': False,
                'error': f'Task timed out after {self.task_timeout} seconds',
                'stderr': f'Timeout after {self.task_timeout} seconds'
            }
        except Exception as e:
            logger.error(f"Error executing task {task_id} with timeout: {e}")
            return {
                'success': False,
                'error': str(e),
                'stderr': str(e)
            }

    def _execute_task(self, task_id):
        """Execute task in background thread with detailed structured logging"""
        task = self.tasks[task_id]
        start_time = time.time()
        
        # Log task start with context
        log_with_context(
            'info',
            f"Starting task execution: {task.get('title', 'Untitled')}",
            task_id=task_id,
            operation=task.get('operation_type', 'unknown'),
            namespace=task.get('namespace'),
            cost_center=task.get('cost_center')
        )
        
        try:
            # Handle different operation types
            if task.get('operation_type') == 'activate':
                log_with_context(
                    'info',
                    f"Activating namespace",
                    task_id=task_id,
                    namespace=task['namespace'],
                    operation='activate'
                )
                result = self.activate_namespace(
                    task['namespace'], 
                    task['cost_center'],
                    user_id='scheduler',
                    requested_by=f"scheduler-task-{task_id}"
                )
            elif task.get('operation_type') == 'deactivate':
                log_with_context(
                    'info',
                    f"Deactivating namespace",
                    task_id=task_id,
                    namespace=task['namespace'],
                    operation='deactivate'
                )
                result = self.deactivate_namespace(
                    task['namespace'], 
                    task['cost_center'],
                    user_id='scheduler',
                    requested_by=f"scheduler-task-{task_id}"
                )
            else:
                # Regular kubectl command
                log_with_context(
                    'info',
                    f"Executing kubectl command: {task.get('command')}",
                    task_id=task_id,
                    namespace=task.get('namespace', 'default'),
                    operation='kubectl_command'
                )
                result = self.execute_kubectl_command(
                    task['command'],
                    task.get('namespace', 'default')
                )
            
            execution_time = time.time() - start_time
            duration_ms = int(execution_time * 1000)
            
            # Update task status based on result
            with self.task_locks.get(task_id, threading.Lock()):
                if result.get('success', False):
                    task['status'] = 'completed'
                    task['success_count'] += 1
                    
                    log_with_context(
                        'info',
                        f"Task completed successfully",
                        task_id=task_id,
                        namespace=task.get('namespace'),
                        cost_center=task.get('cost_center'),
                        operation=task.get('operation_type'),
                        duration_ms=duration_ms
                    )
                else:
                    task['status'] = 'failed'
                    task['error_count'] += 1
                    error_msg = result.get('stderr', result.get('error', 'Unknown error'))
                    
                    log_with_context(
                        'error',
                        f"Task failed: {error_msg}",
                        task_id=task_id,
                        namespace=task.get('namespace'),
                        cost_center=task.get('cost_center'),
                        operation=task.get('operation_type'),
                        duration_ms=duration_ms
                    )

                # Add to history with detailed information
                history_entry = {
                    'task_id': task_id,
                    'title': task['title'],
                    'command': task.get('command', f"{task.get('operation_type', 'unknown')} {task.get('namespace', 'N/A')}"),
                    'timestamp': datetime.now().isoformat(),
                    'execution_time_seconds': round(execution_time, 2),
                    'success': result.get('success', False),
                    'output': result.get('stdout', result.get('message', ''))[:1000],  # Limit output size
                    'error': result.get('stderr', result.get('error', ''))[:1000],  # Limit error size
                    'operation_type': task.get('operation_type'),
                    'namespace': task.get('namespace'),
                    'cost_center': task.get('cost_center')
                }
                self.task_history.append(history_entry)
                
                # Keep only last 100 history entries
                if len(self.task_history) > 100:
                    self.task_history = self.task_history[-100:]

                # Calculate next run if it's a scheduled task
                if task['schedule']:
                    # Use the original scheduled time as base for calculating next run
                    # This ensures consistent scheduling even if execution is delayed
                    try:
                        original_next_run = datetime.fromisoformat(task['next_run'])
                        task['next_run'] = self.calculate_next_run(task['schedule'], original_next_run)
                        logger.info(f"Next run for task {task_id} scheduled at {task['next_run']}")
                    except (ValueError, TypeError) as e:
                        # Fallback to current time if original next_run is invalid
                        logger.warning(f"Could not parse original next_run for task {task_id}: {e}")
                        task['next_run'] = self.calculate_next_run(task['schedule'])
                    task['status'] = 'pending'
                
                self.save_tasks()
            
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error executing task {task_id} after {execution_time:.2f}s: {e}")
            logger.error(traceback.format_exc())
            
            with self.task_locks.get(task_id, threading.Lock()):
                task['status'] = 'failed'
                task['error_count'] += 1
                
                # Add error to history
                history_entry = {
                    'task_id': task_id,
                    'title': task.get('title', 'Untitled'),
                    'command': task.get('command', 'N/A'),
                    'timestamp': datetime.now().isoformat(),
                    'execution_time_seconds': round(execution_time, 2),
                    'success': False,
                    'output': '',
                    'error': f"Exception: {str(e)}"[:1000],
                    'operation_type': task.get('operation_type'),
                    'namespace': task.get('namespace'),
                    'cost_center': task.get('cost_center')
                }
                self.task_history.append(history_entry)
                
                self.save_tasks()
            
            return {
                'success': False,
                'error': str(e),
                'stderr': str(e)
            }

    def cancel_task(self, task_id):
        """Cancel a running task"""
        if task_id not in self.running_tasks:
            logger.warning(f"Task {task_id} is not running, cannot cancel")
            return False
        
        try:
            future = self.running_tasks[task_id]
            cancelled = future.cancel()
            
            if cancelled:
                logger.info(f"Task {task_id} cancelled successfully")
                with self.task_locks.get(task_id, threading.Lock()):
                    if task_id in self.tasks:
                        self.tasks[task_id]['status'] = 'cancelled'
                        self.save_tasks()
            else:
                logger.warning(f"Task {task_id} could not be cancelled (already running or completed)")
            
            return cancelled
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    def cleanup_completed_tasks(self):
        """Clean up completed task futures from tracking"""
        completed_task_ids = []
        
        for task_id, future in list(self.running_tasks.items()):
            if future.done():
                completed_task_ids.append(task_id)
        
        for task_id in completed_task_ids:
            del self.running_tasks[task_id]
            if task_id in self.task_futures:
                del self.task_futures[task_id]
        
        if completed_task_ids:
            logger.debug(f"Cleaned up {len(completed_task_ids)} completed task futures")
        
        return len(completed_task_ids)

    def get_thread_pool_stats(self):
        """Get thread pool statistics"""
        return {
            'max_workers': self.max_workers,
            'running_tasks': len(self.running_tasks),
            'task_timeout': self.task_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'total_tasks': len(self.tasks),
            'pending_tasks': len([t for t in self.tasks.values() if t.get('status') == 'pending']),
            'completed_tasks': len([t for t in self.tasks.values() if t.get('status') == 'completed']),
            'failed_tasks': len([t for t in self.tasks.values() if t.get('status') == 'failed'])
        }

    def start_scheduler(self):
        """Start the task scheduler with periodic cleanup and default state validation"""
        def scheduler_loop():
            cleanup_counter = 0
            default_validation_counter = 0
            
            while True:
                try:
                    now = datetime.now()
                    
                    # Check for tasks that need to run
                    for task_id, task in list(self.tasks.items()):
                        if (task['status'] == 'pending' and 
                            task.get('next_run') and 
                            datetime.fromisoformat(task['next_run']) <= now and
                            task_id not in self.running_tasks):
                            
                            logger.info(f"Running scheduled task: {task.get('title', task_id)}")
                            self.run_task(task_id)
                    
                    # Periodic cleanup of completed task futures (every 5 minutes)
                    cleanup_counter += 1
                    if cleanup_counter >= 5:
                        cleaned = self.cleanup_completed_tasks()
                        if cleaned > 0:
                            logger.info(f"Periodic cleanup: removed {cleaned} completed task futures")
                        cleanup_counter = 0
                    
                    # Default namespace state validation (every 15 minutes)
                    default_validation_counter += 1
                    if default_validation_counter >= 15 and self.default_validation_enabled:
                        logger.info("Starting periodic default namespace state validation")
                        self.ensure_default_namespace_state()
                        default_validation_counter = 0
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    logger.error(traceback.format_exc())
                    time.sleep(60)

        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Task scheduler started with periodic cleanup and default state validation")

    def get_weekly_scheduled_tasks(self, week_start_date):
        """
        Get all scheduled tasks for a specific week
        
        Args:
            week_start_date: datetime object representing the start of the week (Monday)
        
        Returns:
            List of tasks that are scheduled to run during the specified week
        """
        try:
            from datetime import timedelta
            
            # Calculate week end date (Sunday)
            week_end_date = week_start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            weekly_tasks = []
            
            # Iterate through all tasks
            for task_id, task in self.tasks.items():
                # Skip tasks without schedule (one-time tasks)
                if not task.get('schedule'):
                    continue
                
                # Skip non-pending tasks for future scheduling
                if task.get('status') not in ['pending', 'running']:
                    continue
                
                # Skip tasks for protected namespaces (they don't appear in weekly view)
                namespace = task.get('namespace', '')
                if self.is_protected_namespace(namespace):
                    continue
                
                try:
                    # Get all occurrences of this task during the week
                    task_occurrences = self._get_task_occurrences_in_week(
                        task, week_start_date, week_end_date
                    )
                    
                    # Add each occurrence to the weekly tasks list
                    for occurrence in task_occurrences:
                        weekly_task = {
                            'task_id': task_id,
                            'title': task.get('title', ''),
                            'namespace': task.get('namespace', ''),
                            'cost_center': task.get('cost_center', ''),
                            'operation_type': task.get('operation_type', ''),
                            'schedule': task.get('schedule', ''),
                            'scheduled_time': occurrence['scheduled_time'],
                            'day_of_week': occurrence['day_of_week'],
                            'hour': occurrence['hour'],
                            'minute': occurrence['minute'],
                            'created_by': task.get('created_by', ''),
                            'status': task.get('status', 'pending')
                        }
                        weekly_tasks.append(weekly_task)
                        
                except Exception as task_error:
                    logger.error(f"Error processing task {task_id} for weekly schedule: {task_error}")
                    continue
            
            # Sort by scheduled time
            weekly_tasks.sort(key=lambda x: x['scheduled_time'])
            
            logger.info(f"Found {len(weekly_tasks)} scheduled task occurrences for week starting {week_start_date.strftime('%Y-%m-%d')}")
            return weekly_tasks
            
        except Exception as e:
            logger.error(f"Error getting weekly scheduled tasks: {e}")
            return []

    def _get_task_occurrences_in_week(self, task, week_start, week_end):
        """
        Get all occurrences of a task within a specific week
        
        Args:
            task: Task dictionary
            week_start: Start of week datetime
            week_end: End of week datetime
        
        Returns:
            List of occurrence dictionaries with scheduled_time, day_of_week, hour, minute
        """
        try:
            cron_expression = task.get('schedule', '')
            if not cron_expression:
                return []
            
            occurrences = []
            
            # Use croniter to find all occurrences in the week
            cron = croniter(cron_expression, week_start)
            
            # Get up to 50 occurrences to prevent infinite loops
            max_occurrences = 50
            occurrence_count = 0
            
            while occurrence_count < max_occurrences:
                next_occurrence = cron.get_next(datetime)
                
                # If we've passed the end of the week, stop
                if next_occurrence > week_end:
                    break
                
                # Add this occurrence
                occurrences.append({
                    'scheduled_time': next_occurrence.isoformat(),
                    'day_of_week': next_occurrence.weekday(),  # 0=Monday, 6=Sunday
                    'hour': next_occurrence.hour,
                    'minute': next_occurrence.minute
                })
                
                occurrence_count += 1
            
            return occurrences
            
        except Exception as e:
            logger.error(f"Error getting task occurrences: {e}")
            return []

    def process_weekly_tasks_to_time_slots(self, weekly_tasks, week_start_date):
        """
        Process weekly tasks into a 7x24 time slot grid structure
        
        Args:
            weekly_tasks: List of task occurrences from get_weekly_scheduled_tasks
            week_start_date: datetime object representing the start of the week
        
        Returns:
            Dictionary with time slots organized by day and hour
        """
        try:
            from datetime import timedelta
            
            # Initialize the time slots structure
            time_slots = {}
            
            # Days of the week (0=Monday, 6=Sunday)
            day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            # Initialize empty slots for each day and hour
            for day_index, day_name in enumerate(day_names):
                time_slots[day_name] = {}
                for hour in range(24):
                    time_slots[day_name][f"{hour:02d}"] = []
            
            # Process each task occurrence
            for task in weekly_tasks:
                try:
                    # Parse the scheduled time
                    scheduled_time = datetime.fromisoformat(task['scheduled_time'])
                    
                    # Get day of week and hour
                    day_of_week = scheduled_time.weekday()  # 0=Monday, 6=Sunday
                    hour = scheduled_time.hour
                    
                    # Get the day name
                    day_name = day_names[day_of_week]
                    hour_key = f"{hour:02d}"
                    
                    # Create the task slot data
                    task_slot = {
                        'task_id': task['task_id'],
                        'namespace_id': task['namespace'],
                        'namespace_name': task['namespace'],
                        'cost_center': task['cost_center'],
                        'title': task['title'],
                        'operation_type': task['operation_type'],
                        'scheduled_time': task['scheduled_time'],
                        'minute': task['minute'],
                        'is_active': task['operation_type'] == 'activate',
                        'schedule_type': 'cron',
                        'duration': self._estimate_task_duration(task),
                        'created_by': task.get('created_by', ''),
                        'status': task.get('status', 'pending')
                    }
                    
                    # Add to the appropriate time slot
                    time_slots[day_name][hour_key].append(task_slot)
                    
                except Exception as task_error:
                    logger.error(f"Error processing task {task.get('task_id', 'unknown')} into time slots: {task_error}")
                    continue
            
            # Sort tasks within each time slot by minute
            for day_name in day_names:
                for hour_key in time_slots[day_name]:
                    time_slots[day_name][hour_key].sort(key=lambda x: x['minute'])
            
            logger.info(f"Processed {len(weekly_tasks)} tasks into time slots for week starting {week_start_date.strftime('%Y-%m-%d')}")
            return time_slots
            
        except Exception as e:
            logger.error(f"Error processing weekly tasks to time slots: {e}")
            return {}

    def _estimate_task_duration(self, task):
        """
        Estimate task duration in minutes based on operation type
        
        Args:
            task: Task dictionary
        
        Returns:
            Estimated duration in minutes
        """
        operation_type = task.get('operation_type', 'command')
        
        # Default durations based on operation type
        duration_map = {
            'activate': 5,      # Namespace activation typically takes a few minutes
            'deactivate': 2,    # Deactivation is usually faster
            'command': 1        # Custom commands vary, default to 1 minute
        }
        
        return duration_map.get(operation_type, 1)

    def format_weekly_schedule_response(self, week_start_date, time_slots):
        """
        Format weekly schedule data for frontend consumption
        
        Args:
            week_start_date: datetime object representing the start of the week
            time_slots: Time slots dictionary from process_weekly_tasks_to_time_slots
        
        Returns:
            Formatted response dictionary for the frontend
        """
        try:
            from datetime import timedelta
            
            # Calculate week end date
            week_end_date = week_start_date + timedelta(days=6)
            
            # Format the response
            response = {
                'success': True,
                'data': {
                    'week_start_date': week_start_date.strftime('%Y-%m-%d'),
                    'week_end_date': week_end_date.strftime('%Y-%m-%d'),
                    'time_slots': time_slots,
                    'metadata': {
                        'total_tasks': self._count_total_tasks_in_slots(time_slots),
                        'active_namespaces': self._get_unique_namespaces_in_slots(time_slots),
                        'cost_centers': self._get_unique_cost_centers_in_slots(time_slots),
                        'generated_at': datetime.now().isoformat(),
                        'timezone': 'UTC'  # TODO: Make this configurable
                    }
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting weekly schedule response: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def _count_total_tasks_in_slots(self, time_slots):
        """Count total number of tasks across all time slots"""
        total = 0
        for day_slots in time_slots.values():
            for hour_tasks in day_slots.values():
                total += len(hour_tasks)
        return total

    def _get_unique_namespaces_in_slots(self, time_slots):
        """Get list of unique namespaces in the time slots"""
        namespaces = set()
        for day_slots in time_slots.values():
            for hour_tasks in day_slots.values():
                for task in hour_tasks:
                    namespaces.add(task['namespace_name'])
        return sorted(list(namespaces))

    def _get_unique_cost_centers_in_slots(self, time_slots):
        """Get list of unique cost centers in the time slots"""
        cost_centers = set()
        for day_slots in time_slots.values():
            for hour_tasks in day_slots.values():
                for task in hour_tasks:
                    cost_centers.add(task['cost_center'])
        return sorted(list(cost_centers))

    def get_weekly_schedule_cached(self, week_start_date):
        """
        Get weekly schedule with caching support
        
        Args:
            week_start_date: datetime object representing the start of the week
        
        Returns:
            Formatted weekly schedule response
        """
        try:
            # Check cache first if enabled
            if self.weekly_cache_enabled:
                cached_data = self._get_weekly_cache(week_start_date)
                if cached_data is not None:
                    logger.debug(f"Weekly cache hit for {week_start_date.strftime('%Y-%m-%d')}")
                    return cached_data
            
            # Cache miss - generate fresh data
            logger.debug(f"Weekly cache miss for {week_start_date.strftime('%Y-%m-%d')}, generating fresh data")
            
            # Get all scheduled tasks for the week
            weekly_tasks = self.get_weekly_scheduled_tasks(week_start_date)
            
            # Process tasks into time slots
            time_slots = self.process_weekly_tasks_to_time_slots(weekly_tasks, week_start_date)
            
            # Format response for frontend
            response = self.format_weekly_schedule_response(week_start_date, time_slots)
            
            # Cache the result if caching is enabled
            if self.weekly_cache_enabled:
                self._put_weekly_cache(week_start_date, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting cached weekly schedule: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def _get_weekly_cache(self, week_start_date):
        """Get weekly schedule data from cache"""
        try:
            cache_key = week_start_date.strftime('%Y-%m-%d')
            
            if cache_key in self.weekly_cache:
                cache_entry = self.weekly_cache[cache_key]
                
                # Check if cache entry is still valid
                if time.time() - cache_entry['timestamp'] < self.weekly_cache_ttl:
                    return cache_entry['data']
                else:
                    # Cache expired, remove it
                    logger.debug(f"Weekly cache expired for {cache_key}")
                    del self.weekly_cache[cache_key]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting weekly cache: {e}")
            return None

    def _put_weekly_cache(self, week_start_date, data):
        """Put weekly schedule data in cache"""
        try:
            cache_key = week_start_date.strftime('%Y-%m-%d')
            
            self.weekly_cache[cache_key] = {
                'data': data,
                'timestamp': time.time()
            }
            
            logger.debug(f"Cached weekly schedule for {cache_key}")
            
            # Clean up old cache entries to prevent memory leaks
            self._cleanup_weekly_cache()
            
        except Exception as e:
            logger.error(f"Error putting weekly cache: {e}")

    def _cleanup_weekly_cache(self):
        """Clean up expired cache entries"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for cache_key, cache_entry in self.weekly_cache.items():
                if current_time - cache_entry['timestamp'] >= self.weekly_cache_ttl:
                    expired_keys.append(cache_key)
            
            for key in expired_keys:
                del self.weekly_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired weekly cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up weekly cache: {e}")

    def invalidate_weekly_cache(self, week_start_date=None):
        """
        Invalidate weekly cache for a specific week or all cache
        
        Args:
            week_start_date: Optional datetime object. If None, clears all cache
        """
        try:
            if week_start_date:
                cache_key = week_start_date.strftime('%Y-%m-%d')
                if cache_key in self.weekly_cache:
                    del self.weekly_cache[cache_key]
                    logger.info(f"Invalidated weekly cache for {cache_key}")
            else:
                cache_count = len(self.weekly_cache)
                self.weekly_cache.clear()
                logger.info(f"Invalidated all weekly cache ({cache_count} entries)")
                
        except Exception as e:
            logger.error(f"Error invalidating weekly cache: {e}")

    def get_weekly_cache_stats(self):
        """Get weekly cache statistics"""
        try:
            return {
                'enabled': self.weekly_cache_enabled,
                'ttl_seconds': self.weekly_cache_ttl,
                'cached_entries': len(self.weekly_cache),
                'cache_keys': list(self.weekly_cache.keys()),
                'total_memory_entries': len(self.weekly_cache)
            }
        except Exception as e:
            logger.error(f"Error getting weekly cache stats: {e}")
            return {
                'enabled': False,
                'error': str(e)
            }

# Initialize scheduler
scheduler = TaskScheduler()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with detailed thread pool status"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tasks_count': len(scheduler.tasks),
        'running_tasks': len(scheduler.running_tasks),
        'thread_pool': {
            'max_workers': scheduler.max_workers,
            'active_threads': len(scheduler.running_tasks),
            'task_timeout': scheduler.task_timeout,
            'max_retries': scheduler.max_retries
        }
    })

@app.route('/api/business-hours', methods=['GET'])
def get_business_hours_status():
    """Get current business hours status and configuration"""
    try:
        business_info = scheduler.get_business_hours_info()
        is_business_hours = not scheduler.is_non_business_hours()
        
        return jsonify({
            'success': True,
            'is_business_hours': is_business_hours,
            'business_hours_info': business_info,
            'protected_namespaces_count': len(scheduler.protected_namespaces),
            'next_validation': 'Every 15 minutes'
        })
    except Exception as e:
        logger.error(f"Error getting business hours status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/business-hours/test-validation', methods=['POST'])
def test_business_hours_validation():
    """Test the business hours validation logic (manual trigger)"""
    try:
        result = scheduler.ensure_default_namespace_state()
        
        return jsonify({
            'success': True,
            'validation_completed': result,
            'message': 'Business hours validation completed successfully' if result else 'Validation failed',
            'timestamp': datetime.now().isoformat(),
            'method': 'traditional_scaling'
        })
    except Exception as e:
        logger.error(f"Error testing business hours validation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/business-hours/test-validation-kyverno', methods=['POST'])
def test_business_hours_validation_kyverno():
    """Test the business hours validation logic using Kyverno (manual trigger)"""
    try:
        result = scheduler.ensure_default_namespace_state_kyverno()
        
        return jsonify({
            'success': True,
            'validation_completed': result,
            'message': 'Business hours validation with Kyverno completed successfully' if result else 'Validation failed',
            'timestamp': datetime.now().isoformat(),
            'method': 'kyverno_labels'
        })
    except Exception as e:
        logger.error(f"Error testing business hours validation with Kyverno: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/namespaces/<namespace>/activate-kyverno', methods=['POST'])
def activate_namespace_kyverno(namespace):
    """Activate a namespace using Kyverno labels"""
    try:
        # Check if namespace is protected
        if scheduler.is_protected_namespace(namespace):
            return jsonify({
                'success': False,
                'error': f'Namespace "{namespace}" is protected and cannot be activated/deactivated',
                'protected': True,
                'reason': 'This namespace is critical for cluster operations'
            }), 403
        
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        requested_by = data.get('requested_by', user_id)
        
        result = scheduler.activate_namespace_with_kyverno(namespace, cost_center, user_id, requested_by)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error activating namespace {namespace} with Kyverno: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces/<namespace>/deactivate-kyverno', methods=['POST'])
def deactivate_namespace_kyverno(namespace):
    """Deactivate a namespace using Kyverno labels"""
    try:
        # Check if namespace is protected
        if scheduler.is_protected_namespace(namespace):
            return jsonify({
                'success': False,
                'error': f'Namespace "{namespace}" is protected and cannot be activated/deactivated',
                'protected': True,
                'reason': 'This namespace is critical for cluster operations'
            }), 403
        
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        requested_by = data.get('requested_by', user_id)
        
        result = scheduler.deactivate_namespace_with_kyverno(namespace, cost_center, user_id, requested_by)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error deactivating namespace {namespace} with Kyverno: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/running', methods=['GET'])
def get_running_tasks():
    """Get currently running tasks with status"""
    running_tasks_info = []
    for task_id, future in scheduler.running_tasks.items():
        if task_id in scheduler.tasks:
            task = scheduler.tasks[task_id]
            running_tasks_info.append({
                'task_id': task_id,
                'title': task.get('title', 'Untitled'),
                'status': task.get('status', 'unknown'),
                'last_run': task.get('last_run'),
                'run_count': task.get('run_count', 0),
                'is_done': future.done() if future else False,
                'is_cancelled': future.cancelled() if future else False
            })
    return jsonify(running_tasks_info)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    return jsonify(list(scheduler.tasks.values()))

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        task_data = request.get_json()
        
        # Validate required fields
        if not task_data.get('cost_center'):
            return jsonify({'error': 'cost_center is required'}), 400
        
        task = scheduler.add_task(task_data)
        return jsonify(task), 201
    except ValueError as e:
        # Cost center validation error
        logger.warning(f"Task creation failed: {e}")
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get specific task"""
    if task_id in scheduler.tasks:
        return jsonify(scheduler.tasks[task_id])
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    if task_id in scheduler.tasks:
        del scheduler.tasks[task_id]
        scheduler.save_tasks()
        return jsonify({'message': 'Task deleted'})
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<task_id>/run', methods=['POST'])
def run_task_now(task_id):
    """Run a task immediately"""
    if scheduler.run_task(task_id):
        return jsonify({'message': 'Task started'})
    return jsonify({'error': 'Task not found or already running'}), 400

@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running task"""
    if scheduler.cancel_task(task_id):
        return jsonify({'message': 'Task cancelled successfully'})
    return jsonify({'error': 'Task not found or not running'}), 400

@app.route('/api/tasks/stats', methods=['GET'])
def get_task_stats():
    """Get thread pool and task statistics"""
    stats = scheduler.get_thread_pool_stats()
    task_stats = scheduler.get_task_statistics()
    
    # Merge both statistics
    if task_stats:
        stats.update(task_stats)
    
    return jsonify(stats)

@app.route('/api/tasks/export', methods=['POST'])
def export_tasks():
    """Export all tasks to a file"""
    try:
        data = request.get_json() or {}
        export_path = data.get('path')
        
        result_path = scheduler.export_tasks(export_path)
        
        if result_path:
            return jsonify({
                'success': True,
                'message': 'Tasks exported successfully',
                'path': result_path,
                'task_count': len(scheduler.tasks)
            })
        else:
            return jsonify({'error': 'Failed to export tasks'}), 500
    
    except Exception as e:
        logger.error(f"Error in export endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/import', methods=['POST'])
def import_tasks():
    """Import tasks from a file"""
    try:
        data = request.get_json()
        import_path = data.get('path')
        merge = data.get('merge', False)
        
        if not import_path:
            return jsonify({'error': 'Import path is required'}), 400
        
        imported_count = scheduler.import_tasks(import_path, merge=merge)
        
        if imported_count is not None:
            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_count} tasks',
                'imported_count': imported_count,
                'total_tasks': len(scheduler.tasks),
                'merge': merge
            })
        else:
            return jsonify({'error': 'Failed to import tasks'}), 500
    
    except Exception as e:
        logger.error(f"Error in import endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Clean up old completed/failed tasks"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        removed_count = scheduler.cleanup_old_tasks(days=days)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {removed_count} old tasks',
            'removed_count': removed_count,
            'remaining_tasks': len(scheduler.tasks)
        })
    
    except Exception as e:
        logger.error(f"Error in cleanup endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute', methods=['POST'])
def execute_command():
    """Execute kubectl command directly"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        namespace = data.get('namespace', 'default')
        
        if not command:
            return jsonify({'error': 'Command is required'}), 400

        result = scheduler.execute_kubectl_command(command, namespace)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get execution logs with filtering"""
    try:
        limit = request.args.get('limit', 50, type=int)
        task_id = request.args.get('task_id')
        namespace = request.args.get('namespace')
        cost_center = request.args.get('cost_center')
        success = request.args.get('success')
        
        logs = scheduler.task_history
        
        # Apply filters
        if task_id:
            logs = [log for log in logs if log.get('task_id') == task_id]
        if namespace:
            logs = [log for log in logs if log.get('namespace') == namespace]
        if cost_center:
            logs = [log for log in logs if log.get('cost_center') == cost_center]
        if success is not None:
            success_bool = success.lower() == 'true'
            logs = [log for log in logs if log.get('success') == success_bool]
        
        # Return last N logs
        logs = logs[-limit:]
        
        return jsonify({
            'logs': logs,
            'total': len(logs),
            'limit': limit
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/file', methods=['GET'])
def get_log_file():
    """Get logs from log file"""
    try:
        lines = request.args.get('lines', 100, type=int)
        log_file = os.getenv('LOG_FILE', '/app/logs/app.log')
        
        if not os.path.exists(log_file):
            return jsonify({'error': 'Log file not found'}), 404
        
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
        
        return jsonify({
            'lines': last_lines,
            'total_lines': len(last_lines),
            'file': log_file
        })
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/level', methods=['GET'])
def get_log_level():
    """Get current log level"""
    return jsonify({
        'level': logging.getLevelName(logger.level),
        'numeric_level': logger.level
    })

@app.route('/api/logs/level', methods=['POST'])
def set_log_level():
    """Set log level dynamically"""
    try:
        data = request.get_json()
        level = data.get('level', 'INFO').upper()
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            return jsonify({'error': f'Invalid log level. Must be one of: {valid_levels}'}), 400
        
        logger.setLevel(getattr(logging, level))
        
        logger.info(f"Log level changed to {level}")
        
        return jsonify({
            'message': f'Log level set to {level}',
            'level': level
        })
    except Exception as e:
        logger.error(f"Error setting log level: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cluster/info', methods=['GET'])
def get_cluster_info():
    """Get cluster information"""
    try:
        result = scheduler.execute_kubectl_command('cluster-info')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting cluster info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces', methods=['GET'])
def get_namespaces():
    """Get all namespaces"""
    try:
        result = scheduler.execute_kubectl_command('get namespaces -o json')
        if result['success']:
            namespaces_data = json.loads(result['stdout'])
            namespaces = [item['metadata']['name'] for item in namespaces_data['items']]
            return jsonify(namespaces)
        else:
            return jsonify({'error': result['stderr']}), 500
    except Exception as e:
        logger.error(f"Error getting namespaces: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces/schedulable', methods=['GET'])
def get_schedulable_namespaces():
    """Get namespaces that can be scheduled (non-protected)"""
    try:
        # Get basic list of schedulable namespaces (fast)
        schedulable_namespaces = scheduler.get_schedulable_namespaces()
        
        # For the modal, we only need basic info - don't fetch detailed resource info
        # This makes the endpoint much faster
        namespace_details = []
        for namespace in schedulable_namespaces:
            # Only get basic active status, skip detailed resource queries
            is_active = scheduler.is_namespace_active(namespace)
            namespace_details.append({
                'name': namespace,
                'is_active': is_active,
                'is_protected': False  # These are all non-protected by definition
            })
        
        logger.info(f"Returning {len(namespace_details)} schedulable namespaces")
        
        return jsonify({
            'success': True,
            'schedulable_namespaces': namespace_details,
            'total_count': len(namespace_details),
            'protected_count': len(scheduler.protected_namespaces)
        })
        
    except Exception as e:
        logger.error(f"Error getting schedulable namespaces: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/namespaces/<namespace>/activate', methods=['POST'])
def activate_namespace(namespace):
    """Activate a namespace"""
    try:
        # Check if namespace is protected
        if scheduler.is_protected_namespace(namespace):
            return jsonify({
                'success': False,
                'error': f'Namespace "{namespace}" is protected and cannot be activated/deactivated',
                'protected': True,
                'reason': 'This namespace is critical for cluster operations'
            }), 403
        
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        requested_by = data.get('requested_by', user_id)  # Capture requested_by
        
        result = scheduler.activate_namespace(namespace, cost_center, user_id, requested_by)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error activating namespace {namespace}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces/<namespace>/deactivate', methods=['POST'])
def deactivate_namespace(namespace):
    """Deactivate a namespace"""
    try:
        # Check if namespace is protected
        if scheduler.is_protected_namespace(namespace):
            return jsonify({
                'success': False,
                'error': f'Namespace "{namespace}" is protected and cannot be activated/deactivated',
                'protected': True,
                'reason': 'This namespace is critical for cluster operations'
            }), 403
        
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        requested_by = data.get('requested_by', user_id)  # Capture requested_by
        
        result = scheduler.deactivate_namespace(namespace, cost_center, user_id, requested_by)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error deactivating namespace {namespace}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces/status', methods=['GET'])
def get_namespaces_status():
    """Get status of all namespaces with accurate active counting"""
    try:
        # Get all namespaces
        result = scheduler.execute_kubectl_command('get namespaces -o json')
        if not result['success']:
            return jsonify({'error': result['stderr']}), 500
        
        namespaces_data = json.loads(result['stdout'])
        namespace_status = []
        total_active_count = 0
        user_namespaces_active = 0
        
        for item in namespaces_data['items']:
            namespace_name = item['metadata']['name']
            
            # Get detailed namespace information
            details = scheduler.get_namespace_details(namespace_name)
            namespace_status.append(details)
            
            # Count active namespaces
            if details['is_active']:
                total_active_count += 1
                # Count non-system namespaces separately
                if not details['is_system']:
                    user_namespaces_active += 1
        
        return jsonify({
            'namespaces': namespace_status,
            'total_active_count': total_active_count,
            'user_namespaces_active': user_namespaces_active,
            'active_count': user_namespaces_active,  # For backward compatibility
            'is_non_business_hours': scheduler.is_non_business_hours(),
            'max_allowed_during_non_business': 5,
            'limit_applies': scheduler.is_non_business_hours()
        })
        
    except Exception as e:
        logger.error(f"Error getting namespace status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cost-centers', methods=['GET'])
def get_cost_centers():
    """Get all cost centers and their permissions"""
    try:
        # This would typically come from a database or configuration
        # For now, return some default cost centers
        cost_centers = [
            {'name': 'development', 'is_authorized': True, 'max_concurrent': 5},
            {'name': 'testing', 'is_authorized': True, 'max_concurrent': 3},
            {'name': 'production', 'is_authorized': False, 'max_concurrent': 0},
            {'name': 'default', 'is_authorized': True, 'max_concurrent': 2}
        ]
        return jsonify(cost_centers)
    except Exception as e:
        logger.error(f"Error getting cost centers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cost-centers/<cost_center>/validate', methods=['GET'])
def validate_cost_center(cost_center):
    """Validate if a cost center has permissions"""
    try:
        # Get optional audit parameters from query string
        user_id = request.args.get('user_id', 'api_request')
        requested_by = request.args.get('requested_by', user_id)  # Capture requested_by
        operation_type = request.args.get('operation_type', 'permission_check')
        namespace = request.args.get('namespace')
        
        is_authorized = scheduler.dynamodb_manager.validate_cost_center_permissions(
            cost_center,
            user_id=user_id,
            requested_by=requested_by,
            operation_type=operation_type,
            namespace=namespace,
            cluster_name=scheduler.cluster_name
        )
        
        # Get additional details if authorized
        details = None
        if is_authorized:
            try:
                response = scheduler.dynamodb_manager.permissions_table.get_item(
                    Key={'cost_center': cost_center}
                )
                if 'Item' in response:
                    details = {
                        'cost_center': cost_center,
                        'is_authorized': response['Item'].get('is_authorized', False),
                        'max_concurrent_namespaces': response['Item'].get('max_concurrent_namespaces', 5),
                        'authorized_namespaces': response['Item'].get('authorized_namespaces', []),
                        'created_at': response['Item'].get('created_at'),
                        'updated_at': response['Item'].get('updated_at')
                    }
            except Exception as e:
                logger.warning(f"Could not fetch details for cost center {cost_center}: {e}")
        
        return jsonify({
            'cost_center': cost_center,
            'is_authorized': is_authorized,
            'details': details
        })
        
    except Exception as e:
        logger.error(f"Error validating cost center {cost_center}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cost-centers/<cost_center>/permissions', methods=['POST'])
def set_cost_center_permissions(cost_center):
    """Set permissions for a cost center"""
    try:
        data = request.get_json()
        is_authorized = data.get('is_authorized', False)
        max_concurrent = data.get('max_concurrent_namespaces', 5)
        authorized_namespaces = data.get('authorized_namespaces', [])
        
        scheduler.dynamodb_manager.set_cost_center_permissions(
            cost_center, is_authorized, max_concurrent, authorized_namespaces
        )
        
        return jsonify({'message': f'Permissions updated for cost center {cost_center}'})
        
    except Exception as e:
        logger.error(f"Error setting cost center permissions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/activities', methods=['GET'])
def get_activities():
    """Get namespace activities"""
    try:
        cost_center = request.args.get('cost_center')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        
        if cost_center:
            activities = scheduler.dynamodb_manager.get_activities_by_cost_center(
                cost_center, start_date, end_date
            )
        else:
            # Return recent activities (this would need a different query)
            activities = []
        
        return jsonify(activities)
        
    except Exception as e:
        logger.error(f"Error getting activities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audit/user/<requested_by>', methods=['GET'])
def get_activities_by_user(requested_by):
    """Get activities by user (requested_by) for audit purposes"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100, type=int)
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 1
        
        # Parse dates
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            return jsonify({'error': 'start_date cannot be after end_date'}), 400
        
        activities = scheduler.dynamodb_manager.get_activities_by_user(
            requested_by, start_date, end_date, limit
        )
        
        # Add summary statistics
        summary = {
            'total_activities': len(activities),
            'user': requested_by,
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'limit_applied': limit
        }
        
        # Calculate operation type counts
        operation_counts = {}
        for activity in activities:
            op_type = activity.get('operation_type', 'unknown')
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        
        summary['operation_counts'] = operation_counts
        
        return jsonify({
            'summary': summary,
            'activities': activities
        })
        
    except Exception as e:
        logger.error(f"Error getting activities by user {requested_by}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audit/cluster/<cluster_name>', methods=['GET'])
def get_activities_by_cluster(cluster_name):
    """Get activities by cluster for audit purposes"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100, type=int)
        
        # Validate limit
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 1
        
        # Parse dates
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            return jsonify({'error': 'start_date cannot be after end_date'}), 400
        
        activities = scheduler.dynamodb_manager.get_activities_by_cluster(
            cluster_name, start_date, end_date, limit
        )
        
        # Add summary statistics
        summary = {
            'total_activities': len(activities),
            'cluster': cluster_name,
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'limit_applied': limit
        }
        
        # Calculate operation type counts
        operation_counts = {}
        user_counts = {}
        cost_center_counts = {}
        
        for activity in activities:
            # Count by operation type
            op_type = activity.get('operation_type', 'unknown')
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
            
            # Count by user
            user = activity.get('requested_by', 'unknown')
            user_counts[user] = user_counts.get(user, 0) + 1
            
            # Count by cost center
            cost_center = activity.get('cost_center', 'unknown')
            cost_center_counts[cost_center] = cost_center_counts.get(cost_center, 0) + 1
        
        summary['operation_counts'] = operation_counts
        summary['user_counts'] = user_counts
        summary['cost_center_counts'] = cost_center_counts
        
        return jsonify({
            'summary': summary,
            'activities': activities
        })
        
    except Exception as e:
        logger.error(f"Error getting activities by cluster {cluster_name}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audit/summary', methods=['GET'])
def get_audit_summary():
    """Get audit summary with overall statistics"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            return jsonify({'error': 'start_date cannot be after end_date'}), 400
        
        # Get recent activities for summary (limit to avoid large scans)
        summary = {
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'message': 'Use specific endpoints (/api/audit/user/<user> or /api/audit/cluster/<cluster>) for detailed audit queries'
        }
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/business-hours', methods=['GET'])
def get_business_hours():
    """Get business hours configuration and current status"""
    try:
        info = scheduler.get_business_hours_info()
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Error getting business hours info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = scheduler.dynamodb_manager.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/invalidate', methods=['POST'])
def invalidate_cache():
    """Invalidate cache for a specific cost center or all cache"""
    try:
        data = request.get_json() or {}
        cost_center = data.get('cost_center')
        
        scheduler.dynamodb_manager.invalidate_cache(cost_center)
        
        if cost_center:
            return jsonify({'message': f'Cache invalidated for cost center {cost_center}'})
        else:
            return jsonify({'message': 'All cache invalidated'})
            
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/cleanup-all', methods=['POST'])
def cleanup_all_tasks():
    """Clean up all tasks (for testing/reset purposes)"""
    try:
        task_count = len(scheduler.tasks)
        scheduler.tasks.clear()
        scheduler.save_tasks()
        
        logger.info(f"Cleaned up all {task_count} tasks")
        
        return jsonify({
            'message': f'All {task_count} tasks have been cleaned up',
            'cleaned_count': task_count
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up all tasks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/batch', methods=['POST'])
def create_batch_tasks():
    """Create multiple tasks in batch"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract tasks from payload
        tasks = data.get('tasks', [])
        batch_create = data.get('batch_create', False)
        source = data.get('source', 'api')
        created_by = data.get('created_by', 'unknown')
        
        if not tasks:
            return jsonify({'error': 'No tasks provided'}), 400
        
        if not isinstance(tasks, list):
            return jsonify({'error': 'Tasks must be a list'}), 400
        
        created_tasks = []
        failed_tasks = []
        
        logger.info(f"Creating batch of {len(tasks)} tasks from source: {source}")
        
        for i, task_data in enumerate(tasks):
            try:
                # Validate required fields
                required_fields = ['title', 'operation_type', 'namespace', 'schedule', 'cost_center']
                missing_fields = [field for field in required_fields if not task_data.get(field)]
                
                if missing_fields:
                    failed_tasks.append({
                        'index': i,
                        'task': task_data.get('title', f'Task {i}'),
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    })
                    continue
                
                # Create task using existing scheduler logic
                task_id = task_data.get('id') or str(uuid.uuid4())
                
                # Prepare task for scheduler
                task = {
                    'id': task_id,
                    'title': task_data['title'],
                    'description': task_data.get('description', ''),
                    'operation_type': task_data['operation_type'],
                    'namespace': task_data['namespace'],
                    'schedule': task_data['schedule'],
                    'cost_center': task_data['cost_center'],
                    'status': 'pending',
                    'created_at': datetime.now().isoformat(),
                    'user_id': task_data.get('user_id', created_by),
                    'requested_by': task_data.get('requested_by', created_by),
                    'cluster_name': task_data.get('cluster_name', scheduler.cluster_name),
                    'auto_created': task_data.get('auto_created', batch_create),
                    'system_task': task_data.get('system_task', False)
                }
                
                # Add command if it's a command type task
                if task_data['operation_type'] == 'command':
                    task['command'] = task_data.get('command', '')
                
                # Add task to scheduler
                scheduler.add_task(task)
                
                created_tasks.append(task)
                logger.info(f"Created batch task {i+1}/{len(tasks)}: {task['title']}")
                
            except Exception as task_error:
                logger.error(f"Error creating task {i}: {task_error}")
                failed_tasks.append({
                    'index': i,
                    'task': task_data.get('title', f'Task {i}'),
                    'error': str(task_error)
                })
        
        # Save tasks if any were created successfully
        if created_tasks:
            scheduler.save_tasks()
        
        response = {
            'message': f'Batch task creation completed',
            'total_requested': len(tasks),
            'created_count': len(created_tasks),
            'failed_count': len(failed_tasks),
            'created_tasks': created_tasks,
            'source': source,
            'created_by': created_by
        }
        
        if failed_tasks:
            response['failed_tasks'] = failed_tasks
        
        status_code = 200 if created_tasks else 400
        
        logger.info(f"Batch creation result: {len(created_tasks)} created, {len(failed_tasks)} failed")
        
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Error in batch task creation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/default', methods=['POST'])
def create_default_system_tasks():
    """Create default system tasks for critical namespaces"""
    try:
        # Import the default tasks creator
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from create_default_tasks import create_default_tasks
        
        # Generate default tasks
        default_tasks = create_default_tasks()
        
        # Create batch payload
        batch_data = {
            'tasks': default_tasks,
            'batch_create': True,
            'source': 'system-default-generator',
            'created_by': 'system-auto'
        }
        
        # Use the batch creation endpoint
        return create_batch_tasks_internal(batch_data)
        
    except Exception as e:
        logger.error(f"Error creating default system tasks: {e}")
        return jsonify({'error': str(e)}), 500

def create_batch_tasks_internal(data):
    """Internal function for batch task creation (used by other endpoints)"""
    tasks = data.get('tasks', [])
    created_tasks = []
    failed_tasks = []
    
    for i, task_data in enumerate(tasks):
        try:
            task_id = task_data.get('id') or str(uuid.uuid4())
            
            # Prepare complete task data
            complete_task_data = {
                'id': task_id,
                'title': task_data['title'],
                'schedule': task_data['schedule'],
                'operation_type': task_data['operation_type'],
                'namespace': task_data['namespace'],
                'cost_center': task_data['cost_center'],
                'command': task_data.get('command'),
                'description': task_data.get('description'),
                'user_id': task_data.get('user_id', 'system'),
                'requested_by': task_data.get('requested_by', 'system-auto')
            }
            
            scheduler.add_task(complete_task_data)
            
            created_tasks.append(task_data)
            
        except Exception as task_error:
            failed_tasks.append({
                'index': i,
                'task': task_data.get('title', f'Task {i}'),
                'error': str(task_error)
            })
    
    if created_tasks:
        scheduler.save_tasks()
    
    return jsonify({
        'message': f'Created {len(created_tasks)} default system tasks',
        'created_count': len(created_tasks),
        'failed_count': len(failed_tasks),
        'created_tasks': created_tasks,
        'failed_tasks': failed_tasks if failed_tasks else None
    })

@app.route('/api/weekly-schedule/create-task', methods=['POST'])
def create_weekly_schedule_task():
    """
    Create a task from the weekly schedule view
    Simplified task creation for click-to-schedule functionality
    """
    try:
        data = request.get_json()
        
        # Required fields
        required_fields = ['namespace', 'day_of_week', 'hour', 'operation_type', 'cost_center']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate operation type
        if data['operation_type'] not in ['activate', 'deactivate']:
            return jsonify({
                'error': 'operation_type must be either "activate" or "deactivate"'
            }), 400
        
        # Validate day of week (0=Monday, 6=Sunday)
        day_of_week = data['day_of_week']
        if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
            return jsonify({
                'error': 'day_of_week must be an integer between 0 (Monday) and 6 (Sunday)'
            }), 400
        
        # Validate hour
        hour = data['hour']
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            return jsonify({
                'error': 'hour must be an integer between 0 and 23'
            }), 400
        
        # Check if namespace is protected
        namespace = data['namespace']
        if scheduler.is_protected_namespace(namespace):
            return jsonify({
                'error': f'Cannot schedule protected namespace: {namespace}'
            }), 400
        
        # Create cron expression for the specific day and hour
        # Format: minute hour day month day_of_week
        minute = data.get('minute', 0)  # Default to start of hour
        
        # Convert day_of_week (0=Monday) to cron format (1=Monday, 0=Sunday)
        cron_day_of_week = day_of_week + 1 if day_of_week < 6 else 0
        cron_expression = f"{minute} {hour} * * {cron_day_of_week}"
        
        # Generate task title
        day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        operation_text = 'Activar' if data['operation_type'] == 'activate' else 'Desactivar'
        title = f"{operation_text} {namespace} - {day_names[day_of_week]} {hour:02d}:{minute:02d}"
        
        # Create task data
        task_data = {
            'title': title,
            'description': data.get('description', f'Tarea creada desde vista semanal'),
            'operation_type': data['operation_type'],
            'namespace': namespace,
            'schedule': cron_expression,
            'cost_center': data['cost_center'],
            'user_id': data.get('user_id', 'weekly-view-user'),
            'requested_by': data.get('requested_by', 'weekly-view-user'),
            'created_from': 'weekly_view'
        }
        
        # Create the task
        task = scheduler.add_task(task_data)
        
        # Invalidate weekly cache since we added a new task
        scheduler.invalidate_weekly_cache()
        
        logger.info(f"Created weekly schedule task: {title}")
        
        return jsonify({
            'success': True,
            'message': 'Task created successfully',
            'task': task,
            'cron_expression': cron_expression
        }), 201
        
    except ValueError as e:
        logger.error(f"Validation error creating weekly schedule task: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating weekly schedule task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weekly-schedule/<week_start_date>', methods=['GET'])
def get_weekly_schedule(week_start_date):
    """
    Get weekly schedule for a specific week
    
    Args:
        week_start_date: Date string in YYYY-MM-DD format representing Monday of the week
    
    Returns:
        JSON response with weekly schedule data organized in 7x24 time slots
    """
    try:
        # Parse the week start date
        try:
            week_start = datetime.strptime(week_start_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD format.'
            }), 400
        
        # Ensure the date is a Monday (weekday 0)
        if week_start.weekday() != 0:
            # Adjust to the Monday of that week
            days_since_monday = week_start.weekday()
            week_start = week_start - timedelta(days=days_since_monday)
            logger.info(f"Adjusted week start date to Monday: {week_start.strftime('%Y-%m-%d')}")
        
        # Get all scheduled tasks for the week (with caching)
        response = scheduler.get_weekly_schedule_cached(week_start)
        
        logger.info(f"Generated weekly schedule for {week_start_date}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting weekly schedule for {week_start_date}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': None
        }), 500

@app.route('/api/weekly-schedule/cache/stats', methods=['GET'])
def get_weekly_cache_stats():
    """Get weekly schedule cache statistics"""
    try:
        stats = scheduler.get_weekly_cache_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting weekly cache stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/weekly-schedule/cache/invalidate', methods=['POST'])
def invalidate_weekly_cache():
    """Invalidate weekly schedule cache"""
    try:
        data = request.get_json() or {}
        week_start_date_str = data.get('week_start_date')
        
        if week_start_date_str:
            try:
                week_start_date = datetime.strptime(week_start_date_str, '%Y-%m-%d')
                scheduler.invalidate_weekly_cache(week_start_date)
                return jsonify({'message': f'Weekly cache invalidated for {week_start_date_str}'})
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD format.'}), 400
        else:
            scheduler.invalidate_weekly_cache()
            return jsonify({'message': 'All weekly cache invalidated'})
            
    except Exception as e:
        logger.error(f"Error invalidating weekly cache: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the Flask app
    # Updated: 2026-02-18 - Force rebuild to include batch task creation endpoints
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
