# Configuración de GitHub Actions para Task Scheduler

## Prerrequisitos

### 1. Permisos de AWS
- Acceso de administrador a la cuenta AWS `226633502530`
- AWS CLI configurado con credenciales apropiadas
- Permisos para crear/modificar:
  - Roles de IAM
  - Políticas de IAM
  - OIDC Identity Providers

### 2. Acceso a GitHub
- Permisos de administrador en el repositorio `bcocbo/apagado-automatico`
- Capacidad para configurar secrets del repositorio
- Capacidad para crear/modificar workflows

### 3. Herramientas Requeridas
- AWS CLI v2
- OpenSSL (para generar thumbprints)
- Bash shell
- Git

## Arquitectura del Workflow

El workflow de GitHub Actions (`build.yaml`) implementa:

### 1. Build Paralelo
- **Frontend**: Construye imagen `task-scheduler-frontend`
- **Backend**: Construye imagen `task-scheduler-backend` (anteriormente kubectl-runner)

### 2. Actualización de Manifiestos
- **Estrategia**: Actualiza tags directamente en el mismo repositorio
- **Archivo objetivo**: `manifests/overlays/production/kustomization.yaml`
- **Método**: Usa `sed` para actualizar el campo `newTag` con el SHA del commit

### 3. Seguridad Mejorada
- **OIDC**: Usa roles de IAM sin credenciales de larga duración
- **Secrets parametrizados**: ARN del rol y región desde GitHub Secrets
- **Permisos mínimos**: Solo acceso a ECR y escritura en el repositorio

## Pasos de Configuración

### Paso 1: Ejecutar Script de IAM

```bash
# Hacer el script ejecutable
chmod +x scripts/setup-github-actions-iam.sh

# Ejecutar el script
./scripts/setup-github-actions-iam.sh
```

Este script creará:
- **Política ECR**: `GitHubActions-TaskScheduler-ECR-Policy`
- **Rol IAM**: `GitHubActions-TaskScheduler-Role`
- **OIDC Provider**: Para GitHub Actions (si no existe)

### Paso 2: Configurar Secrets en GitHub

Ve a: `https://github.com/bcocbo/apagado-automatico/settings/secrets/actions`

Configura los siguientes secrets:

| Secret Name | Value | Descripción |
|-------------|-------|-------------|
| `AWS_REGION` | `us-east-1` | Región de AWS |
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role` | ARN del rol de IAM |
| `GITHUB_TOKEN` | (automático) | Token automático de GitHub para commits |

### Paso 3: Verificar Configuración

```bash
# Verificar que el rol existe
aws iam get-role --role-name GitHubActions-TaskScheduler-Role

# Verificar que la política está adjunta
aws iam list-attached-role-policies --role-name GitHubActions-TaskScheduler-Role

# Verificar OIDC provider
aws iam list-open-id-connect-providers
```

## Estructura de Permisos

### Política ECR Creada

La política `GitHubActions-TaskScheduler-ECR-Policy` permite:

- **Autenticación**: `ecr:GetAuthorizationToken`
- **Pull de imágenes**: `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`
- **Push de imágenes**: `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`

### Repositorios ECR Permitidos

- `task-scheduler-frontend`
- `task-scheduler-backend`

### Trust Policy

El rol solo puede ser asumido por:
- GitHub Actions del repositorio `bcocbo/apagado-automatico`
- Cualquier branch o pull request del repositorio

## Troubleshooting

### Error: "OIDC provider does not exist"

```bash
# Crear manualmente el OIDC provider
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Error: "Role already exists"

```bash
# Actualizar la trust policy del rol existente
aws iam update-assume-role-policy \
    --role-name GitHubActions-TaskScheduler-Role \
    --policy-document file://trust-policy.json
```

### Error: "Access denied to ECR"

Verificar que:
1. Los repositorios ECR existen
2. La política tiene los ARNs correctos
3. El rol tiene la política adjunta

## Validación

### Test de Autenticación ECR

```bash
# Simular lo que haría GitHub Actions
aws sts assume-role-with-web-identity \
    --role-arn arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role \
    --role-session-name test-session \
    --web-identity-token $GITHUB_TOKEN

# Login a ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin 226633502530.dkr.ecr.us-east-1.amazonaws.com
```

## Próximos Pasos

Después de completar esta configuración:

1. **Crear workflows de GitHub Actions** (Tarea 1.2)
2. **Configurar secrets adicionales** si es necesario
3. **Probar el pipeline completo** con un push de prueba

## Seguridad

### Principio de Menor Privilegio

- El rol solo tiene permisos para ECR
- Solo puede acceder a los repositorios específicos del proyecto
- Solo puede ser asumido por el repositorio específico de GitHub

### Rotación de Credenciales

- No se usan credenciales de larga duración
- Los tokens de GitHub Actions expiran automáticamente
- El rol se asume dinámicamente en cada ejecución

### Auditoría

- Todas las acciones quedan registradas en CloudTrail
- Los logs de GitHub Actions muestran el uso del rol
- Las políticas pueden ser revisadas periódicamente