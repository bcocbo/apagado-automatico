#!/bin/bash
# Script para validar la configuración de IAM roles para EKS

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="226633502530"
EKS_CLUSTER_NAME="eks-cloud"
NAMESPACE="task-scheduler"
SERVICE_ACCOUNT="kubectl-runner"
ROLE_NAME="kubectl-runner-role"
POLICY_NAME="kubectl-runner-dynamodb-policy"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validando configuración de IAM para EKS...${NC}"
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
echo -e "${BLUE}📋 Verificando política DynamoDB...${NC}"
aws iam get-policy --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" >/dev/null 2>&1
check_result $? "Política $POLICY_NAME existe"

# 3. Verificar que la política está adjunta al rol
echo -e "${BLUE}🔗 Verificando política adjunta al rol...${NC}"
aws iam list-attached-role-policies --role-name $ROLE_NAME | grep -q $POLICY_NAME
check_result $? "Política adjunta al rol"

# 4. Verificar cluster EKS
echo -e "${BLUE}🏗️  Verificando cluster EKS...${NC}"
aws eks describe-cluster --name $EKS_CLUSTER_NAME >/dev/null 2>&1
check_result $? "Cluster EKS $EKS_CLUSTER_NAME existe"

# 5. Obtener OIDC issuer y verificar provider
echo -e "${BLUE}🤝 Verificando OIDC provider...${NC}"
OIDC_ISSUER=$(aws eks describe-cluster --name $EKS_CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text)
OIDC_ID=$(echo $OIDC_ISSUER | cut -d '/' -f 5)
OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}"

aws iam get-open-id-connect-provider --open-id-connect-provider-arn $OIDC_PROVIDER_ARN >/dev/null 2>&1
check_result $? "OIDC provider para EKS existe"

# 6. Verificar service account (si kubectl está configurado)
echo -e "${BLUE}🔧 Verificando service account...${NC}"
if command -v kubectl >/dev/null 2>&1; then
    # Intentar configurar kubectl si no está configurado
    if ! kubectl cluster-info >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Configurando kubectl...${NC}"
        aws eks update-kubeconfig --region $AWS_REGION --name $EKS_CLUSTER_NAME
    fi
    
    # Verificar que el service account existe
    if kubectl get serviceaccount $SERVICE_ACCOUNT -n $NAMESPACE >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Service account $SERVICE_ACCOUNT existe${NC}"
        
        # Verificar anotación del rol
        ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
        CURRENT_ANNOTATION=$(kubectl get serviceaccount $SERVICE_ACCOUNT -n $NAMESPACE -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}' 2>/dev/null || echo "")
        
        if [ "$CURRENT_ANNOTATION" = "$ROLE_ARN" ]; then
            echo -e "${GREEN}✅ Service account tiene la anotación correcta${NC}"
        else
            echo -e "${YELLOW}⚠️  Service account necesita actualizar anotación${NC}"
            echo -e "${YELLOW}   Actual: $CURRENT_ANNOTATION${NC}"
            echo -e "${YELLOW}   Esperado: $ROLE_ARN${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Service account $SERVICE_ACCOUNT no existe en namespace $NAMESPACE${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  kubectl no está disponible, saltando verificación de service account${NC}"
fi

# 7. Verificar tablas DynamoDB
echo -e "${BLUE}🗄️  Verificando tablas DynamoDB...${NC}"
aws dynamodb describe-table --table-name task-scheduler-logs-production >/dev/null 2>&1
check_result $? "Tabla task-scheduler-logs-production existe"

aws dynamodb describe-table --table-name cost-center-permissions-production >/dev/null 2>&1
check_result $? "Tabla cost-center-permissions-production existe"

# 8. Mostrar información del rol
echo ""
echo -e "${BLUE}📋 Información del rol:${NC}"
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "   ARN: $ROLE_ARN"
echo "   OIDC Issuer: $OIDC_ISSUER"

# 9. Mostrar trust policy
echo ""
echo -e "${BLUE}🤝 Trust Policy:${NC}"
aws iam get-role --role-name $ROLE_NAME --query 'Role.AssumeRolePolicyDocument' --output json | jq .

# 10. Mostrar políticas adjuntas
echo ""
echo -e "${BLUE}📋 Políticas adjuntas:${NC}"
aws iam list-attached-role-policies --role-name $ROLE_NAME --query 'AttachedPolicies[].PolicyName' --output table

# 11. Mostrar detalles de la política DynamoDB
echo ""
echo -e "${BLUE}🗄️  Permisos DynamoDB:${NC}"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"
POLICY_VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN --query 'Policy.DefaultVersionId' --output text)
aws iam get-policy-version --policy-arn $POLICY_ARN --version-id $POLICY_VERSION --query 'PolicyVersion.Document' --output json | jq .

echo ""
echo -e "${GREEN}✅ Validación completada!${NC}"
echo ""
echo -e "${YELLOW}🔧 Variables de entorno para el deployment:${NC}"
echo "   EKS_CLUSTER_NAME: $EKS_CLUSTER_NAME"
echo "   AWS_REGION: $AWS_REGION"
echo "   DYNAMODB_TABLE_NAME: task-scheduler-logs-production"
echo "   PERMISSIONS_TABLE_NAME: cost-center-permissions-production"
echo ""
echo -e "${YELLOW}🚀 Para aplicar cambios:${NC}"
echo "   1. Asegurar que el service account tiene la anotación correcta"
echo "   2. Reiniciar el deployment: kubectl rollout restart deployment/task-scheduler -n $NAMESPACE"
echo "   3. Verificar logs: kubectl logs deployment/task-scheduler -n $NAMESPACE"