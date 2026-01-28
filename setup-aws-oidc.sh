#!/bin/bash
# setup-aws-oidc.sh - Script para configurar OIDC con GitHub Actions

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Configurando OIDC para GitHub Actions...${NC}"

# Verificar que AWS CLI esté configurado
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI no está configurado o no tienes permisos${NC}"
    echo "Ejecuta: aws configure"
    exit 1
fi

# Obtener Account ID automáticamente
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${YELLOW}📋 Información de configuración:${NC}"
echo "Account ID: $ACCOUNT_ID"
echo "Región: $AWS_REGION"
echo ""

# Solicitar información del repositorio
read -p "🔗 Ingresa tu repositorio GitHub (formato: usuario/repo): " GITHUB_REPO

if [[ -z "$GITHUB_REPO" ]]; then
    echo -e "${RED}❌ Error: Debes proporcionar el repositorio GitHub${NC}"
    exit 1
fi

echo -e "${BLUE}📝 Paso 1: Creando OIDC Identity Provider...${NC}"
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
    2>/dev/null && echo -e "${GREEN}✅ OIDC Provider creado${NC}" || echo -e "${YELLOW}⚠️  OIDC Provider ya existe${NC}"

echo -e "${BLUE}📋 Paso 2: Creando policy para ECR...${NC}"
cat > /tmp/ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchImportLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:DescribeRepositories",
                "ecr:InitiateLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name ECRGitHubActionsPolicy \
    --policy-document file:///tmp/ecr-policy.json \
    2>/dev/null && echo -e "${GREEN}✅ ECR Policy creada${NC}" || echo -e "${YELLOW}⚠️  ECR Policy ya existe${NC}"

echo -e "${BLUE}🔐 Paso 3: Creando trust policy...${NC}"
cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*"
                }
            }
        }
    ]
}
EOF

echo -e "${BLUE}👤 Paso 4: Creando IAM Role...${NC}"
aws iam create-role \
    --role-name GitHubActionsECRRole \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    2>/dev/null && echo -e "${GREEN}✅ IAM Role creado${NC}" || echo -e "${YELLOW}⚠️  IAM Role ya existe${NC}"

echo -e "${BLUE}🔗 Paso 5: Attachando policy al role...${NC}"
aws iam attach-role-policy \
    --role-name GitHubActionsECRRole \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/ECRGitHubActionsPolicy \
    && echo -e "${GREEN}✅ Policy attachada al role${NC}"

echo -e "${BLUE}📦 Paso 6: Creando repositorios ECR...${NC}"
aws ecr create-repository \
    --repository-name namespace-scaler \
    --region ${AWS_REGION} \
    2>/dev/null && echo -e "${GREEN}✅ Repositorio namespace-scaler creado${NC}" || echo -e "${YELLOW}⚠️  Repositorio namespace-scaler ya existe${NC}"

aws ecr create-repository \
    --repository-name namespace-frontend \
    --region ${AWS_REGION} \
    2>/dev/null && echo -e "${GREEN}✅ Repositorio namespace-frontend creado${NC}" || echo -e "${YELLOW}⚠️  Repositorio namespace-frontend ya existe${NC}"

# Cleanup
rm -f /tmp/ecr-policy.json /tmp/trust-policy.json

echo ""
echo -e "${GREEN}🎉 ¡Setup completado exitosamente!${NC}"
echo ""
echo -e "${YELLOW}📋 INFORMACIÓN IMPORTANTE:${NC}"
echo -e "${BLUE}AWS_ROLE_ARN:${NC} arn:aws:iam::${ACCOUNT_ID}:role/GitHubActionsECRRole"
echo ""
echo -e "${YELLOW}🔧 PRÓXIMOS PASOS:${NC}"
echo "1. Ve a tu repositorio GitHub: https://github.com/${GITHUB_REPO}"
echo "2. Ve a Settings → Secrets and variables → Actions"
echo "3. Clic en 'New repository secret'"
echo "4. Añade este secret:"
echo -e "   ${BLUE}Name:${NC} AWS_ROLE_ARN"
echo -e "   ${BLUE}Value:${NC} arn:aws:iam::${ACCOUNT_ID}:role/GitHubActionsECRRole"
echo ""
echo -e "${YELLOW}📦 Repositorios ECR creados:${NC}"
echo "• ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-scaler"
echo "• ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-frontend"
echo ""
echo -e "${GREEN}✅ ¡Listo para usar GitHub Actions con OIDC!${NC}"