# Namespace Scheduler para EKS

Este proyecto reemplaza Backstage con un sistema de programación de tareas que incluye:

1. **Frontend**: Aplicación web con HTML + Nginx + FullCalendar para programar tareas
2. **kubectl-runner**: Contenedor Linux con kubectl para ejecutar comandos en el cluster EKS

## Arquitectura

```
┌─────────────────┐    ┌──────────────────┐
│   Frontend      │    │  kubectl-runner  │
│   (Nginx +      │◄──►│  (Python Flask + │
│   FullCalendar) │    │   kubectl + AWS) │
└─────────────────┘    └──────────────────┘
         │                       │
         └───────────────────────┘
                   │
            ┌─────────────┐
            │ EKS Cluster │
            └─────────────┘
```

## Características

### Frontend
- Interfaz web moderna con Bootstrap y FullCalendar
- Dashboard con métricas de tareas
- Programador visual de tareas con calendario
- Visualización de logs en tiempo real
- Responsive design

### kubectl-runner
- API REST para ejecutar comandos kubectl
- Programador de tareas con expresiones cron
- Integración con AWS EKS
- Logs persistentes
- Health checks

## Estructura del Proyecto

```
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── kubectl-runner/
│   ├── Dockerfile
│   ├── src/
│   │   └── app.py
│   └── scripts/
│       ├── setup-kubeconfig.sh
│       └── health-check.sh
├── manifests/
│   ├── base/
│   │   ├── task-scheduler-deployment.yaml
│   │   ├── task-scheduler-service.yaml
│   │   ├── kubectl-runner-rbac.yaml
│   │   ├── namespace.yaml
│   │   └── kustomization.yaml
│   └── overlays/production/
│       ├── kustomization.yaml
│       ├── task-scheduler-patch.yaml
│       └── ingress.yaml
└── .github/workflows/build.yaml
```

## Despliegue

### Prerequisitos
- Cluster EKS configurado y accesible
- GitHub OIDC provider configurado en AWS
- Repositorios ECR creados
- Secret `MANIFESTS_REPO_TOKEN` en GitHub con permisos para actualizar el repositorio de manifiestos

### 1. Configurar ECR Repositories

```bash
# Crear repositorios en ECR
aws ecr create-repository --repository-name task-scheduler-frontend --region us-east-1
aws ecr create-repository --repository-name kubectl-runner --region us-east-1
```

### 2. Configurar IAM Role para kubectl-runner

```bash
# Crear rol IAM con permisos para EKS
aws iam create-role --role-name kubectl-runner-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::226633502530:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/YOUR_OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/YOUR_OIDC_ID:sub": "system:serviceaccount:namespace-scheduler:kubectl-runner"
        }
      }
    }
  ]
}'

# Adjuntar políticas necesarias
aws iam attach-role-policy --role-name kubectl-runner-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
aws iam attach-role-policy --role-name kubectl-runner-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
```

### 2.1 Configurar IAM Role para GitHub Actions

```bash
# Crear rol IAM para GitHub Actions con OIDC
aws iam create-role --role-name github-actions-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::226633502530:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}'

# Adjuntar política para ECR
aws iam attach-role-policy --role-name github-actions-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

### 3. Build y Push de Imágenes

El workflow de GitHub Actions (`.github/workflows/build.yaml`) se encarga automáticamente de:

**Triggers:**
- Push a ramas `main` o `develop`
- Pull requests a `main`
- Cambios en directorios: `frontend/`, `kubectl-runner/`, `Dockerfile.*`, o el workflow mismo

**Proceso automatizado:**
1. **Build Frontend**: Construye y pushea la imagen del frontend a ECR
2. **Build kubectl-runner**: Construye y pushea la imagen del kubectl-runner a ECR
3. **Update Manifests**: Actualiza automáticamente los manifiestos en el repositorio `backstage-k8s-manifests-auth`

**Autenticación:**
- Usa OIDC (OpenID Connect) con AWS para autenticación sin credenciales estáticas
- Role ARN: `arn:aws:iam::226633502530:role/github-actions-role`

**Tagging Strategy:**
- Tags por rama: `main`, `develop`
- Tags por SHA: `{branch}-{sha}`
- Tag `latest` solo para rama principal

**Requisitos:**
- Repositorios ECR creados: `task-scheduler-frontend` y `kubectl-runner`
- Secret `MANIFESTS_REPO_TOKEN` configurado en GitHub para actualizar manifiestos

### 4. Desplegar con ArgoCD

```bash
# Aplicar la aplicación de ArgoCD
kubectl apply -f argocd/namespace-scheduler-app.yaml
```

## Uso

### Acceso a la Aplicación
- Frontend: `https://namespace-scheduler.pocarqnube.com`
- API: `https://namespace-scheduler.pocarqnube.com/api`

### Crear una Tarea Programada

1. Accede al frontend
2. Ve a la sección "Programador"
3. Completa el formulario:
   - **Nombre**: Descripción de la tarea
   - **Tipo**: Tipo de operación (command, scale, restart, etc.)
   - **Comando/Operación**: Comando kubectl o tipo de operación específica
   - **Programación**: Expresión cron (ej: `0 */6 * * *` para cada 6 horas)
   - **Namespace**: Namespace de Kubernetes
   - **Centro de Costo**: Centro de costo para facturación (opcional, default: 'default')

### API Endpoints

```bash
# Listar tareas
curl https://namespace-scheduler.pocarqnube.com/api/tasks

# Crear tarea
curl -X POST https://namespace-scheduler.pocarqnube.com/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Check pods",
    "operation_type": "command",
    "command": "get pods -n default",
    "schedule": "0 */6 * * *",
    "namespace": "default",
    "cost_center": "development"
  }'

# Ejecutar comando directamente
curl -X POST https://namespace-scheduler.pocarqnube.com/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "get nodes",
    "namespace": "default"
  }'

# Ver logs
curl https://namespace-scheduler.pocarqnube.com/api/logs
```

### Detalles de Tareas Mejorados

El frontend ahora muestra información detallada de cada tarea incluyendo:

- **Tipo de Operación**: Distingue entre comandos kubectl y operaciones específicas (scale, restart, etc.)
- **Centro de Costo**: Para seguimiento de facturación y organización
- **Estadísticas de Ejecución**: Contador de ejecuciones totales, exitosas y fallidas
- **Visualización Inteligente**: Muestra el comando completo o una descripción amigable según el tipo de operación

**Campos de Tarea:**
- `operation_type`: Tipo de operación (default: 'command')
- `cost_center`: Centro de costo (default: 'default')
- `run_count`: Número total de ejecuciones
- `success_count`: Número de ejecuciones exitosas
- `error_count`: Número de ejecuciones fallidas

## Monitoreo

### Health Checks
- Frontend: `GET /`
- kubectl-runner: `GET /health`

### Logs
Los logs se almacenan en:
- Frontend: Logs de Nginx en `/var/log/nginx/`
- kubectl-runner: Logs de aplicación en `/app/logs/app.log`

## Configuración Avanzada

### Variables de Entorno

**kubectl-runner:**
- `EKS_CLUSTER_NAME`: Nombre del cluster EKS (default: "eks-cloud")
- `AWS_REGION`: Región de AWS (default: "us-east-1")

### Personalización del Frontend

Puedes modificar:
- `frontend/src/styles.css`: Estilos personalizados
- `frontend/src/app.js`: Lógica de la aplicación
- `frontend/nginx.conf`: Configuración de Nginx

### Escalado

Para escalar los componentes, modifica:
- `manifests/overlays/production/kustomization.yaml`: Número de réplicas
- `manifests/overlays/production/task-scheduler-patch.yaml`: Recursos de CPU/memoria

## Troubleshooting

### Problemas Comunes

1. **kubectl-runner no puede conectar al cluster**
   - Verificar que el ServiceAccount tenga los permisos correctos
   - Comprobar que el IAM role esté configurado correctamente

2. **Frontend no puede comunicarse con la API**
   - Verificar la configuración del Ingress
   - Comprobar que ambos servicios estén en el mismo namespace

3. **Tareas no se ejecutan**
   - Verificar los logs del kubectl-runner
   - Comprobar la sintaxis de las expresiones cron

### Comandos de Diagnóstico

```bash
# Verificar pods
kubectl get pods -n namespace-scheduler

# Ver logs del frontend
kubectl logs -n namespace-scheduler deployment/task-scheduler-frontend

# Ver logs del kubectl-runner
kubectl logs -n namespace-scheduler deployment/kubectl-runner

# Verificar servicios
kubectl get svc -n namespace-scheduler

# Verificar ingress
kubectl get ingress -n namespace-scheduler
```