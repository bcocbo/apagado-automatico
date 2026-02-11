# Deployment Configuration

## Image Management Strategy

The Namespace Scheduler uses Kustomize for managing different deployment environments. The image configuration follows this pattern:

### Base Configuration
The base deployment manifests (`manifests/base/task-scheduler-deployment.yaml`) use generic image names:
- `task-scheduler-frontend:latest`
- `task-scheduler-backend:latest`

### Production Overlay
The production overlay (`manifests/overlays/production/kustomization.yaml`) replaces these generic names with actual ECR registry URLs:
- `226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-frontend:latest`
- `226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-backend:latest`

This approach allows:
1. **Environment flexibility**: Different overlays can use different registries
2. **Clean base manifests**: Base configurations remain registry-agnostic
3. **Automated updates**: CI/CD can update image tags in overlays without touching base files

## Kustomize Image Replacement

The production overlay uses Kustomize's `images` field to replace image references:

```yaml
images:
- name: task-scheduler-frontend
  newName: 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-frontend
  newTag: latest
- name: task-scheduler-backend
  newName: 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-backend
  newTag: latest
```

## CI/CD Integration

GitHub Actions actualiza automáticamente los image tags en el mismo repositorio:

### Proceso Automatizado
1. **Build**: GitHub Actions construye y pushea imágenes a ECR con tag basado en commit SHA
2. **Update**: El workflow actualiza `manifests/overlays/production/kustomization.yaml` con el nuevo tag
3. **Commit**: Los cambios se commitean automáticamente con mensaje `[skip ci]`
4. **Deploy**: ArgoCD detecta los cambios y sincroniza el cluster

### Ventajas de esta Estrategia
- **Simplicidad**: Todo en un solo repositorio
- **Trazabilidad**: Cada commit tiene su imagen correspondiente
- **Atomicidad**: Código e infraestructura se actualizan juntos
- **GitOps**: ArgoCD maneja el despliegue basado en Git

## Deployment Process

1. **Build**: GitHub Actions builds and pushes images to ECR with commit SHA as tag
2. **Update**: CI/CD updates image tags in `manifests/overlays/production/kustomization.yaml` using `sed`
3. **Commit**: Changes are automatically committed with `[skip ci]` to avoid infinite loops
4. **Deploy**: ArgoCD syncs the production overlay to the cluster
5. **Result**: Kustomize applies the overlay, replacing generic names with ECR URLs and specific tags

## Configuration Files

- **Base deployment**: `manifests/base/task-scheduler-deployment.yaml`
- **Base kustomization**: `manifests/base/kustomization.yaml`
- **Production overlay**: `manifests/overlays/production/kustomization.yaml`
- **ArgoCD app**: `argocd/namespace-scheduler-app.yaml`