# Namespace Scheduler - Diseño Técnico

## Arquitectura del Sistema

### Componentes Principales

1. **Frontend (SPA)**
   - Tecnología: HTML5, CSS3, JavaScript vanilla, Bootstrap 5
   - Funcionalidades: Interfaz de usuario, calendario, gestión de tareas
   - Puerto: 80 (nginx)

2. **Backend (API REST)**
   - Tecnología: Python Flask, boto3, croniter
   - Funcionalidades: API REST, scheduler, kubectl wrapper
   - Puerto: 8080

3. **Base de Datos**
   - DynamoDB: Logs de actividades y permisos de centros de costo
   - Almacenamiento local: Configuración de tareas (JSON)

4. **Infraestructura**
   - Kubernetes: EKS cluster
   - ArgoCD: Despliegue continuo
   - ECR: Registro de imágenes
   - GitHub Actions: CI/CD

## Diseño de la API

### Endpoints Principales

```
GET /health - Health check
GET /api/namespaces - Listar namespaces
GET /api/namespaces/status - Estado de namespaces
POST /api/namespaces/{namespace}/activate - Activar namespace
POST /api/namespaces/{namespace}/deactivate - Desactivar namespace

GET /api/tasks - Listar tareas
POST /api/tasks - Crear tarea
GET /api/tasks/{id} - Obtener tarea
DELETE /api/tasks/{id} - Eliminar tarea
POST /api/tasks/{id}/run - Ejecutar tarea

GET /api/logs - Obtener logs
GET /api/activities - Obtener actividades por centro de costo

GET /api/cost-centers - Listar centros de costo
GET /api/cost-centers/{cost_center}/validate - Validar permisos de centro de costo
POST /api/cost-centers/{cost_center}/permissions - Configurar permisos de centro de costo
```

### Modelo de Datos

#### Tarea (Task)
```json
{
  "id": "string",
  "title": "string",
  "operation_type": "activate|deactivate|command",
  "command": "string",
  "schedule": "string (cron)",
  "namespace": "string",
  "cost_center": "string",
  "status": "pending|running|completed|failed",
  "created_at": "datetime",
  "next_run": "datetime",
  "run_count": "number",
  "success_count": "number",
  "error_count": "number"
}
```

#### Actividad DynamoDB
```json
{
  "namespace_name": "string (hash key)",
  "timestamp_start": "number (range key)",
  "operation_type": "string",
  "cost_center": "string",
  "cluster_name": "string",
  "requested_by": "string",
  "approved_by": "string",
  "user_id": "string",
  "status": "active|completed",
  "timestamp_end": "number",
  "duration_minutes": "number"
}
```

**Índices Secundarios Globales:**
- `cost-center-timestamp-index`: Para consultas por centro de costo
- `operation-type-timestamp-index`: Para consultas por tipo de operación
- `cluster-timestamp-index`: Para consultas por cluster específico
- `requested-by-timestamp-index`: Para auditoría por usuario solicitante

## Lógica de Negocio

### Validación de Horarios
- **Horario laboral**: Lunes a Viernes, 7:00 AM - 8:00 PM
- **Horario no laboral**: Resto del tiempo
- **Límite**: Máximo 5 namespaces activos en horario no laboral

### Gestión de Namespaces
1. **Activación**: Escalar recursos a réplicas originales (default: 1)
2. **Desactivación**: Escalar todos los recursos a 0 réplicas
3. **Validación**: Verificar permisos de centro de costo
4. **Logging**: Registrar todas las operaciones en DynamoDB

### Scheduler de Tareas
- Verificación cada minuto de tareas pendientes
- Ejecución en threads separados
- Cálculo automático de próxima ejecución
- Manejo de errores y reintentos

## Configuración de Despliegue

### Estructura de Manifiestos
```
manifests/
├── base/
│   ├── namespace.yaml
│   ├── kubectl-runner-rbac.yaml
│   ├── task-scheduler-deployment.yaml
│   ├── task-scheduler-service.yaml
│   └── kustomization.yaml
└── overlays/
    └── production/
        ├── ingress.yaml
        ├── task-scheduler-patch.yaml
        ├── backstage-patch.yaml
        └── kustomization.yaml
```

### RBAC Requerido
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-runner
rules:
- apiGroups: [""]
  resources: ["namespaces", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "patch", "update"]
- apiGroups: ["apps"]
  resources: ["deployments/scale", "statefulsets/scale"]
  verbs: ["get", "patch", "update"]
```

### Variables de Entorno
```yaml
env:
- name: EKS_CLUSTER_NAME
  value: "production-cluster"
- name: AWS_REGION
  value: "us-east-1"
- name: DYNAMODB_TABLE_NAME
  value: "task-scheduler-logs-production"
- name: PERMISSIONS_TABLE_NAME
  value: "cost-center-permissions-production"
```

## Pipeline de CI/CD

### GitHub Actions Workflow
```yaml
name: Build and Deploy
on:
  push:
    branches: [main]
jobs:
  build-frontend:
    - Build frontend image
    - Push to ECR
  build-backend:
    - Build backend image
    - Push to ECR
  update-manifests:
    - Update image tags in manifests
    - Commit changes
```

### ArgoCD Application
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: namespace-scheduler
spec:
  source:
    repoURL: https://github.com/user/namespace-scheduler
    path: manifests/overlays/production
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: task-scheduler
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Seguridad

### Autenticación y Autorización
- Service Account con RBAC limitado
- Validación de centros de costo
- Logs de auditoría en DynamoDB

### Configuración de Red
- Ingress con TLS
- Network policies para limitar tráfico
- Service mesh (opcional)

## Monitoreo

### Métricas
- Número de namespaces activos
- Tareas ejecutadas/fallidas
- Tiempo de respuesta de API
- Uso de recursos

### Logs
- Logs estructurados en JSON
- Rotación automática
- Integración con CloudWatch (opcional)

### Health Checks
- Endpoint `/health` para readiness/liveness
- Verificación de conectividad a DynamoDB
- Verificación de acceso a cluster

## Propiedades de Correctitud

### 1. Límite de Namespaces en Horario No Laboral
**Propiedad**: Durante horarios no laborales, nunca debe haber más de 5 namespaces activos simultáneamente.

**Validación**: Para cualquier timestamp en horario no laboral, contar namespaces activos ≤ 5

### 2. Validación de Centros de Costo
**Propiedad**: Toda operación debe estar asociada a un centro de costo válido y autorizado.

**Validación**: Para toda operación, existe un centro de costo con `is_authorized = true`

### 3. Consistencia de Estados
**Propiedad**: El estado reportado de un namespace debe coincidir con su estado real en Kubernetes.

**Validación**: Para todo namespace, `reported_status == kubectl_status`

### 4. Programación de Tareas
**Propiedad**: Las tareas programadas deben ejecutarse dentro de una ventana de tiempo aceptable.

**Validación**: Para toda tarea programada, `|execution_time - scheduled_time| ≤ 2 minutos`

### 5. Logging de Actividades
**Propiedad**: Toda operación de activación/desactivación debe generar un log en DynamoDB.

**Validación**: Para toda operación, existe un registro correspondiente en DynamoDB

## Framework de Testing

- **Unit Tests**: pytest para lógica de negocio
- **Integration Tests**: Pruebas de API con cluster de prueba
- **Property-Based Tests**: Hypothesis para validar propiedades de correctitud
- **E2E Tests**: Selenium para interfaz web

## Consideraciones de Performance

- **Caching**: Cache de lista de namespaces (TTL: 30s)
- **Rate Limiting**: Límite de operaciones por minuto
- **Async Operations**: Operaciones de kubectl en background
- **Connection Pooling**: Pool de conexiones a DynamoDB

## Plan de Rollback

1. **Rollback de ArgoCD**: Revertir a versión anterior
2. **Rollback de Imágenes**: Usar tags anteriores
3. **Rollback de Base de Datos**: Backup/restore de DynamoDB
4. **Rollback Manual**: Procedimientos de emergencia