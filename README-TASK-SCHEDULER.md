# Task Scheduler para EKS

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
          "oidc.eks.us-east-1.amazonaws.com/id/YOUR_OIDC_ID:sub": "system:serviceaccount:task-scheduler:kubectl-runner"
        }
      }
    }
  ]
}'

# Adjuntar políticas necesarias
aws iam attach-role-policy --role-name kubectl-runner-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
aws iam attach-role-policy --role-name kubectl-runner-role --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
```

### 3. Build y Push de Imágenes

El workflow de GitHub Actions se encarga automáticamente de:
- Construir ambas imágenes Docker
- Pushear a ECR
- Actualizar los manifiestos de Kubernetes

### 4. Desplegar con ArgoCD

```bash
# Aplicar la aplicación de ArgoCD
kubectl apply -f argocd/backstage-app.yaml
```

## Uso

### Acceso a la Aplicación
- Frontend: `https://task-scheduler.pocarqnube.com`
- API: `https://task-scheduler.pocarqnube.com/api`

### Crear una Tarea Programada

1. Accede al frontend
2. Ve a la sección "Programador"
3. Completa el formulario:
   - **Nombre**: Descripción de la tarea
   - **Comando**: Comando kubectl (ej: `get pods -n default`)
   - **Programación**: Expresión cron (ej: `0 */6 * * *` para cada 6 horas)
   - **Namespace**: Namespace de Kubernetes

### API Endpoints

```bash
# Listar tareas
curl https://task-scheduler.pocarqnube.com/api/tasks

# Crear tarea
curl -X POST https://task-scheduler.pocarqnube.com/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Check pods",
    "command": "get pods -n default",
    "schedule": "0 */6 * * *",
    "namespace": "default"
  }'

# Ejecutar comando directamente
curl -X POST https://task-scheduler.pocarqnube.com/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "get nodes",
    "namespace": "default"
  }'

# Ver logs
curl https://task-scheduler.pocarqnube.com/api/logs
```

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
- `EKS_CLUSTER_NAME`: Nombre del cluster EKS (default: "poc-kafka")
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
kubectl get pods -n task-scheduler

# Ver logs del frontend
kubectl logs -n task-scheduler deployment/task-scheduler-frontend

# Ver logs del kubectl-runner
kubectl logs -n task-scheduler deployment/kubectl-runner

# Verificar servicios
kubectl get svc -n task-scheduler

# Verificar ingress
kubectl get ingress -n task-scheduler
```