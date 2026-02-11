#!/bin/bash
# Script para construir y pushear imágenes a ECR

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="226633502530"
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Autenticando con ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

echo ""
echo -e "${BLUE}🏗️  Construyendo imagen del Frontend...${NC}"
docker build -t task-scheduler-frontend:latest ./frontend
docker tag task-scheduler-frontend:latest $ECR_REGISTRY/task-scheduler-frontend:latest
docker tag task-scheduler-frontend:latest $ECR_REGISTRY/task-scheduler-frontend:$(git rev-parse --short HEAD)

echo ""
echo -e "${BLUE}📤 Pusheando imagen del Frontend a ECR...${NC}"
docker push $ECR_REGISTRY/task-scheduler-frontend:latest
docker push $ECR_REGISTRY/task-scheduler-frontend:$(git rev-parse --short HEAD)

echo ""
echo -e "${BLUE}🏗️  Construyendo imagen del Backend...${NC}"
docker build -t task-scheduler-backend:latest ./kubectl-runner
docker tag task-scheduler-backend:latest $ECR_REGISTRY/task-scheduler-backend:latest
docker tag task-scheduler-backend:latest $ECR_REGISTRY/task-scheduler-backend:$(git rev-parse --short HEAD)

echo ""
echo -e "${BLUE}📤 Pusheando imagen del Backend a ECR...${NC}"
docker push $ECR_REGISTRY/task-scheduler-backend:latest
docker push $ECR_REGISTRY/task-scheduler-backend:$(git rev-parse --short HEAD)

echo ""
echo -e "${GREEN}✅ Imágenes construidas y pusheadas exitosamente!${NC}"
echo ""
echo -e "${YELLOW}📋 Imágenes disponibles:${NC}"
echo "   Frontend:"
echo "   - $ECR_REGISTRY/task-scheduler-frontend:latest"
echo "   - $ECR_REGISTRY/task-scheduler-frontend:$(git rev-parse --short HEAD)"
echo ""
echo "   Backend:"
echo "   - $ECR_REGISTRY/task-scheduler-backend:latest"
echo "   - $ECR_REGISTRY/task-scheduler-backend:$(git rev-parse --short HEAD)"
echo ""
echo -e "${YELLOW}🚀 Siguiente paso: Desplegar con ArgoCD${NC}"
echo "   kubectl apply -f argocd/namespace-scheduler-app.yaml"
