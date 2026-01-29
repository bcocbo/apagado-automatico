#!/bin/bash
# setup-controller-iam-role.sh - Script para crear IAM Role para el controlador de namespaces

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Configurando IAM Role para el controlador de namespaces...${NC}"

# Verificar que AWS CLI esté configurado
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI no está configurado o no tienes permisos${NC}"
    echo "Ejecuta: aws configure"
    exit 1
fi

# Obtener información del cluster EKS
read -p "🔗 Ingresa el nombre de tu cluster EKS: " CLUSTER_NAME
read -p "🌍 Ingresa la región AWS (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

if [[ -z "$CLUSTER_NAME" ]]; then
    echo -e "${RED}❌ Error: Debes proporcionar el nombre del cluster EKS${NC}"
    exit 1
fi

# Obtener Account ID automáticamente
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}📋 Información de configuración:${NC}"
echo "Account ID: $ACCOUNT_ID"
echo "Región: $AWS_REGION"
echo "Cluster EKS: $CLUSTER_NAME"
echo ""

# Obtener OIDC Issuer URL del cluster EKS
echo -e "${BLUE}🔍 Obteniendo información del cluster EKS...${NC}"
OIDC_ISSUER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION --query "cluster.identity.oidc.issuer" --output text)

if [[ -z "$OIDC_ISSUER" ]]; then
    echo -e "${RED}❌ Error: No se pudo obtener el OIDC Issuer del cluster${NC}"
    echo "Verifica que el cluster $CLUSTER_NAME existe en la región $AWS_REGION"
    exit 1
fi

# Extraer el ID del OIDC Issuer
OIDC_ID=$(echo $OIDC_ISSUER | sed 's|https://||' | sed 's|\..*||')
echo -e "${GREEN}✅ OIDC Issuer encontrado: $OIDC_ISSUER${NC}"

# Verificar si el OIDC Identity Provider ya existe
echo -e "${BLUE}📝 Verificando OIDC Identity Provider...${NC}"
OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER#https://}"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" &> /dev/null; then
    echo -e "${GREEN}✅ OIDC Provider ya existe${NC}"
else
    echo -e "${YELLOW}⚠️  OIDC Provider no existe. Creándolo...${NC}"
    
    # Obtener el thumbprint del OIDC provider
    THUMBPRINT=$(echo | openssl s_client -servername ${OIDC_ISSUER#https://} -connect ${OIDC_ISSUER#https://}:443 2>/dev/null | openssl x509 -fingerprint -noout -sha1 | sed 's/://g' | awk -F= '{print tolower($2)}')
    
    aws iam create-open-id-connect-provider \
        --url $OIDC_ISSUER \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list $THUMBPRINT \
        && echo -e "${GREEN}✅ OIDC Provider creado${NC}"
fi

# Crear policy para DynamoDB
echo -e "${BLUE}📋 Creando policy para DynamoDB...${NC}"
cat > /tmp/dynamodb-policy.json << EOF
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
                "dynamodb:DescribeTable",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/NamespaceSchedules",
                "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/NamespaceSchedules/index/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name NamespaceControllerDynamoDBPolicy \
    --policy-document file:///tmp/dynamodb-policy.json \
    --description "Policy para que el controlador de namespaces acceda a DynamoDB" \
    2>/dev/null && echo -e "${GREEN}✅ DynamoDB Policy creada${NC}" || echo -e "${YELLOW}⚠️  DynamoDB Policy ya existe${NC}"

# Crear trust policy para IRSA
echo -e "${BLUE}🔐 Creando trust policy para IRSA...${NC}"
cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER#https://}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_ISSUER#https://}:sub": "system:serviceaccount:encendido-eks:scaler-sa",
                    "${OIDC_ISSUER#https://}:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
EOF

# Crear IAM Role
echo -e "${BLUE}👤 Creando IAM Role para el controlador...${NC}"
aws iam create-role \
    --role-name NamespaceControllerRole \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    --description "Role para el controlador de namespaces con acceso a DynamoDB" \
    2>/dev/null && echo -e "${GREEN}✅ IAM Role creado${NC}" || echo -e "${YELLOW}⚠️  IAM Role ya existe${NC}"

# Attachar policy al role
echo -e "${BLUE}🔗 Attachando policy al role...${NC}"
aws iam attach-role-policy \
    --role-name NamespaceControllerRole \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/NamespaceControllerDynamoDBPolicy \
    && echo -e "${GREEN}✅ Policy attachada al role${NC}"

# Crear tabla DynamoDB si no existe
echo -e "${BLUE}📦 Verificando tabla DynamoDB...${NC}"
if aws dynamodb describe-table --table-name NamespaceSchedules --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✅ Tabla NamespaceSchedules ya existe${NC}"
else
    echo -e "${YELLOW}⚠️  Tabla NamespaceSchedules no existe. Creándola...${NC}"
    
    aws dynamodb create-table \
        --table-name NamespaceSchedules \
        --attribute-definitions \
            AttributeName=namespace,AttributeType=S \
        --key-schema \
            AttributeName=namespace,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION \
        && echo -e "${GREEN}✅ Tabla DynamoDB creada${NC}"
    
    # Esperar a que la tabla esté activa
    echo -e "${BLUE}⏳ Esperando a que la tabla esté activa...${NC}"
    aws dynamodb wait table-exists --table-name NamespaceSchedules --region $AWS_REGION
    echo -e "${GREEN}✅ Tabla DynamoDB está activa${NC}"
fi

# Cleanup
rm -f /tmp/dynamodb-policy.json /tmp/trust-policy.json

echo ""
echo -e "${GREEN}🎉 ¡Setup del IAM Role completado exitosamente!${NC}"
echo ""
echo -e "${YELLOW}📋 INFORMACIÓN IMPORTANTE:${NC}"
echo -e "${BLUE}IAM Role ARN:${NC} arn:aws:iam::${ACCOUNT_ID}:role/NamespaceControllerRole"
echo -e "${BLUE}DynamoDB Table:${NC} NamespaceSchedules"
echo -e "${BLUE}ServiceAccount:${NC} scaler-sa (namespace: encendido-eks)"
echo ""
echo -e "${YELLOW}🔧 PRÓXIMOS PASOS:${NC}"
echo "1. Anotar el ServiceAccount con el IAM Role ARN:"
echo -e "   ${BLUE}kubectl annotate serviceaccount scaler-sa -n encendido-eks \\${NC}"
echo -e "   ${BLUE}    eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/NamespaceControllerRole${NC}"
echo ""
echo "2. Reiniciar el deployment del controlador:"
echo -e "   ${BLUE}kubectl rollout restart deployment namespace-scaler -n encendido-eks${NC}"
echo ""
echo "3. Verificar que el pod tenga acceso a DynamoDB:"
echo -e "   ${BLUE}kubectl logs -f deployment/namespace-scaler -n encendido-eks${NC}"
echo ""
echo -e "${GREEN}✅ ¡El controlador ahora debería tener acceso a DynamoDB!${NC}"