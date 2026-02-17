# Configuración RBAC de Kubernetes - Namespace Scheduler

## Descripción

Este documento describe la configuración de RBAC (Role-Based Access Control) para el servicio `kubectl-runner` en el cluster de Kubernetes, que es responsable de ejecutar operaciones de gestión de namespaces y recursos.

## Configuración Actual

### Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubectl-runner
  namespace: task-scheduler
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::226633502530:role/kubectl-runner-role
```

### ClusterRoles

La configuración implementa dos ClusterRoles separados siguiendo el principio de menor privilegio:

#### 1. kubectl-runner-readonly (Permisos de Solo Lectura)

Este role se usa en namespaces protegidos para prevenir modificaciones.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-runner-readonly
rules:
# Permisos para listar y ver namespaces
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list", "watch"]

# Permisos de solo lectura para pods
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

# Permisos de solo lectura para pods con field selectors (para status checks)
- apiGroups: [""]
  resources: ["pods/status"]
  verbs: ["get", "list"]

# Permisos de solo lectura para deployments, statefulsets, etc.
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch"]

# Permisos de solo lectura para métricas (opcional)
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
```

#### 2. kubectl-runner-scale (Permisos de Escritura)

Este role se usa en namespaces NO protegidos mediante ClusterRoleBinding.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-runner-scale
rules:
# Permisos para listar y ver namespaces
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list", "watch"]

# Permisos para ver pods y su estado
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]

# Permisos para ver estado de pods (necesario para field selectors)
- apiGroups: [""]
  resources: ["pods/status"]
  verbs: ["get", "list"]

# Permisos para escalar deployments, statefulsets y daemonsets
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]

# Permisos para escalar usando el subrecurso scale (método recomendado)
- apiGroups: ["apps"]
  resources: ["deployments/scale", "statefulsets/scale", "replicasets/scale"]
  verbs: ["get", "patch", "update"]

# Permisos para recursos de extensiones (compatibilidad con versiones antiguas)
- apiGroups: ["extensions"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]

- apiGroups: ["extensions"]
  resources: ["deployments/scale", "replicasets/scale"]
  verbs: ["get", "patch", "update"]

# Permisos de solo lectura para métricas (opcional)
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
```

### Bindings

#### ClusterRoleBinding para Permisos de Solo Lectura

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubectl-runner-readonly
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-runner-readonly
subjects:
- kind: ServiceAccount
  name: kubectl-runner
  namespace: task-scheduler
```

#### ClusterRoleBinding para Permisos de Escalado

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubectl-runner-scale
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-runner-scale
subjects:
- kind: ServiceAccount
  name: kubectl-runner
  namespace: task-scheduler
```

#### RoleBindings para Namespaces Protegidos

Los siguientes namespaces tienen RoleBindings de solo lectura para protegerlos de modificaciones:

- `kube-system`
- `kube-public`
- `kube-node-lease`
- `argocd`
- `istio-system`
- `kyverno`
- `task-scheduler`
- `karpenter` (NUEVO)
- `keda` (NUEVO)
- `vision` (NUEVO)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kubectl-runner-readonly
  namespace: <protected-namespace>
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-runner-readonly
subjects:
- kind: ServiceAccount
  name: kubectl-runner
  namespace: task-scheduler
```

## ✅ Mejoras de Seguridad Implementadas

### Principio de Menor Privilegio

1. **Separación de Permisos**: Dos ClusterRoles distintos (readonly y scale) en lugar de permisos amplios
2. **Protección de Namespaces Críticos**: RoleBindings de solo lectura en namespaces del sistema
3. **Permisos Específicos**: Solo los verbos necesarios para cada recurso
4. **Sin Permisos de Administrador**: No hay uso de wildcards (`*`) en recursos o verbos

### Estrategia de Protección

- **Namespaces Protegidos**: Los namespaces críticos del sistema tienen RoleBindings explícitos de solo lectura que sobrescriben el ClusterRoleBinding de scale
- **Namespaces de Usuario**: Todos los demás namespaces heredan los permisos de scale del ClusterRoleBinding
- **Doble Capa de Seguridad**: RBAC + validación en el backend (ver `docs/protected-namespaces.md`)

## Permisos Implementados

### Permisos de Solo Lectura (kubectl-runner-readonly)

Estos permisos se aplican a nivel de cluster y específicamente en namespaces protegidos:

- **Namespaces**: `get`, `list`, `watch`
- **Pods**: `get`, `list`, `watch`
- **Pods/Status**: `get`, `list` (necesario para field selectors y status checks)
- **Deployments/StatefulSets/DaemonSets/ReplicaSets**: `get`, `list`, `watch`
- **Métricas**: `get`, `list` (opcional)

### Permisos de Escritura (kubectl-runner-scale)

Estos permisos se aplican solo en namespaces NO protegidos:

- **Namespaces**: `get`, `list`, `watch`
- **Pods**: `get`, `list`, `watch`
- **Pods/Status**: `get`, `list` (necesario para field selectors y status checks)
- **Deployments/StatefulSets/DaemonSets/ReplicaSets**: `get`, `list`, `watch`, `patch`, `update`
- **Subrecursos de Scale**: `get`, `patch`, `update` en `deployments/scale`, `statefulsets/scale`, `replicasets/scale`
- **Extensiones (compatibilidad)**: Permisos similares para el apiGroup `extensions`
- **Métricas**: `get`, `list` (opcional)

### Permisos Adicionales Potenciales (Si se Requieren)

Si el sistema necesita funcionalidades adicionales, considerar agregar:

```yaml
# Jobs y CronJobs para tareas programadas
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Eventos para logging y debugging
- apiGroups: [""]
  resources: ["events"]
  verbs: ["get", "list", "watch", "create"]

# ResourceQuotas para gestión de límites
- apiGroups: [""]
  resources: ["resourcequotas", "limitranges"]
  verbs: ["get", "list", "watch"]
```

## Funcionalidades Requeridas

### 1. Gestión de Namespaces

- **Activar/Desactivar namespaces**: Requiere permisos para escalar deployments y statefulsets a 0 réplicas
- **Crear namespaces temporales**: Requiere permisos de creación de namespaces
- **Aplicar ResourceQuotas**: Requiere permisos para gestionar quotas y límites

### 2. Escalado de Recursos

- **Scale deployments**: `deployments/scale` con verbs `get`, `update`, `patch`
- **Scale statefulsets**: `statefulsets/scale` con verbs `get`, `update`, `patch`
- **Gestión de réplicas**: Acceso a `replicasets` para verificar estado

### 3. Tareas Programadas

- **Crear/gestionar Jobs**: Permisos en `batch/jobs`
- **Crear/gestionar CronJobs**: Permisos en `batch/cronjobs`
- **Monitorear ejecución**: Acceso a pods y eventos

### 4. Monitoreo y Logging

- **Métricas de recursos**: Acceso de lectura a `metrics.k8s.io`
- **Eventos del cluster**: Lectura y creación de eventos
- **Estado de pods**: Lectura de información de pods

## Comandos de Validación

### Verificar Permisos Actuales

```bash
# Ver service account
kubectl get sa kubectl-runner -n task-scheduler -o yaml

# Ver ClusterRoles
kubectl get clusterrole kubectl-runner-readonly -o yaml
kubectl get clusterrole kubectl-runner-scale -o yaml

# Ver ClusterRoleBindings
kubectl get clusterrolebinding kubectl-runner-readonly -o yaml
kubectl get clusterrolebinding kubectl-runner-scale -o yaml

# Ver RoleBindings en namespaces protegidos
kubectl get rolebinding kubectl-runner-readonly -n kube-system -o yaml
kubectl get rolebinding kubectl-runner-readonly -n argocd -o yaml

# Probar permisos específicos
kubectl auth can-i --as=system:serviceaccount:task-scheduler:kubectl-runner get namespaces
kubectl auth can-i --as=system:serviceaccount:task-scheduler:kubectl-runner scale deployment -n dev-namespace
kubectl auth can-i --as=system:serviceaccount:task-scheduler:kubectl-runner scale deployment -n kube-system
```

### Probar Operaciones Críticas

```bash
# Desde un pod con el service account
kubectl exec -it deployment/task-scheduler -n task-scheduler -- /bin/bash

# Dentro del pod, probar comandos kubectl

# Debe funcionar: listar namespaces
kubectl get namespaces

# Debe funcionar: listar deployments
kubectl get deployments --all-namespaces

# Debe funcionar: escalar en namespace no protegido
kubectl scale deployment/test-app --replicas=0 -n dev-namespace

# Debe FALLAR: escalar en namespace protegido
kubectl scale deployment/coredns --replicas=0 -n kube-system
```

### Validar Protección de Namespaces

```bash
# Verificar que los namespaces protegidos tienen RoleBindings de solo lectura
for ns in kube-system kube-public kube-node-lease argocd istio-system kyverno task-scheduler karpenter keda vision; do
  echo "Checking $ns..."
  kubectl get rolebinding kubectl-runner-readonly -n $ns
done

# Probar que NO se puede escalar en namespaces protegidos
kubectl auth can-i scale deployment --as=system:serviceaccount:task-scheduler:kubectl-runner -n kube-system
# Resultado esperado: no

# Probar que SÍ se puede escalar en namespaces no protegidos
kubectl auth can-i scale deployment --as=system:serviceaccount:task-scheduler:kubectl-runner -n dev-namespace
# Resultado esperado: yes
```

## Plan de Implementación Completado

### ✅ Fase 1: Análisis (Completada)
1. ✅ Auditar operaciones actuales del kubectl-runner
2. ✅ Identificar recursos y verbos realmente utilizados
3. ✅ Documentar casos de uso específicos

### ✅ Fase 2: Implementación (Completada)
1. ✅ Crear ClusterRoles con permisos mínimos (readonly y scale)
2. ✅ Implementar protección de namespaces críticos con RoleBindings
3. ✅ Configurar ClusterRoleBindings apropiados
4. ⏳ Probar en entorno de desarrollo
5. ⏳ Validar todas las funcionalidades
6. ⏳ Aplicar en producción

### ⏳ Fase 3: Validación (Pendiente)
1. Monitorear logs de errores de permisos
2. Ajustar permisos según necesidades reales
3. Documentar configuración final

## Arquitectura de Permisos

```
kubectl-runner ServiceAccount
    │
    ├─── ClusterRoleBinding (kubectl-runner-readonly)
    │    └─── ClusterRole: kubectl-runner-readonly
    │         └─── Permisos: get, list, watch (namespaces, pods, deployments, etc.)
    │
    ├─── ClusterRoleBinding (kubectl-runner-scale)
    │    └─── ClusterRole: kubectl-runner-scale
    │         └─── Permisos: get, list, watch, patch, update (deployments, statefulsets, scale)
    │
    └─── RoleBindings en Namespaces Protegidos
         ├─── kube-system → kubectl-runner-readonly (SOLO LECTURA)
         ├─── kube-public → kubectl-runner-readonly (SOLO LECTURA)
         ├─── kube-node-lease → kubectl-runner-readonly (SOLO LECTURA)
         ├─── argocd → kubectl-runner-readonly (SOLO LECTURA)
         ├─── istio-system → kubectl-runner-readonly (SOLO LECTURA)
         ├─── kyverno → kubectl-runner-readonly (SOLO LECTURA)
         ├─── task-scheduler → kubectl-runner-readonly (SOLO LECTURA)
         ├─── karpenter → kubectl-runner-readonly (SOLO LECTURA)
         ├─── keda → kubectl-runner-readonly (SOLO LECTURA)
         └─── vision → kubectl-runner-readonly (SOLO LECTURA)

Resultado:
- Namespaces protegidos: SOLO LECTURA (RoleBinding sobrescribe ClusterRoleBinding)
- Otros namespaces: LECTURA + ESCRITURA (heredan del ClusterRoleBinding de scale)
```

## Troubleshooting

### Error: "Forbidden" al ejecutar kubectl

**Causa**: Permisos insuficientes en RBAC

**Solución**:
```bash
# Verificar permisos específicos
kubectl auth can-i <verb> <resource> --as=system:serviceaccount:task-scheduler:kubectl-runner

# Ver logs del pod para detalles
kubectl logs deployment/task-scheduler -n task-scheduler
```

### Error: "ServiceAccount not found"

**Causa**: Service account no existe o está en namespace incorrecto

**Solución**:
```bash
# Verificar service account
kubectl get sa -n task-scheduler

# Recrear si es necesario
kubectl apply -f manifests/base/kubectl-runner-rbac.yaml
```

### Error: "ClusterRoleBinding not found"

**Causa**: Binding entre service account y role no existe

**Solución**:
```bash
# Verificar binding
kubectl get clusterrolebinding kubectl-runner

# Verificar que apunta al service account correcto
kubectl get clusterrolebinding kubectl-runner -o yaml
```

## Referencias

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [EKS IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)