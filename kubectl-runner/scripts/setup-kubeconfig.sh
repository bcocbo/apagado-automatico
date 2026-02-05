#!/bin/bash
# Setup kubeconfig for EKS cluster

set -e

CLUSTER_NAME=${EKS_CLUSTER_NAME:-"default-cluster"}
AWS_REGION=${AWS_REGION:-"us-east-1"}

echo "Setting up kubeconfig for EKS cluster: $CLUSTER_NAME in region: $AWS_REGION"

# Create .kube directory if it doesn't exist
mkdir -p /root/.kube

# Update kubeconfig
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Verify connection
kubectl cluster-info

echo "Kubeconfig setup completed successfully"