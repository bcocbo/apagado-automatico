# GitHub Actions - Configuración ECR

Este directorio contiene los archivos necesarios para configurar GitHub Actions con acceso a Amazon ECR para el proyecto Task Scheduler.

## Archivos Incluidos

### Scripts de Configuración

- **`scripts/setup-github-actions-iam.sh`**: Script principal para configurar IAM roles y políticas
- **`scripts/validate-github-actions-setup.sh`**: Script para validar que la configuración esté correcta

### Documentación

- **`docs/github-actions-setup.md`**: Guía completa de configuración con prerrequisitos
- **`docs/github-workflow-example.yml`**: Ejemplo de workflow de GitHub Actions

## Inicio Rápido

### 1. Configurar IAM

```bash
# Ejecutar script de configuración
./scripts/setup-github-actions-iam.sh

# Validar configuración
./scripts/validate-github-actions-setup.sh
```

### 2. Configurar GitHub Secrets

Ve a: `https://github.com/bcocbo/apagado-automatico/settings/secrets/actions`

Agrega:
- `AWS_REGION`: `us-east-1`
- `AWS_ROLE_TO_ASSUME`: `arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role`

### 3. Crear Workflow

Copia el contenido de `docs/github-workflow-example.yml` a `.github/workflows/build-and-deploy.yml`

**Características del workflow:**
- Build automático de frontend y backend
- Push a ECR con tags SHA y latest
- Actualización automática de manifiestos Kubernetes
- Escaneo de seguridad opcional
- Ejecución en branches main y develop

## Recursos Creados

### IAM Role
- **Nombre**: `GitHubActions-TaskScheduler-Role`
- **ARN**: `arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role`
- **Propósito**: Permite a GitHub Actions acceder a ECR

### IAM Policy
- **Nombre**: `GitHubActions-TaskScheduler-ECR-Policy`
- **Permisos**: Login, push y pull de imágenes ECR
- **Repositorios**: `task-scheduler-frontend`, `task-scheduler-backend`

### OIDC Provider
- **URL**: `https://token.actions.githubusercontent.com`
- **Propósito**: Permite autenticación sin credenciales de larga duración

## Seguridad

- ✅ Sin credenciales de larga duración
- ✅ Principio de menor privilegio
- ✅ Acceso limitado al repositorio específico
- ✅ Permisos limitados a ECR únicamente
- ✅ Auditoría completa en CloudTrail

## Troubleshooting

### Problema: "No permission to assume role"

**Solución**: Verificar que los secrets estén configurados correctamente en GitHub

### Problema: "ECR repository does not exist"

**Solución**: Ejecutar `./scripts/create-ecr-repos.sh` primero

### Problema: "OIDC provider not found"

**Solución**: El script debería crear el provider automáticamente. Si falla, crearlo manualmente.

## Workflow Implementado

El workflow de ejemplo incluye los siguientes jobs:

### 1. Build Frontend (`build-frontend`)
- Construye imagen Docker desde `./frontend`
- Etiqueta con SHA del commit y `latest`
- Push a ECR: `task-scheduler-frontend`

### 2. Build Backend (`build-backend`)
- Construye imagen Docker desde `./kubectl-runner`
- Etiqueta con SHA del commit y `latest`
- Push a ECR: `task-scheduler-backend`

### 3. Update Manifests (`update-manifests`)
- Se ejecuta solo en branch `main`
- Actualiza tags en `manifests/overlays/production/kustomization.yaml`
- Hace commit automático de los cambios

### 4. Security Scan (`security-scan`)
- Ejecuta escaneo de vulnerabilidades en ECR
- Se ejecuta después de los builds
- Opcional: puede fallar sin afectar el pipeline

## Próximos Pasos

1. ✅ Configurar políticas de acceso para GitHub Actions
2. ✅ Crear workflow para build del frontend (Tarea 1.2)
3. ✅ Crear workflow para build del backend (Tarea 1.2)
4. ⏳ Configurar secrets de AWS en GitHub (Tarea 1.2)
5. ⏳ Configurar push automático a ECR (Tarea 1.2)
6. ⏳ Configurar actualización de tags en manifiestos (Tarea 1.2)

## Soporte

Para problemas o preguntas:
1. Revisar los logs de los scripts
2. Verificar la configuración con el script de validación
3. Consultar la documentación completa en `docs/github-actions-setup.md`