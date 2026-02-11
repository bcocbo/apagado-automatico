#!/bin/bash
# Script para crear repositorios ECR para Task Scheduler

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="226633502530"

echo "🚀 Creando repositorios ECR..."

# Crear repositorio para frontend
echo "📦 Creando repositorio task-scheduler-frontend..."
aws ecr create-repository \
    --repository-name task-scheduler-frontend \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || echo "✓ Repositorio task-scheduler-frontend ya existe"

# Crear repositorio para backend
echo "📦 Creando repositorio task-scheduler-backend..."
aws ecr create-repository \
    --repository-name task-scheduler-backend \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || echo "✓ Repositorio task-scheduler-backend ya existe"

echo ""
echo "✅ Repositorios ECR listos:"
echo "   - $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/task-scheduler-frontend"
echo "   - $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/task-scheduler-backend"
