#!/usr/bin/env python3
"""
Production runner for the kubectl-runner backend
This script sets up the environment for production EKS cluster
"""

import os
import sys

# Set up local directories
os.makedirs('./logs', exist_ok=True)
os.makedirs('./config', exist_ok=True)

# Set environment variables for production
os.environ['LOG_FILE'] = './logs/app.log'
os.environ['FLASK_ENV'] = 'production'
os.environ['EKS_CLUSTER_NAME'] = 'eks-cloud'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['DYNAMODB_TABLE_NAME'] = 'task-scheduler-logs-production'
os.environ['PERMISSIONS_TABLE_NAME'] = 'cost-center-permissions-production'
os.environ['KUBECONFIG'] = os.path.expanduser('~/.kube/config')

# Ensure AWS credentials are available (they should be inherited from parent process)
# If not present, the subprocess will fail to authenticate with EKS
if 'AWS_ACCESS_KEY_ID' not in os.environ:
    print("WARNING: AWS_ACCESS_KEY_ID not found in environment")
if 'AWS_SECRET_ACCESS_KEY' not in os.environ:
    print("WARNING: AWS_SECRET_ACCESS_KEY not found in environment")

# Patch the hardcoded paths in app.py before importing
import builtins
original_makedirs = os.makedirs
original_exists = os.path.exists

def patched_makedirs(path, *args, **kwargs):
    """Patch makedirs to replace /app with local paths"""
    if path.startswith('/app'):
        path = '.' + path[4:]  # Replace /app with .
    return original_makedirs(path, *args, **kwargs)

def patched_exists(path):
    """Patch exists to handle kubeconfig path"""
    if path == '/root/.kube/config':
        # Check user's kubeconfig instead
        return original_exists(os.path.expanduser('~/.kube/config'))
    return original_exists(path)

os.makedirs = patched_makedirs
os.path.exists = patched_exists

# Now import and run the app
print("=" * 60)
print("Starting Flask backend connected to EKS cluster")
print("=" * 60)
print(f"Cluster: {os.environ['EKS_CLUSTER_NAME']}")
print(f"Region: {os.environ['AWS_REGION']}")
print(f"DynamoDB Table: {os.environ['DYNAMODB_TABLE_NAME']}")
print(f"Permissions Table: {os.environ['PERMISSIONS_TABLE_NAME']}")
print(f"Logs: {os.environ['LOG_FILE']}")
print(f"Config: ./config/")
print("=" * 60)

# Import the app module
import app as flask_app

# Run the Flask app
if __name__ == '__main__':
    flask_app.app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
