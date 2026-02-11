#!/bin/bash
# Script para configurar IAM Role y políticas para GitHub Actions

set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="226633502530"
GITHUB_REPO="bcocbo/apagado-automatico"
ROLE_NAME="GitHubActions-TaskScheduler-Role"
POLICY_NAME="GitHubActions-TaskScheduler-ECR-Policy"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Configurando IAM para GitHub Actions...${NC}"

# 1. Crear política para ECR
echo -e "${BLUE}📋 Creando política ECR...${NC}"
cat > /tmp/github-actions-ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": [
                "arn:aws:ecr:${AWS_REGION}:${AWS_ACCOUNT_ID}:repository/task-scheduler-frontend",
                "arn:aws:ecr:${AWS_REGION}:${AWS_ACCOUNT_ID}:repository/kubectl-runner"
            ]
        }
    ]
}
EOF

# Crear la política
aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file:///tmp/github-actions-ecr-policy.json \
    --description "Política para que GitHub Actions pueda acceder a ECR" \
    2>/dev/null || echo "✓ Política $POLICY_NAME ya existe"

# 2. Crear trust policy para GitHub Actions OIDC
echo -e "${BLUE}🤝 Creando trust policy para GitHub OIDC...${NC}"
cat > /tmp/github-actions-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
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

# 3. Crear el rol de IAM
echo -e "${BLUE}👤 Creando rol de IAM...${NC}"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/github-actions-trust-policy.json \
    --description "Rol para GitHub Actions del proyecto Task Scheduler" \
    2>/dev/null || echo "✓ Rol $ROLE_NAME ya existe"

# 4. Adjuntar la política al rol
echo -e "${BLUE}🔗 Adjuntando política al rol...${NC}"
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

# 5. Verificar que el OIDC provider existe
echo -e "${BLUE}🔍 Verificando OIDC provider...${NC}"
if ! aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com" \
    >/dev/null 2>&1; then
    
    echo -e "${YELLOW}⚠️  OIDC provider no existe. Creándolo...${NC}"
    
    # Obtener el thumbprint de GitHub
    THUMBPRINT=$(echo | openssl s_client -servername token.actions.githubusercontent.com -connect token.actions.githubusercontent.com:443 2>/dev/null | openssl x509 -fingerprint -noout -sha1 | cut -d= -f2 | tr -d :)
    
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list $THUMBPRINT
    
    echo -e "${GREEN}✅ OIDC provider creado${NC}"
else
    echo -e "${GREEN}✅ OIDC provider ya existe${NC}"
fi

# Limpiar archivos temporales
rm -f /tmp/github-actions-*.json

echo ""
echo -e "${GREEN}✅ Configuración de IAM completada!${NC}"
echo ""
echo -e "${YELLOW}📋 Información para GitHub Secrets:${NC}"
echo "   AWS_REGION: $AWS_REGION"
echo "   AWS_ROLE_TO_ASSUME: arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo -e "${YELLOW}🚀 Siguiente paso:${NC}"
echo "   1. Configurar los secrets en GitHub"
echo "   2. Crear los workflows de GitHub Actions"
echo ""
echo -e "${BLUE}💡 Para configurar secrets en GitHub:${NC}"
echo "   - Ve a: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo "   - Agrega los secrets mostrados arriba"