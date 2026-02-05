#!/bin/bash
# Health check script for kubectl runner

set -e

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found"
    exit 1
fi

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "ERROR: aws cli not found"
    exit 1
fi

# Check if kubeconfig exists and is valid
if [ -f /root/.kube/config ]; then
    if kubectl cluster-info &> /dev/null; then
        echo "OK: Kubernetes cluster connection is healthy"
    else
        echo "WARNING: Cannot connect to Kubernetes cluster"
        exit 1
    fi
else
    echo "WARNING: No kubeconfig found"
fi

# Check if the API server is running
if curl -f http://localhost:8080/health &> /dev/null; then
    echo "OK: API server is healthy"
else
    echo "ERROR: API server is not responding"
    exit 1
fi

echo "All health checks passed"