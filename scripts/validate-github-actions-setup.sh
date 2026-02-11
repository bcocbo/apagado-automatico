#!/bin/bash
# Script para validar la configuración de GitHub Actions

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="226633502530"
ROLE_NAME="GitHubActions-TaskScheduler-Role"
POLICY_NAME="GitHubActions-TaskScheduler-ECR-Policy"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validando configuración de GitHub Actions...${NC}"
echo ""

# Función para mostrar resultado
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# 1. Verificar que el rol existe
echo -e "${BLUE}👤 Verificando rol de IAM...${NC}"
aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1
check_result $? "Rol $ROLE_NAME existe"

# 2. Verificar que la política existe
echo -e "${BLUE}📋 Verificando política ECR...${NC}"
aws iam get-policy --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" >/dev/null 2>&1
check_result $? "Política $POLICY_NAME existe"

# 3. Verificar que la política está adjunta al rol
echo -e "${BLUE}🔗 Verificando política adjunta al rol...${NC}"
aws iam list-attached-role-policies --role-name $ROLE_NAME | grep -q $POLICY_NAME
check_result $? "Política adjunta al rol"

# 4. Verificar OIDC provider
echo -e "${BLUE}🤝 Verificando OIDC provider...${NC}"
aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com" \
    >/dev/null 2>&1
check_result $? "OIDC provider para GitHub existe"

# 5. Verificar repositorios ECR
echo -e "${BLUE}📦 Verificando repositorios ECR...${NC}"
aws ecr describe-repositories --repository-names task-scheduler-frontend >/dev/null 2>&1
check_result $? "Repositorio task-scheduler-frontend existe"

aws ecr describe-repositories --repository-names task-scheduler-backend >/dev/null 2>&1
check_result $? "Repositorio task-scheduler-backend existe"

# 6. Mostrar información del rol
echo ""
echo -e "${BLUE}📋 Información del rol:${NC}"
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "   ARN: $ROLE_ARN"

# 7. Mostrar trust policy
echo ""
echo -e "${BLUE}🤝 Trust Policy:${NC}"
aws iam get-role --role-name $ROLE_NAME --query 'Role.AssumeRolePolicyDocument' --output json | jq .

# 8. Mostrar políticas adjuntas
echo ""
echo -e "${BLUE}📋 Políticas adjuntas:${NC}"
aws iam list-attached-role-policies --role-name $ROLE_NAME --query 'AttachedPolicies[].PolicyName' --output table

echo ""
echo -e "${GREEN}✅ Validación completada!${NC}"
echo ""
echo -e "${YELLOW}📋 Para GitHub Secrets:${NC}"
echo "   AWS_REGION: $AWS_REGION"
echo "   AWS_ROLE_TO_ASSUME: $ROLE_ARN"
echo ""
echo -e "${YELLOW}🔗 Configurar en:${NC}"
echo "   https://github.com/bcocbo/apagado-automatico/settings/secrets/actions"