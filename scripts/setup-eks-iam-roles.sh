#!/bin/bash
# Script para configurar IAM roles para acceso desde EKS a DynamoDB

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

echo -e "${BLUE}🔐 Configurando IAM roles para EKS...${NC}"

# Función para verificar si un comando fue exitoso
check_command() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
        exit 1
    fi
}

# 1. Obtener el OIDC issuer URL del cluster EKS
echo -e "${BLUE}🔍 Obteniendo OIDC issuer URL del cluster EKS...${NC}"
OIDC_ISSUER=$(aws eks describe-cluster --name $EKS_CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text)
check_command "OIDC issuer obtenido: $OIDC_ISSUER"

# Extraer el ID del OIDC issuer
OIDC_ID=$(echo $OIDC_ISSUER | cut -d '/' -f 5)
echo -e "${BLUE}📋 OIDC ID: $OIDC_ID${NC}"

# 2. Verificar si el OIDC provider existe
echo -e "${BLUE}🤝 Verificando OIDC provider para EKS...${NC}"
OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/oidc.eks.${AWS_REGION}.amazonaws.com/id/${OIDC_ID}"

if ! aws iam get-open-id-connect-provider --open-id-connect-provider-arn $OIDC_PROVIDER_ARN >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  OIDC provider no existe. Creándolo...${NC}"
    
    # Obtener el certificado thumbprint
    THUMBPRINT=$(echo | openssl s_client -servername oidc.eks.${AWS_REGION}.amazonaws.com -connect oidc.eks.${AWS_REGION}.amazonaws.com:443 2>/dev/null | openssl x509 -fingerprint -noout -sha1 | cut -d= -f2 | tr -d :)
    
    aws iam create-open-id-connect-provider \
        --url $OIDC_ISSUER \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list $THUMBPRINT
    
    check_command "OIDC provider creado"
else
    echo -e "${GREEN}✅ OIDC provider ya existe${NC}"
fi

# 3. Crear política para DynamoDB
echo -e "${BLUE}📋 Creando política DynamoDB...${NC}"
cat > /tmp/kubectl-runner-dynamodb-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/task-scheduler-logs-production*",
                "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/cost-center-permissions-production*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:ListTables",
                "dynamodb:DescribeTable"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "eks:DescribeCluster"
            ],
            "Resource": "arn:aws:eks:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/eks-cloud"
        }
    ]
}
EOF

# Crear la política
aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file:///tmp/kubectl-runner-dynamodb-policy.json \
    --description "Política para que kubectl-runner pueda acceder a DynamoDB" \
    2>/dev/null || echo "✓ Política $POLICY_NAME ya existe"

# 4. Crear trust policy para el service account
echo -e "${BLUE}🤝 Creando trust policy para service account...${NC}"
cat > /tmp/kubectl-runner-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "$OIDC_PROVIDER_ARN"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_ISSUER#https://}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT}",
                    "${OIDC_ISSUER#https://}:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
EOF

# 5. Crear el rol de IAM
echo -e "${BLUE}👤 Creando rol de IAM...${NC}"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/kubectl-runner-trust-policy.json \
    --description "Rol para kubectl-runner service account en EKS" \
    2>/dev/null || echo "✓ Rol $ROLE_NAME ya existe"

# 6. Adjuntar la política al rol
echo -e "${BLUE}🔗 Adjuntando política al rol...${NC}"
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

check_command "Política adjuntada al rol"

# 7. Verificar que el service account tiene la anotación correcta
echo -e "${BLUE}🔍 Verificando anotación del service account...${NC}"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo -e "${YELLOW}📋 El service account debe tener esta anotación:${NC}"
echo "   eks.amazonaws.com/role-arn: $ROLE_ARN"

# Limpiar archivos temporales
rm -f /tmp/kubectl-runner-*.json

echo ""
echo -e "${GREEN}✅ Configuración de IAM para EKS completada!${NC}"
echo ""
echo -e "${YELLOW}📋 Información del rol creado:${NC}"
echo "   Nombre: $ROLE_NAME"
echo "   ARN: $ROLE_ARN"
echo "   Política: $POLICY_NAME"
echo ""
echo -e "${YELLOW}🔧 Variables de entorno para el deployment:${NC}"
echo "   EKS_CLUSTER_NAME: $EKS_CLUSTER_NAME"
echo "   AWS_REGION: $AWS_REGION"
echo "   DYNAMODB_TABLE_NAME: task-scheduler-logs-production"
echo "   PERMISSIONS_TABLE_NAME: cost-center-permissions-production"
echo ""
echo -e "${YELLOW}🚀 Próximos pasos:${NC}"
echo "   1. Verificar que el service account tiene la anotación correcta"
echo "   2. Reiniciar el deployment para que tome el nuevo rol"
echo "   3. Probar conectividad a DynamoDB"
echo ""
echo -e "${BLUE}💡 Para probar la configuración:${NC}"
echo "   kubectl get serviceaccount $SERVICE_ACCOUNT -n $NAMESPACE -o yaml"
echo "   kubectl logs deployment/task-scheduler -n $NAMESPACE"