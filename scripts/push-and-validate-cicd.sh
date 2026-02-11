#!/bin/bash
# Script para hacer push y validar CI/CD

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Preparando push para validar CI/CD...${NC}"
echo ""

# 1. Verificar estado del repositorio
echo -e "${BLUE}📋 Verificando estado del repositorio...${NC}"
if git status --porcelain | grep -q .; then
    echo -e "${YELLOW}⚠️  Hay cambios pendientes${NC}"
    git status --short
else
    echo -e "${GREEN}✅ Repositorio limpio${NC}"
fi

# 2. Verificar que estamos en la rama correcta
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${BLUE}🌿 Rama actual: $CURRENT_BRANCH${NC}"

if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "develop" ]; then
    echo -e "${YELLOW}⚠️  No estás en main o develop. El workflow solo se ejecuta en estas ramas.${NC}"
    echo -e "${YELLOW}   Rama actual: $CURRENT_BRANCH${NC}"
fi

# 3. Agregar todos los cambios
echo -e "${BLUE}📦 Agregando cambios...${NC}"
git add .

# 4. Hacer commit
echo -e "${BLUE}💾 Haciendo commit...${NC}"
COMMIT_MSG="feat: Configure GitHub Actions IAM and ECR policies

- Add IAM role and policies for GitHub Actions
- Update workflow to use secrets for AWS credentials
- Add validation and test scripts
- Configure ECR repositories for frontend and backend
- Update manifests to use new backend repository

[skip ci] for initial setup"

git commit -m "$COMMIT_MSG" || echo "No hay cambios para commitear"

# 5. Push
echo -e "${BLUE}🚀 Haciendo push...${NC}"
git push origin $CURRENT_BRANCH

echo ""
echo -e "${GREEN}✅ Push completado!${NC}"
echo ""
echo -e "${YELLOW}📋 Para monitorear el workflow:${NC}"
echo "   1. Ve a: https://github.com/bcocbo/apagado-automatico/actions"
echo "   2. Busca el workflow 'Build and Push Task Scheduler Containers'"
echo "   3. Verifica que los jobs se ejecuten correctamente"
echo ""
echo -e "${YELLOW}🔍 Verificaciones esperadas:${NC}"
echo "   ✅ build-frontend: Debe construir y pushear imagen frontend"
echo "   ✅ build-backend: Debe construir y pushear imagen backend"
echo "   ✅ update-manifests: Debe actualizar tags en manifiestos (solo en main)"
echo ""
echo -e "${YELLOW}📦 Imágenes esperadas en ECR:${NC}"
echo "   - 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-frontend:latest"
echo "   - 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-backend:latest"
echo "   - Tags con SHA del commit"
echo ""
echo -e "${BLUE}💡 Si hay errores, revisar:${NC}"
echo "   1. Secrets configurados en GitHub:"
echo "      - AWS_REGION: us-east-1"
echo "      - AWS_ROLE_TO_ASSUME: arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role"
echo "   2. Permisos del rol IAM"
echo "   3. Repositorios ECR existentes"