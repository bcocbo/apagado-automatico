#!/bin/bash
# Script para probar el flujo completo de GitHub Actions (simulación)

set -e

AWS_REGION="us-east-1"
ECR_REGISTRY="226633502530.dkr.ecr.us-east-1.amazonaws.com"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Probando flujo de GitHub Actions...${NC}"
echo ""

# 1. Simular login a ECR (lo que haría GitHub Actions)
echo -e "${BLUE}🔐 Probando login a ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
echo -e "${GREEN}✅ Login a ECR exitoso${NC}"

# 2. Verificar que podemos listar repositorios
echo -e "${BLUE}📦 Verificando acceso a repositorios...${NC}"
aws ecr describe-repositories --repository-names task-scheduler-frontend task-scheduler-backend --region $AWS_REGION > /dev/null
echo -e "${GREEN}✅ Acceso a repositorios confirmado${NC}"

# 3. Verificar que podemos obtener información de imágenes
echo -e "${BLUE}🖼️  Verificando acceso a imágenes...${NC}"
aws ecr list-images --repository-name task-scheduler-frontend --region $AWS_REGION > /dev/null
aws ecr list-images --repository-name task-scheduler-backend --region $AWS_REGION > /dev/null
echo -e "${GREEN}✅ Acceso a imágenes confirmado${NC}"

echo ""
echo -e "${GREEN}✅ Todas las pruebas pasaron!${NC}"
echo ""
echo -e "${YELLOW}📋 Configuración lista para GitHub Actions:${NC}"
echo "   - Rol IAM: GitHubActions-TaskScheduler-Role"
echo "   - Política ECR: GitHubActions-TaskScheduler-ECR-Policy"
echo "   - OIDC Provider: Configurado"
echo "   - Repositorios ECR: Accesibles"
echo ""
echo -e "${YELLOW}🚀 Próximos pasos:${NC}"
echo "   1. Configurar secrets en GitHub:"
echo "      - AWS_REGION: us-east-1"
echo "      - AWS_ROLE_TO_ASSUME: arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role"
echo "   2. Crear workflow en .github/workflows/"
echo "   3. Hacer push para probar el pipeline"