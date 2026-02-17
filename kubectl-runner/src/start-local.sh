#!/bin/bash

# Create local directories
mkdir -p ./logs
mkdir -p ./config

# Set environment variables for local development
export LOG_FILE="./logs/app.log"
export FLASK_ENV="development"
export FLASK_DEBUG="1"
export EKS_CLUSTER_NAME="local-cluster"
export AWS_REGION="us-east-1"
export DYNAMODB_TABLE_NAME="task-scheduler-logs-local"
export PERMISSIONS_TABLE_NAME="cost-center-permissions-local"

# Run the Flask app
python3 app.py
