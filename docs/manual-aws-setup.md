# Configuración Manual de AWS para GitHub Actions

## 🎯 Objetivo

Configurar AWS OIDC y ECR para que GitHub Actions pueda construir y subir imágenes Docker automáticamente.

## 📋 Prerrequisitos

- Cuenta de AWS con permisos administrativos
- Acceso a la consola de AWS
- Repositorio GitHub: `bcocbo/apagado-automatico`

## 🔧 Paso 1: Configurar AWS CLI (Opcional)

Si quieres usar el script automatizado:

```bash
# Configurar AWS CLI
aws configure

# Ingresar:
# AWS Access Key ID: [tu-access-key]
# AWS Secret Access Key: [tu-secret-key]  
# Default region name: us-east-1
# Default output format: json

# Verificar configuración
aws sts get-caller-identity
```

## 🔐 Paso 2: Crear OIDC Identity Provider

### Opción A: Usando AWS CLI
```bash
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Opción B: Usando la Consola AWS

1. Ve a **IAM** → **Identity providers**
2. Clic en **Add provider**
3. Selecciona **OpenID Connect**
4. **Provider URL**: `https://token.actions.githubusercontent.com`
5. **Audience**: `sts.amazonaws.com`
6. Clic en **Add provider**

## 👤 Paso 3: Crear IAM Role para GitHub Actions

### Crear Policy para ECR

1. Ve a **IAM** → **Policies** → **Create policy**
2. Selecciona **JSON** y pega:

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

3. **Name**: `ECRGitHubActionsPolicy`
4. Clic en **Create policy**

### Crear IAM Role

1. Ve a **IAM** → **Roles** → **Create role**
2. Selecciona **Web identity**
3. **Identity provider**: Selecciona el OIDC provider creado
4. **Audience**: `sts.amazonaws.com`
5. Clic en **Next**
6. Busca y selecciona `ECRGitHubActionsPolicy`
7. Clic en **Next**
8. **Role name**: `GitHubActionsECRRole`
9. Clic en **Create role**

### Configurar Trust Policy

1. Ve al role `GitHubActionsECRRole`
2. Pestaña **Trust relationships** → **Edit trust policy**
3. Reemplaza con:

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
                    "token.actions.githubusercontent.com:sub": "repo:bcocbo/apagado-automatico:*"
                }
            }
        }
    ]
}
```

**⚠️ Importante**: Reemplaza `TU-ACCOUNT-ID` con tu AWS Account ID real.

## 📦 Paso 4: Crear Repositorios ECR

### Opción A: Usando AWS CLI
```bash
aws ecr create-repository --repository-name namespace-scaler --region us-east-1
aws ecr create-repository --repository-name namespace-frontend --region us-east-1
```

### Opción B: Usando la Consola AWS

1. Ve a **ECR** → **Repositories**
2. Clic en **Create repository**
3. **Repository name**: `namespace-scaler`
4. Deja las demás opciones por defecto
5. Clic en **Create repository**
6. Repite para `namespace-frontend`

## 🔑 Paso 5: Configurar GitHub Secret

1. Ve a tu repositorio GitHub: `https://github.com/bcocbo/apagado-automatico`
2. **Settings** → **Secrets and variables** → **Actions**
3. Clic en **New repository secret**
4. **Name**: `AWS_ROLE_ARN`
5. **Value**: `arn:aws:iam::TU-ACCOUNT-ID:role/GitHubActionsECRRole`
6. Clic en **Add secret**

**⚠️ Importante**: Reemplaza `TU-ACCOUNT-ID` con tu AWS Account ID real.

## 🧪 Paso 6: Probar el Pipeline

1. Haz cualquier cambio en el repositorio
2. Haz commit y push:
   ```bash
   git add .
   git commit -m "Test AWS OIDC configuration"
   git push origin main
   ```
3. Ve a **Actions** en GitHub para ver el pipeline ejecutándose

## ✅ Verificación

Si todo está configurado correctamente, deberías ver:

1. ✅ **validate-kyverno** - Pasa
2. ✅ **lint-yaml** - Pasa  
3. ✅ **build-and-push-images** - Pasa y sube imágenes a ECR
4. ✅ **update-manifests** - Actualiza los manifests con las nuevas imágenes

## 🔍 Troubleshooting

### Error: "No OpenIDConnect provider found"
- Verifica que el OIDC provider esté creado
- Confirma que la URL sea exactamente: `https://token.actions.githubusercontent.com`

### Error: "AssumeRoleWithWebIdentity failed"
- Verifica que el trust policy tenga el repositorio correcto
- Confirma que el Account ID sea correcto

### Error: "Access denied to ECR"
- Verifica que la policy ECR esté attachada al role
- Confirma que los repositorios ECR existan

## 📊 Costos Estimados

- **OIDC Provider**: $0.00
- **IAM Roles**: $0.00
- **ECR Repositories**: ~$0.10/mes (1GB storage)

## 🎉 ¡Listo!

Una vez configurado, el pipeline construirá y subirá automáticamente las imágenes Docker a ECR cada vez que hagas push al repositorio.

---

**¿Necesitas ayuda?** Revisa los logs del pipeline en GitHub Actions para identificar errores específicos.