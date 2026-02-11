# Configuración de Secrets de AWS en GitHub

## Resumen
Esta guía explica cómo configurar los secrets de AWS necesarios para que GitHub Actions pueda construir y desplegar las imágenes del Task Scheduler usando OIDC y actualización automática de manifiestos.

## Secrets Requeridos

Los siguientes secrets deben configurarse en GitHub:

### 1. AWS_REGION
- **Valor**: `us-east-1`
- **Descripción**: Región de AWS donde están los recursos ECR

### 2. AWS_ROLE_TO_ASSUME
- **Valor**: `arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role`
- **Descripción**: ARN del rol de IAM para GitHub Actions
- **Nota**: Ahora es requerido ya que se usa desde secrets en lugar de estar hardcodeado

### 3. GITHUB_TOKEN
- **Valor**: Automático
- **Descripción**: Token automático de GitHub para commits de actualización de manifiestos
- **Permisos**: `contents: write` configurado en el workflow

## Pasos para Configurar Secrets

### 1. Acceder a la Configuración de Secrets
1. Ve a: https://github.com/bcocbo/apagado-automatico/settings/secrets/actions
2. Haz clic en "New repository secret"

### 2. Configurar cada Secret
Para cada secret listado arriba:
1. Ingresa el **Name** exactamente como se muestra
2. Ingresa el **Value** correspondiente
3. Haz clic en "Add secret"

## Verificación de la Configuración

### 1. Verificar que el Rol de IAM Existe
```bash
aws iam get-role --role-name GitHubActions-TaskScheduler-Role
```

### 2. Verificar Permisos del Rol
```bash
aws iam list-attached-role-policies --role-name GitHubActions-TaskScheduler-Role
```

### 3. Probar el Workflow
1. Haz un push a la rama `main` o `develop`
2. Ve a la pestaña "Actions" en GitHub
3. Verifica que el workflow se ejecute sin errores

## Rol Anterior a Eliminar

El rol anterior que debe eliminarse de IAM es:
- **Nombre**: `github-actions-role`
- **ARN**: `arn:aws:iam::226633502530:role/github-actions-role`

### Comando para Eliminar el Rol Anterior
```bash
# 1. Desadjuntar todas las políticas del rol
aws iam list-attached-role-policies --role-name github-actions-role

# 2. Desadjuntar cada política (ejemplo)
aws iam detach-role-policy --role-name github-actions-role --policy-arn arn:aws:iam::226633502530:policy/POLICY_NAME

# 3. Eliminar el rol
aws iam delete-role --role-name github-actions-role
```

## Troubleshooting

### Error: "Could not assume role"
- Verificar que el rol `GitHubActions-TaskScheduler-Role` existe
- Verificar que el OIDC provider está configurado
- Verificar que la trust policy permite el repositorio correcto

### Error: "Access denied to ECR"
- Verificar que el rol tiene la política ECR adjunta
- Verificar que los repositorios ECR existen:
  - `task-scheduler-frontend`
  - `task-scheduler-backend`

### Error: "Cannot update manifests"
- Verificar que el workflow tiene permisos `contents: write`
- Verificar que el archivo `manifests/overlays/production/kustomization.yaml` existe
- Verificar que el formato del archivo kustomization es correcto

## Seguridad

### Principios Aplicados
- **OIDC**: No se usan credenciales de larga duración
- **Principio de menor privilegio**: El rol solo tiene permisos ECR
- **Scope limitado**: Solo el repositorio específico puede usar el rol

### Rotación de Tokens
- El `GITHUB_TOKEN` se genera automáticamente para cada workflow run
- Los tokens de GitHub Actions expiran automáticamente
- El rol de IAM se asume dinámicamente en cada ejecución
- No se requieren tokens de larga duración

## Estado Actual del Workflow

El workflow actual (`build.yaml`) está configurado para:

### 1. Build Jobs Paralelos
- **build-frontend**: Construye imagen `task-scheduler-frontend`
- **build-backend**: Construye imagen `task-scheduler-backend` (renombrado desde kubectl-runner)

### 2. Configuración de Seguridad
- **OIDC**: Usa `aws-actions/configure-aws-credentials@v4` con role assumption
- **Secrets parametrizados**: `AWS_ROLE_TO_ASSUME` y `AWS_REGION` desde GitHub Secrets
- **Permisos mínimos**: Solo ECR y escritura en repositorio

### 3. Actualización de Manifiestos
- **Estrategia**: Actualiza el mismo repositorio (no repositorio externo)
- **Archivo**: `manifests/overlays/production/kustomization.yaml`
- **Método**: Usa `sed` para actualizar `newTag` con commit SHA
- **Commit**: Automático con mensaje `[skip ci]` para evitar loops infinitos

### 4. Mejoras Implementadas
- **Nomenclatura consistente**: `ECR_REPOSITORY_BACKEND` en lugar de `ECR_REPOSITORY_KUBECTL`
- **Jobs renombrados**: `build-backend` en lugar de `build-kubectl-runner`
- **Eliminación de repositorio externo**: Simplifica la gestión de manifiestos
- **Uso de GITHUB_TOKEN**: Elimina necesidad de tokens personales

## Próximos Pasos

Después de configurar los secrets:
1. Ejecutar el script `scripts/setup-github-actions-iam.sh` si no se ha hecho
2. Eliminar el rol anterior `github-actions-role`
3. Probar el workflow con un push de prueba
4. Verificar que las imágenes se construyen correctamente en ECR