# Namespaces Protegidos - Namespace Scheduler

## Descripción

Este documento describe la estrategia de protección de namespaces del sistema para evitar que sean desescalados accidentalmente por el Namespace Scheduler.

## Estrategia de Protección

### 1. Protección Principal: RBAC de Kubernetes

La protección de namespaces se implementa mediante una combinación de ClusterRoles y RoleBindings:

- **ClusterRole `kubectl-runner-readonly`**: Permisos de solo lectura a nivel de cluster
- **ClusterRole `kubectl-runner-scale`**: Permisos de escritura (escalar recursos)
- **ClusterRoleBinding `kubectl-runner-scale`**: Otorga permisos de escritura a TODOS los namespaces
- **RoleBindings específicos**: Sobrescriben el ClusterRoleBinding en namespaces protegidos, limitándolos a solo lectura

**Cómo funciona**: Los RoleBindings específicos en namespaces protegidos tienen precedencia sobre el ClusterRoleBinding, por lo que aunque el service account `kubectl-runner` tiene permisos de escritura a nivel de cluster, los namespaces protegidos solo permiten lectura.

### 2. Protección Secundaria: Validación en Backend (Recomendada)

Aunque el RBAC proporciona protección a nivel de Kubernetes, se recomienda implementar validación adicional en el backend para:

- Proporcionar mensajes de error más claros a los usuarios
- Permitir configuración dinámica de namespaces protegidos
- Facilitar auditoría y logging de intentos de modificación
- Agregar lógica de negocio adicional (ej: horarios, permisos por usuario)

### 2. Namespaces Protegidos

Los siguientes namespaces están protegidos mediante RoleBindings de solo lectura y validación en el backend, y NO pueden ser desescalados:

- `karpenter` - Autoscaling de nodos (crítico para el cluster)
- `kyverno` - Policy engine (crítico para enforcement de políticas)
- `argocd` - Sistema de despliegue continuo (crítico para CI/CD)
- `kube-system` - Componentes core de Kubernetes
- `istio-system` - Service mesh (crítico para networking)
- `monitoring` - Sistema de observabilidad (crítico para monitoreo)
- `task-scheduler` - El propio namespace del scheduler

**Nota**: La lista actualizada refleja la implementación actual en el método `is_protected_namespace()` del backend.

Cada uno de estos namespaces tiene un RoleBinding que vincula el service account `kubectl-runner` al ClusterRole `kubectl-runner-readonly`, lo que sobrescribe los permisos de escritura del ClusterRoleBinding global.

### 3. Configuración RBAC Actual

#### ClusterRoles Implementados

```yaml
# Solo lectura
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-runner-readonly
rules:
- apiGroups: [""]
  resources: ["namespaces", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]

---
# Permisos de escritura (scale)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubectl-runner-scale
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch", "patch", "update"]
- apiGroups: ["apps"]
  resources: ["deployments/scale", "statefulsets/scale", "replicasets/scale"]
  verbs: ["get", "patch", "update"]
```

#### Bindings Implementados

```yaml
# ClusterRoleBinding: permisos de escritura en todos los namespaces
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

---
# RoleBinding: solo lectura en namespace protegido (ejemplo: kube-system)
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kubectl-runner-readonly
  namespace: kube-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-runner-readonly
subjects:
- kind: ServiceAccount
  name: kubectl-runner
  namespace: task-scheduler
```

### 4. Implementación en el Backend (Implementada)

El backend ahora incluye el método `is_protected_namespace()` que implementa la validación de namespaces protegidos:

```python
def is_protected_namespace(self, namespace_name):
    """Check if a namespace is protected and cannot be activated/deactivated"""
    protected_namespaces = [
        'karpenter',     # Critical for cluster autoscaling
        'kyverno',       # Critical for policy enforcement
        'argocd',        # Critical for CI/CD operations
        'kube-system',   # Core Kubernetes system
        'istio-system',  # Service mesh - critical for networking
        'monitoring',    # Critical for observability
        'task-scheduler' # This application itself
    ]
    return namespace_name in protected_namespaces
```

Este método debe ser utilizado en todos los endpoints que modifican el estado de los namespaces para prevenir operaciones no autorizadas.

### 5. Validación en Endpoints

Todos los endpoints que modifican namespaces deben validar:

```python
@app.route('/api/namespaces/<namespace>/activate', methods=['POST'])
def activate_namespace(namespace):
    # Validar que el namespace no esté protegido usando el método implementado
    if self.is_protected_namespace(namespace):
        return jsonify({
            'error': f'El namespace {namespace} está protegido y no puede ser activado/desactivado',
            'protected': True
        }), 403
    
    # Continuar con la lógica de activación...
```

### 6. Filtrado en Listado de Namespaces

El endpoint que lista namespaces debe marcar los protegidos:

```python
@app.route('/api/namespaces', methods=['GET'])
def list_namespaces():
    namespaces = get_all_namespaces()
    
    result = []
    for ns in namespaces:
        result.append({
            'name': ns.metadata.name,
            'status': get_namespace_status(ns),
            'protected': self.is_protected_namespace(ns.metadata.name),
            'can_scale': not self.is_protected_namespace(ns.metadata.name)
        })
    
    return jsonify(result)
```

### 7. Interfaz de Usuario

El frontend debe:

1. Mostrar un indicador visual para namespaces protegidos
2. Deshabilitar botones de activación/desactivación para namespaces protegidos
3. Mostrar un tooltip explicando por qué está protegido

```javascript
function renderNamespaceRow(namespace) {
    const isProtected = namespace.protected;
    const disabledClass = isProtected ? 'disabled' : '';
    const protectedBadge = isProtected ? 
        '<span class="badge bg-warning">🔒 Protegido</span>' : '';
    
    return `
        <tr>
            <td>${namespace.name} ${protectedBadge}</td>
            <td>${namespace.status}</td>
            <td>
                <button 
                    class="btn btn-primary ${disabledClass}" 
                    ${isProtected ? 'disabled title="Este namespace está protegido"' : ''}
                    onclick="activateNamespace('${namespace.name}')">
                    Activar
                </button>
            </td>
        </tr>
    `;
}
```

## Configuración Dinámica (Opcional)

Para mayor flexibilidad, los namespaces protegidos pueden configurarse mediante:

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: namespace-scheduler-config
  namespace: task-scheduler
data:
  protected-namespaces: |
    karpenter
    kyverno
    argocd
    kube-system
    istio-system
    monitoring
    task-scheduler
```

### Variable de Entorno

```yaml
env:
- name: PROTECTED_NAMESPACES
  value: "karpenter,kyverno,argocd,kube-system,istio-system,monitoring,task-scheduler"
```

## Permisos para Otros Namespaces

### Comportamiento Actual

Para namespaces que NO están protegidos, el service account `kubectl-runner` hereda los permisos del ClusterRoleBinding `kubectl-runner-scale`, que permite:

- Listar y ver recursos (get, list, watch)
- Escalar deployments y statefulsets (patch, update)
- Modificar el subrecurso scale (get, patch, update)

**No se requieren RoleBindings adicionales** para namespaces no protegidos, ya que el ClusterRoleBinding proporciona acceso global.

### Agregar Nuevos Namespaces Protegidos

Para proteger un nuevo namespace, simplemente crear un RoleBinding:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kubectl-runner-readonly
  namespace: <nuevo-namespace-protegido>
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kubectl-runner-readonly
subjects:
- kind: ServiceAccount
  name: kubectl-runner
  namespace: task-scheduler
```

Luego aplicar:

```bash
kubectl apply -f rolebinding.yaml
```

## Testing

### Prueba de Protección RBAC

```bash
# Intentar escalar un deployment en un namespace protegido
# Debe FALLAR con error de permisos
kubectl scale deployment/coredns --replicas=0 -n kube-system \
  --as=system:serviceaccount:task-scheduler:kubectl-runner

# Resultado esperado: Error: deployments.apps "coredns" is forbidden

# Verificar permisos con auth can-i
kubectl auth can-i scale deployment -n kube-system \
  --as=system:serviceaccount:task-scheduler:kubectl-runner
# Resultado esperado: no
```

### Prueba de Acceso Normal

```bash
# Escalar un deployment en un namespace no protegido
# Debe FUNCIONAR correctamente
kubectl scale deployment/my-app --replicas=0 -n dev-namespace \
  --as=system:serviceaccount:task-scheduler:kubectl-runner

# Resultado esperado: deployment.apps/my-app scaled

# Verificar permisos con auth can-i
kubectl auth can-i scale deployment -n dev-namespace \
  --as=system:serviceaccount:task-scheduler:kubectl-runner
# Resultado esperado: yes
```

### Verificar RoleBindings en Namespaces Protegidos

```bash
# Listar todos los RoleBindings de solo lectura
for ns in kube-system argocd istio-system kyverno task-scheduler kube-public kube-node-lease karpenter keda vision; do
  echo "=== Namespace: $ns ==="
  kubectl get rolebinding kubectl-runner-readonly -n $ns -o yaml
done

# Verificar que el RoleBinding apunta al ClusterRole correcto
kubectl get rolebinding kubectl-runner-readonly -n kube-system -o jsonpath='{.roleRef.name}'
# Resultado esperado: kubectl-runner-readonly
```

## Monitoreo y Auditoría

Todas las operaciones deben registrarse en DynamoDB incluyendo:

- Intentos de modificar namespaces protegidos (rechazados)
- Usuario que intentó la operación
- Timestamp del intento
- Razón del rechazo

```python
def log_protected_namespace_attempt(namespace, user, operation):
    """
    Registra intentos de modificar namespaces protegidos
    """
    dynamodb_table.put_item(Item={
        'namespace_name': namespace,
        'timestamp_start': int(time.time()),
        'operation_type': f'{operation}_rejected',
        'requested_by': user,
        'status': 'rejected',
        'reason': 'protected_namespace',
        'cluster_name': os.getenv('EKS_CLUSTER_NAME')
    })
```

## Recomendaciones

1. **Protección en Capas**: La configuración actual usa RBAC como primera línea de defensa, complementar con validación en backend
2. **Logging Completo**: Registrar todos los intentos de modificación (exitosos y fallidos)
3. **UI Clara**: Indicar claramente qué namespaces están protegidos en la interfaz
4. **Documentación**: Mantener actualizada la lista de namespaces protegidos en este documento
5. **Alertas**: Configurar alertas para intentos de modificar namespaces protegidos
6. **Auditoría Regular**: Revisar periódicamente los RoleBindings y ClusterRoleBindings
7. **Testing Continuo**: Validar permisos después de cada cambio en RBAC

## Arquitectura de Protección

```
Service Account: kubectl-runner
    │
    ├─── ClusterRoleBinding: kubectl-runner-scale
    │    └─── Aplica a: TODOS los namespaces
    │         └─── Permisos: get, list, watch, patch, update (deployments, statefulsets, scale)
    │
    └─── RoleBindings: kubectl-runner-readonly (en namespaces protegidos)
         ├─── kube-system
         ├─── argocd
         ├─── istio-system
         ├─── kyverno
         ├─── task-scheduler
         ├─── kube-public
         ├─── kube-node-lease
         ├─── karpenter
         ├─── keda
         └─── vision
         └─── Sobrescribe ClusterRoleBinding
              └─── Permisos: SOLO get, list, watch (sin patch, update)

Resultado:
┌─────────────────────────────────────────────────────────────┐
│ Namespaces Protegidos: SOLO LECTURA                         │
│ (RoleBinding tiene precedencia sobre ClusterRoleBinding)    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Otros Namespaces: LECTURA + ESCRITURA                       │
│ (Heredan permisos del ClusterRoleBinding)                   │
└─────────────────────────────────────────────────────────────┘
```

## Referencias

- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [RoleBinding vs ClusterRoleBinding](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#rolebinding-and-clusterrolebinding)
- [Namespace Security Best Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
