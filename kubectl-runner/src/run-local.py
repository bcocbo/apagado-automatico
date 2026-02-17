#!/usr/bin/env python3
"""
Local development runner for the kubectl-runner backend
This script sets up the environment for local development
"""

import os
import sys

# Set up local directories
os.makedirs('./logs', exist_ok=True)
os.makedirs('./config', exist_ok=True)

# Set environment variables for local development
os.environ['LOG_FILE'] = './logs/app.log'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['EKS_CLUSTER_NAME'] = 'local-cluster'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['DYNAMODB_TABLE_NAME'] = 'task-scheduler-logs-local'
os.environ['PERMISSIONS_TABLE_NAME'] = 'cost-center-permissions-local'

# Patch the hardcoded paths in app.py before importing
import builtins
original_makedirs = os.makedirs

def patched_makedirs(path, *args, **kwargs):
    """Patch makedirs to replace /app with local paths"""
    if path.startswith('/app'):
        path = '.' + path[4:]  # Replace /app with .
    return original_makedirs(path, *args, **kwargs)

os.makedirs = patched_makedirs

# Now import and run the app
print("Starting Flask backend in local development mode...")
print(f"Logs: {os.environ['LOG_FILE']}")
print(f"Config: ./config/")
print(f"Cluster: {os.environ['EKS_CLUSTER_NAME']}")
print("-" * 50)

# Import the app module
import app as flask_app
