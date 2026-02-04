# ArgoCD Configuration - Namespace Startup Scheduler

Este directorio contiene la configuración de ArgoCD para el despliegue GitOps del sistema de programación de auto-encendido de namespaces.

## Estructura

```
argocd/
├── apps/
│   ├── backend-app.yaml      # Aplicación ArgoCD para backend
│   └── frontend-app.yaml     # Aplicación ArgoCD para frontend
├── bootstrap.yaml            # App of Apps para bootstrap
└── README.md                 # Esta documentación
```

## Aplicaciones ArgoCD

### 1. Backend Application
- **Nombre**: `namespace-startup-scheduler-backend`
- **Path**: `manifests/backend/`
- **Componentes**: API FastAPI, ServiceMonitor para Prometheus
- **Namespace**: `encendido-eks`

### 2. Frontend Application
- **Nombre**: `namespace-startup-scheduler-frontend`
- **Path**: `manifests/frontend/`
- **Componentes**: React SPA, Nginx, Ingress
- **Namespace**: `encendido-eks`

### 3. Bootstrap Application (App of Apps)
- **Nombre**: `namespace-startup-scheduler-apps`
- **Path**: `argocd/apps/`
- **Propósito**: Gestiona las aplicaciones backend y frontend

## Configuración

### Sync Policy
- **Automated**: `true` - Sincronización automática
- **Self Heal**: `true` - Auto-reparación de drift
- **Prune**: `true` - Eliminación de recursos huérfanos

### Retry Policy
- **Limit**: 5 intentos
- **Backoff**: Exponencial (5s → 10s → 20s → 40s → 3m)

## Despliegue

### 1. Instalar ArgoCD (si no está instalado)
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2. Aplicar Bootstrap Application
```bash
kubectl apply -f argocd/bootstrap.yaml
```

### 3. Verificar Aplicaciones
```bash
# Ver aplicaciones en ArgoCD
kubectl get applications -n argocd

# Ver estado de sync
argocd app list
```

## GitOps Workflow

1. **Desarrollo**: Cambios en código fuente
2. **CI/CD**: GitHub Actions construye imágenes y actualiza manifiestos
3. **Git Commit**: Manifiestos actualizados se commitean al repo
4. **ArgoCD Sync**: ArgoCD detecta cambios y sincroniza automáticamente
5. **Deployment**: Aplicaciones se despliegan en EKS

## Rollback

### Automático
- ArgoCD detecta fallos de health check
- Revierte automáticamente a la versión anterior
- GitHub Actions puede revertir manifiestos en caso de fallo

### Manual
```bash
# Rollback via ArgoCD CLI
argocd app rollback namespace-startup-scheduler-backend

# Rollback via Git
git revert <commit-hash>
git push
```

## Monitoreo

### ArgoCD UI
- Estado de sincronización
- Health checks de aplicaciones
- Historial de despliegues
- Logs de sync

### Prometheus Metrics
- ArgoCD expone métricas de aplicaciones
- Integración con ServiceMonitor existente

## Troubleshooting

### Aplicación Out of Sync
```bash
# Forzar sync
argocd app sync namespace-startup-scheduler-backend

# Ver diferencias
argocd app diff namespace-startup-scheduler-backend
```

### Health Check Failed
```bash
# Ver logs de la aplicación
kubectl logs -n encendido-eks deployment/namespace-startup-scheduler-backend

# Ver eventos
kubectl get events -n encendido-eks
```

### Manifest Errors
```bash
# Validar manifiestos localmente
kubectl apply --dry-run=client -f manifests/backend/
kubectl apply --dry-run=client -f manifests/frontend/
```

## Configuración Personalizada

### Cambiar Repository URL
Actualizar `repoURL` en:
- `argocd/apps/backend-app.yaml`
- `argocd/apps/frontend-app.yaml`
- `argocd/bootstrap.yaml`

### Cambiar Target Revision
Actualizar `targetRevision` para usar branches específicos:
```yaml
source:
  targetRevision: main  # o develop, staging, etc.
```

### Configurar Notifications
ArgoCD puede enviar notificaciones a Slack, email, etc. Ver documentación oficial de ArgoCD para configuración de notifications.