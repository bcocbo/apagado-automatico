# Configuración AWS OIDC para GitHub Actions

## 1. Crear OIDC Identity Provider en AWS

### Usando AWS CLI:

```bash
# Crear el OIDC Identity Provider
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Verificar que se creó correctamente
aws iam list-open-id-connect-providers
```

### Usando AWS Console:
1. Ve a IAM → Identity providers
2. Clic en "Add provider"
3. Selecciona "OpenID Connect"
4. Provider URL: `https://token.actions.githubusercontent.com`
5. Audience: `sts.amazonaws.com`

## 2. Crear IAM Role para GitHub Actions

### Policy para ECR (ecr-github-actions-policy.json):

```json
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
```

### Trust Policy (trust-policy.json):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::TU-ACCOUNT-ID:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:TU-USUARIO/apagado-automatico:*"
                }
            }
        }
    ]
}
```

### Crear el Role:

```bash
# Crear la policy
aws iam create-policy \
    --policy-name ECRGitHubActionsPolicy \
    --policy-document file://ecr-github-actions-policy.json

# Crear el role
aws iam create-role \
    --role-name GitHubActionsECRRole \
    --assume-role-policy-document file://trust-policy.json

# Attachar la policy al role
aws iam attach-role-policy \
    --role-name GitHubActionsECRRole \
    --policy-arn arn:aws:iam::TU-ACCOUNT-ID:policy/ECRGitHubActionsPolicy
```

## 3. Crear Repositorios ECR

```bash
# Crear repositorio para el controller
aws ecr create-repository \
    --repository-name namespace-scaler \
    --region us-east-1

# Crear repositorio para el frontend
aws ecr create-repository \
    --repository-name namespace-frontend \
    --region us-east-1
```

## 4. Configurar GitHub Secrets

En tu repositorio de GitHub, ve a Settings → Secrets and variables → Actions y añade:

- `AWS_ROLE_ARN`: `arn:aws:iam::TU-ACCOUNT-ID:role/GitHubActionsECRRole`

## 5. Script de Setup Automatizado

```bash
#!/bin/bash
# setup-aws-oidc.sh

set -e

# Variables - MODIFICA ESTOS VALORES
ACCOUNT_ID="123456789012"  # Tu AWS Account ID
GITHUB_REPO="tu-usuario/apagado-automatico"  # Tu repositorio GitHub
AWS_REGION="us-east-1"

echo "🚀 Configurando OIDC para GitHub Actions..."

# 1. Crear OIDC Provider
echo "📝 Creando OIDC Identity Provider..."
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
    || echo "OIDC Provider ya existe"

# 2. Crear policy para ECR
echo "📋 Creando policy para ECR..."
cat > ecr-policy.json << EOF
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
    --policy-document file://ecr-policy.json \
    || echo "Policy ya existe"

# 3. Crear trust policy
echo "🔐 Creando trust policy..."
cat > trust-policy.json << EOF
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

# 4. Crear role
echo "👤 Creando IAM Role..."
aws iam create-role \
    --role-name GitHubActionsECRRole \
    --assume-role-policy-document file://trust-policy.json \
    || echo "Role ya existe"

# 5. Attachar policy al role
echo "🔗 Attachando policy al role..."
aws iam attach-role-policy \
    --role-name GitHubActionsECRRole \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/ECRGitHubActionsPolicy

# 6. Crear repositorios ECR
echo "📦 Creando repositorios ECR..."
aws ecr create-repository \
    --repository-name namespace-scaler \
    --region ${AWS_REGION} \
    || echo "Repositorio namespace-scaler ya existe"

aws ecr create-repository \
    --repository-name namespace-frontend \
    --region ${AWS_REGION} \
    || echo "Repositorio namespace-frontend ya existe"

# 7. Mostrar información importante
echo ""
echo "✅ Setup completado!"
echo ""
echo "📋 Información importante:"
echo "AWS_ROLE_ARN: arn:aws:iam::${ACCOUNT_ID}:role/GitHubActionsECRRole"
echo ""
echo "🔧 Próximos pasos:"
echo "1. Añade este secret en GitHub:"
echo "   AWS_ROLE_ARN=arn:aws:iam::${ACCOUNT_ID}:role/GitHubActionsECRRole"
echo ""
echo "2. Verifica que los repositorios ECR estén creados:"
echo "   - ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-scaler"
echo "   - ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-frontend"

# Cleanup
rm -f ecr-policy.json trust-policy.json

echo ""
echo "🎉 ¡Listo para usar GitHub Actions con OIDC!"
```

## 6. Verificación

### Verificar OIDC Provider:
```bash
aws iam list-open-id-connect-providers
```

### Verificar Role:
```bash
aws iam get-role --role-name GitHubActionsECRRole
```

### Verificar Repositorios ECR:
```bash
aws ecr describe-repositories --region us-east-1
```

## 7. Troubleshooting

### Error: "No OpenIDConnect provider found"
- Verifica que el OIDC provider esté creado correctamente
- Confirma que la URL sea exactamente: `https://token.actions.githubusercontent.com`

### Error: "AssumeRoleWithWebIdentity failed"
- Verifica que el trust policy tenga el repositorio correcto
- Confirma que el condition string sea exacto

### Error: "Access denied to ECR"
- Verifica que la policy ECR esté attachada al role
- Confirma que los permisos ECR incluyan todas las acciones necesarias

## 8. Seguridad Best Practices

1. **Principio de menor privilegio**: Solo otorga permisos ECR necesarios
2. **Restricción por repositorio**: El trust policy solo permite tu repositorio específico
3. **Tokens de corta duración**: Los tokens OIDC expiran en 15 minutos
4. **Auditoría**: Monitorea el uso del role en CloudTrail
5. **Rotación**: No hay keys que rotar, OIDC maneja la autenticación automáticamente