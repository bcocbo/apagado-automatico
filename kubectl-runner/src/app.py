#!/usr/bin/env python3
"""
kubectl Runner API Server
Provides REST API for executing kubectl commands and managing scheduled tasks
Version: 2.0.0 - Added DynamoDB integration for task scheduling
"""

import os
import json
import logging
import subprocess
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from croniter import croniter
import yaml
import boto3
from botocore.exceptions import ClientError
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class DynamoDBManager:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'task-scheduler-logs')
        self.permissions_table_name = os.getenv('PERMISSIONS_TABLE_NAME', 'cost-center-permissions')
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
                            {'AttributeName': 'cost_center', 'AttributeType': 'S'}
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

    def log_namespace_activity(self, namespace_name, operation_type, cost_center, user_id=None, **kwargs):
        """Log namespace activity to DynamoDB"""
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
            
            if user_id:
                item['user_id'] = user_id
            
            # Add any additional fields
            item.update(kwargs)
            
            self.table.put_item(Item=item)
            logger.info(f"Logged activity for namespace {namespace_name}: {operation_type}")
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

    def validate_cost_center_permissions(self, cost_center):
        """Validate if cost center has permissions"""
        try:
            response = self.permissions_table.get_item(
                Key={'cost_center': cost_center}
            )
            
            if 'Item' in response:
                return response['Item'].get('is_authorized', False)
            else:
                # If not found, deny by default
                return False
                
        except Exception as e:
            logger.error(f"Error validating cost center permissions: {e}")
            return False

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
            logger.info(f"Set permissions for cost center {cost_center}: {is_authorized}")
            
        except Exception as e:
            logger.error(f"Error setting cost center permissions: {e}")
            raise

class TaskScheduler:
    def __init__(self):
        self.tasks = {}
        self.running_tasks = {}
        self.task_history = []
        self.active_namespaces_count = 0
        self.dynamodb_manager = DynamoDBManager()
        self.load_tasks()
        self.start_scheduler()

    def load_tasks(self):
        """Load tasks from file"""
        try:
            if os.path.exists('/app/config/tasks.json'):
                with open('/app/config/tasks.json', 'r') as f:
                    self.tasks = json.load(f)
                logger.info(f"Loaded {len(self.tasks)} tasks")
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")

    def save_tasks(self):
        """Save tasks to file"""
        try:
            os.makedirs('/app/config', exist_ok=True)
            with open('/app/config/tasks.json', 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")

    def is_non_business_hours(self, timestamp=None):
        """Check if current time is non-business hours"""
        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        
        # Weekend (Saturday=5, Sunday=6)
        if timestamp.weekday() >= 5:
            return True
        
        # Business days: 8pm-7am
        hour = timestamp.hour
        return hour >= 20 or hour < 7

    def validate_namespace_activation(self, cost_center, namespace):
        """Validate if namespace can be activated"""
        # Check cost center permissions
        if not self.dynamodb_manager.validate_cost_center_permissions(cost_center):
            return False, "Cost center not authorized"
        
        # Check if it's non-business hours
        if not self.is_non_business_hours():
            return True, "Business hours - no limit"
        
        # Check namespace limit during non-business hours
        if self.active_namespaces_count >= 5:
            return False, "Maximum 5 namespaces allowed during non-business hours"
        
        return True, "Validation passed"

    def activate_namespace(self, namespace, cost_center, user_id=None):
        """Activate a namespace"""
        try:
            # Validate activation
            is_valid, message = self.validate_namespace_activation(cost_center, namespace)
            if not is_valid:
                return {'success': False, 'error': message}
            
            # Scale up namespace resources
            result = self.scale_namespace_resources(namespace, target_replicas=None)  # Restore original
            
            if result['success']:
                # Log activity to DynamoDB
                self.dynamodb_manager.log_namespace_activity(
                    namespace_name=namespace,
                    operation_type='manual_activation',
                    cost_center=cost_center,
                    user_id=user_id
                )
                
                # Update active count if non-business hours
                if self.is_non_business_hours():
                    self.active_namespaces_count += 1
                
                return {'success': True, 'message': f'Namespace {namespace} activated successfully'}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to activate namespace')}
                
        except Exception as e:
            logger.error(f"Error activating namespace {namespace}: {e}")
            return {'success': False, 'error': str(e)}

    def deactivate_namespace(self, namespace, cost_center, user_id=None):
        """Deactivate a namespace"""
        try:
            # Scale down namespace resources
            result = self.scale_namespace_resources(namespace, target_replicas=0)
            
            if result['success']:
                # Log activity to DynamoDB
                self.dynamodb_manager.log_namespace_activity(
                    namespace_name=namespace,
                    operation_type='manual_deactivation',
                    cost_center=cost_center,
                    user_id=user_id
                )
                
                # Update active count if non-business hours
                if self.is_non_business_hours() and self.active_namespaces_count > 0:
                    self.active_namespaces_count -= 1
                
                return {'success': True, 'message': f'Namespace {namespace} deactivated successfully'}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to deactivate namespace')}
                
        except Exception as e:
            logger.error(f"Error deactivating namespace {namespace}: {e}")
            return {'success': False, 'error': str(e)}

    def scale_namespace_resources(self, namespace, target_replicas):
        """Scale all resources in a namespace"""
        try:
            resources = ['deployments', 'statefulsets', 'daemonsets']
            original_scales = {}
            results = []
            
            for resource_type in resources:
                # Get current resources
                result = self.execute_kubectl_command(f'get {resource_type} -n {namespace} -o json')
                
                if result['success']:
                    try:
                        resources_data = json.loads(result['stdout'])
                        for item in resources_data.get('items', []):
                            resource_name = item['metadata']['name']
                            current_replicas = item.get('spec', {}).get('replicas', 1)
                            
                            if target_replicas == 0:
                                # Save original scale for restoration
                                original_scales[f"{resource_type}/{resource_name}"] = current_replicas
                                # Scale to 0
                                scale_result = self.execute_kubectl_command(
                                    f'scale {resource_type} {resource_name} --replicas=0 -n {namespace}'
                                )
                                results.append(scale_result)
                            elif target_replicas is None:
                                # Restore original scale (would need to be stored somewhere)
                                # For now, scale to 1 as default
                                scale_result = self.execute_kubectl_command(
                                    f'scale {resource_type} {resource_name} --replicas=1 -n {namespace}'
                                )
                                results.append(scale_result)
                            else:
                                # Scale to specific number
                                scale_result = self.execute_kubectl_command(
                                    f'scale {resource_type} {resource_name} --replicas={target_replicas} -n {namespace}'
                                )
                                results.append(scale_result)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON for {resource_type} in namespace {namespace}")
            
            # Check if all operations were successful
            all_successful = all(r.get('success', False) for r in results)
            
            return {
                'success': all_successful,
                'original_scales': original_scales,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error scaling namespace resources: {e}")
            return {'success': False, 'error': str(e)}

    def add_task(self, task_data):
        """Add a new task"""
        task_id = task_data.get('id', str(uuid.uuid4()))
        
        # Enhanced task structure for namespace scheduling
        self.tasks[task_id] = {
            'id': task_id,
            'title': task_data.get('title', ''),
            'command': task_data.get('command', ''),
            'schedule': task_data.get('schedule', ''),
            'namespace': task_data.get('namespace', 'default'),
            'cost_center': task_data.get('cost_center', 'default'),
            'operation_type': task_data.get('operation_type', 'command'),  # 'command', 'activate', 'deactivate'
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
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
                task_id=task_id,
                task_title=self.tasks[task_id]['title']
            )
        except Exception as e:
            logger.error(f"Error logging task creation to DynamoDB: {e}")
        
        self.save_tasks()
        return self.tasks[task_id]

    def calculate_next_run(self, cron_expression):
        """Calculate next run time from cron expression"""
        try:
            if cron_expression:
                cron = croniter(cron_expression, datetime.now())
                return cron.get_next(datetime).isoformat()
        except Exception as e:
            logger.error(f"Error calculating next run: {e}")
        return None

    def execute_kubectl_command(self, command, namespace='default'):
        """Execute kubectl command"""
        try:
            # Ensure we have proper kubeconfig
            if not os.path.exists('/root/.kube/config'):
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

            logger.info(f"Executing command: {command}")
            
            # Execute command
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

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
        """Run a specific task"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task['status'] = 'running'
        task['last_run'] = datetime.now().isoformat()
        task['run_count'] += 1
        
        self.running_tasks[task_id] = threading.Thread(
            target=self._execute_task,
            args=(task_id,)
        )
        self.running_tasks[task_id].start()
        return True

    def _execute_task(self, task_id):
        """Execute task in background thread"""
        task = self.tasks[task_id]
        
        try:
            # Handle different operation types
            if task.get('operation_type') == 'activate':
                result = self.activate_namespace(
                    task['namespace'], 
                    task['cost_center'],
                    user_id='scheduler'
                )
            elif task.get('operation_type') == 'deactivate':
                result = self.deactivate_namespace(
                    task['namespace'], 
                    task['cost_center'],
                    user_id='scheduler'
                )
            else:
                # Regular kubectl command
                result = self.execute_kubectl_command(
                    task['command'],
                    task['namespace']
                )
            
            if result.get('success', False):
                task['status'] = 'completed'
                task['success_count'] += 1
            else:
                task['status'] = 'failed'
                task['error_count'] += 1

            # Add to history
            history_entry = {
                'task_id': task_id,
                'title': task['title'],
                'command': task.get('command', f"{task.get('operation_type', 'unknown')} {task['namespace']}"),
                'timestamp': datetime.now().isoformat(),
                'success': result.get('success', False),
                'output': result.get('stdout', result.get('message', '')),
                'error': result.get('stderr', result.get('error', ''))
            }
            self.task_history.append(history_entry)
            
            # Keep only last 100 history entries
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]

            # Calculate next run if it's a scheduled task
            if task['schedule']:
                task['next_run'] = self.calculate_next_run(task['schedule'])
                task['status'] = 'pending'

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            task['status'] = 'failed'
            task['error_count'] += 1

        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            self.save_tasks()

    def start_scheduler(self):
        """Start the task scheduler"""
        def scheduler_loop():
            while True:
                try:
                    now = datetime.now()
                    for task_id, task in self.tasks.items():
                        if (task['status'] == 'pending' and 
                            task['next_run'] and 
                            datetime.fromisoformat(task['next_run']) <= now and
                            task_id not in self.running_tasks):
                            
                            logger.info(f"Running scheduled task: {task['title']}")
                            self.run_task(task_id)
                    
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)

        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Task scheduler started")

# Initialize scheduler
scheduler = TaskScheduler()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tasks_count': len(scheduler.tasks),
        'running_tasks': len(scheduler.running_tasks)
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    return jsonify(list(scheduler.tasks.values()))

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        task_data = request.get_json()
        task = scheduler.add_task(task_data)
        return jsonify(task), 201
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
    """Get execution logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = scheduler.task_history[-limit:]
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
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

@app.route('/api/namespaces/<namespace>/activate', methods=['POST'])
def activate_namespace(namespace):
    """Activate a namespace"""
    try:
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        
        result = scheduler.activate_namespace(namespace, cost_center, user_id)
        
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
        data = request.get_json() or {}
        cost_center = data.get('cost_center', 'default')
        user_id = data.get('user_id', 'anonymous')
        
        result = scheduler.deactivate_namespace(namespace, cost_center, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error deactivating namespace {namespace}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/namespaces/status', methods=['GET'])
def get_namespaces_status():
    """Get status of all namespaces"""
    try:
        # Get all namespaces
        result = scheduler.execute_kubectl_command('get namespaces -o json')
        if not result['success']:
            return jsonify({'error': result['stderr']}), 500
        
        namespaces_data = json.loads(result['stdout'])
        namespace_status = []
        
        for item in namespaces_data['items']:
            namespace_name = item['metadata']['name']
            
            # Check if namespace has active resources
            pods_result = scheduler.execute_kubectl_command(f'get pods -n {namespace_name} --field-selector=status.phase=Running -o json')
            active_pods = 0
            
            if pods_result['success']:
                pods_data = json.loads(pods_result['stdout'])
                active_pods = len(pods_data.get('items', []))
            
            namespace_status.append({
                'name': namespace_name,
                'active_pods': active_pods,
                'is_active': active_pods > 0,
                'is_system': namespace_name in ['kube-system', 'kube-public', 'kube-node-lease', 'default']
            })
        
        return jsonify({
            'namespaces': namespace_status,
            'active_count': scheduler.active_namespaces_count,
            'is_non_business_hours': scheduler.is_non_business_hours()
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

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080, debug=False)