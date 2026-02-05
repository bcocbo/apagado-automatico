#!/usr/bin/env python3
"""
kubectl Runner API Server
Provides REST API for executing kubectl commands and managing scheduled tasks
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

class TaskScheduler:
    def __init__(self):
        self.tasks = {}
        self.running_tasks = {}
        self.task_history = []
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

    def add_task(self, task_data):
        """Add a new task"""
        task_id = task_data.get('id', str(int(time.time())))
        self.tasks[task_id] = {
            'id': task_id,
            'title': task_data.get('title', ''),
            'command': task_data.get('command', ''),
            'schedule': task_data.get('schedule', ''),
            'namespace': task_data.get('namespace', 'default'),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'next_run': self.calculate_next_run(task_data.get('schedule', '')),
            'run_count': 0,
            'success_count': 0,
            'error_count': 0
        }
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
            result = self.execute_kubectl_command(
                task['command'],
                task['namespace']
            )
            
            if result['success']:
                task['status'] = 'completed'
                task['success_count'] += 1
            else:
                task['status'] = 'failed'
                task['error_count'] += 1

            # Add to history
            history_entry = {
                'task_id': task_id,
                'title': task['title'],
                'command': task['command'],
                'timestamp': datetime.now().isoformat(),
                'success': result['success'],
                'output': result['stdout'],
                'error': result['stderr']
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

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('/app/logs', exist_ok=True)
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080, debug=False)