# Kyverno Namespace Scheduler Policies

## Descripción

Este documento describe las políticas de Kyverno implementadas para el Namespace Scheduler. Estas políticas automatizan el enforcement de las reglas de programación de namespaces, bloqueando pods en namespaces inactivos y escalando automáticamente recursos según el estado del namespace.

## Políticas Implementadas

### 1. Block Pods in Inactive Namespaces

**Archivo**: `manifests/base/kyverno-namespace-scheduler-policies.yaml`  
**Política**: `namespace-scheduler-block-inactive-pods`

#### Propósito
Bloquea la creación de nuevos pods en namespaces marcados como inactivos por el namespace scheduler.

#### Funcionamiento
- **Trigger**: Creación de pods (`Pod` resources)
- **Condición**: Namespace tiene label `scheduler.pocarqnube.com/status=inactive`
- **Acción**: Rechaza la creación del pod con mensaje explicativo
- **Exclusiones**: Namespaces protegidos del sistema

#### Configuración
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: namespace-scheduler-block-inactive-pods
spec:
  validationFailureAction: enforce
  background: false
  rules:
  - name: block-pods-in-inactive-namespaces
    match:
      any:
      - resources:
          kinds:
          - Pod
    exclude:
      any:
      - resources:
          namespaces:
          - kube-system
          - kube-public
          - kube-node-lease
          - task-scheduler
          - kyverno
          - argocd
```

#### Mensaje de Error
```
Pod creation blocked: Namespace 'dev-namespace' is currently inactive.
The namespace scheduler has marked this namespace as inactive during non-business hours.
Pods will be allowed again during business hours (8 AM - 6 PM UTC-5) or when scheduled tasks activate the namespace.
```

### 2. Auto-scale Resources in Inactive Namespaces

**Política**: `namespace-scheduler-auto-scale-inactive`

#### Propósito
Escala automáticamente deployments y statefulsets a 0 réplicas cuando un namespace se marca como inactivo.

#### Funcionamiento
- **Trigger**: Modificación de deployments o statefulsets
- **Condición**: Namespace tiene label `scheduler.pocarqnube.com/status=inactive` Y el recurso tiene réplicas > 0
- **Acción**: Escala a 0 réplicas y guarda el valor original en annotations
- **Background**: `true` (se aplica a recursos existentes)

#### Annotations Agregadas
```yaml
metadata:
  annotations:
    scheduler.pocarqnube.com/original-replicas: "3"
    scheduler.pocarqnube.com/scaled-by: "namespace-scheduler"
    scheduler.pocarqnube.com/scaled-at: "2024-02-19T15:30:00Z"
```

#### Reglas Implementadas
1. **force-zero-replicas-deployments**: Escala deployments a 0
2. **force-zero-replicas-statefulsets**: Escala statefulsets a 0

### 3. Restore Resources in Active Namespaces

**Política**: `namespace-scheduler-restore-active`

#### Propósito
Restaura automáticamente deployments y statefulsets a su número original de réplicas cuando un namespace se reactiva.

#### Funcionamiento
- **Trigger**: Modificación de deployments o statefulsets
- **Condición**: 
  - Namespace tiene label `scheduler.pocarqnube.com/status=active`
  - El recurso tiene annotation `scheduler.pocarqnube.com/original-replicas` > 0
  - El recurso actualmente tiene 0 réplicas
- **Acción**: Restaura réplicas al valor original y agrega annotations de restauración

#### Annotations Agregadas
```yaml
metadata:
  annotations:
    scheduler.pocarqnube.com/restored-by: "namespace-scheduler"
    scheduler.pocarqnube.com/restored-at: "2024-02-19T08:00:00Z"
```

#### Reglas Implementadas
1. **restore-replicas-deployments**: Restaura deployments
2. **restore-replicas-statefulsets**: Restaura statefulsets

## Integración con Namespace Scheduler

### Labels de Namespace
El backend del Namespace Scheduler gestiona los siguientes labels en los namespaces:

```yaml
metadata:
  labels:
    scheduler.pocarqnube.com/status: "active|inactive"
    scheduler.pocarqnube.com/cost-center: "CC001"
    scheduler.pocarqnube.com/managed-by: "namespace-scheduler"
```

### Flujo de Activación/Desactivación

#### Desactivación (Horario No Laboral)
1. Backend marca namespace: `scheduler.pocarqnube.com/status=inactive`
2. Kyverno detecta el cambio de label
3. **Auto-scale policy** escala recursos a 0 réplicas
4. **Block pods policy** previene creación de nuevos pods
5. Namespace queda completamente inactivo

#### Activación (Horario Laboral o Tarea Programada)
1. Backend marca namespace: `scheduler.pocarqnube.com/status=active`
2. Kyverno detecta el cambio de label
3. **Restore policy** restaura recursos a réplicas originales
4. **Block pods policy** ya no aplica
5. Namespace vuelve a estar operativo

## Namespaces Excluidos

Las políticas NO se aplican a los siguientes namespaces protegidos:

```yaml
exclude:
  any:
  - resources:
      namespaces:
      - kube-system
      - kube-public
      - kube-node-lease
      - task-scheduler
      - kyverno
      - argocd
```

Estos namespaces están definidos en `kubectl-runner/src/config/protected-namespaces.json` y nunca se desactivan.

## Ventajas de Usar Kyverno

### 1. Enforcement Automático
- Las políticas se aplican automáticamente sin intervención del backend
- Garantiza que las reglas se cumplan incluso si hay fallos en el scheduler

### 2. Declarativo y GitOps
- Políticas definidas como código en manifiestos YAML
- Versionado y auditabilidad completa
- Despliegue automático con ArgoCD

### 3. Performance
- Kyverno opera a nivel de API server
- No requiere polling o monitoreo constante
- Respuesta inmediata a cambios de estado

### 4. Seguridad
- Previene bypass de las reglas de programación
- Enforcement a nivel de cluster, no dependiente del backend

## Monitoreo y Troubleshooting

### Verificar Estado de Políticas

```bash
# Listar políticas de Kyverno
kubectl get clusterpolicy

# Ver detalles de una política específica
kubectl describe clusterpolicy namespace-scheduler-block-inactive-pods

# Ver eventos de Kyverno
kubectl get events --field-selector reason=PolicyViolation
```

### Verificar Labels de Namespace

```bash
# Ver labels de un namespace específico
kubectl get namespace dev-namespace -o yaml

# Listar namespaces con sus labels de scheduler
kubectl get namespaces -l scheduler.pocarqnube.com/managed-by=namespace-scheduler
```

### Verificar Annotations de Recursos

```bash
# Ver annotations de un deployment
kubectl get deployment app-deployment -n dev-namespace -o yaml

# Buscar recursos escalados por el scheduler
kubectl get deployments --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.metadata.annotations.scheduler\.pocarqnube\.com/scaled-by}{"\n"}{end}' | grep namespace-scheduler
```

### Logs de Kyverno

```bash
# Ver logs del controlador de Kyverno
kubectl logs -n kyverno deployment/kyverno-admission-controller

# Ver logs del background controller
kubectl logs -n kyverno deployment/kyverno-background-controller
```

## Casos de Uso y Ejemplos

### Ejemplo 1: Namespace Inactivo

```bash
# Marcar namespace como inactivo
kubectl label namespace dev-namespace scheduler.pocarqnube.com/status=inactive

# Intentar crear un pod (debe fallar)
kubectl run test-pod --image=nginx -n dev-namespace
# Error: Pod creation blocked: Namespace 'dev-namespace' is currently inactive...

# Ver que los deployments se escalaron a 0
kubectl get deployments -n dev-namespace
```

### Ejemplo 2: Reactivar Namespace

```bash
# Marcar namespace como activo
kubectl label namespace dev-namespace scheduler.pocarqnube.com/status=active

# Los deployments se restauran automáticamente
kubectl get deployments -n dev-namespace

# Ahora se pueden crear pods
kubectl run test-pod --image=nginx -n dev-namespace
```

### Ejemplo 3: Verificar Proceso de Escalado

```bash
# Antes de desactivar
kubectl get deployment app-deployment -n dev-namespace -o jsonpath='{.spec.replicas}'
# Output: 3

# Desactivar namespace
kubectl label namespace dev-namespace scheduler.pocarqnube.com/status=inactive

# Verificar escalado automático
kubectl get deployment app-deployment -n dev-namespace -o jsonpath='{.spec.replicas}'
# Output: 0

# Verificar annotation con valor original
kubectl get deployment app-deployment -n dev-namespace -o jsonpath='{.metadata.annotations.scheduler\.pocarqnube\.com/original-replicas}'
# Output: 3
```

## Consideraciones de Implementación

### 1. Orden de Aplicación
Las políticas se aplican en el siguiente orden:
1. Block pods (inmediato al marcar como inactive)
2. Auto-scale (background, puede tomar unos segundos)
3. Restore (inmediato al marcar como active)

### 2. Recursos Soportados
Actualmente las políticas soportan:
- **Pods**: Bloqueo de creación
- **Deployments**: Escalado automático
- **StatefulSets**: Escalado automático

### 3. Limitaciones
- **DaemonSets**: No se escalan (por diseño)
- **Jobs**: No se bloquean (pueden ser necesarios para limpieza)
- **Pods standalone**: Se bloquean pero no se escalan automáticamente

### 4. Compatibilidad
- Requiere Kyverno 1.8+ para funciones de lookup
- Compatible con Kubernetes 1.20+
- Funciona con ArgoCD y GitOps workflows

## Referencias

- [Kyverno Documentation](https://kyverno.io/docs/)
- [Kyverno Policy Examples](https://kyverno.io/policies/)
- [Kubernetes Labels and Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
- [Protected Namespaces Configuration](protected-namespaces.md)
- [Kubernetes RBAC Configuration](kubernetes-rbac-configuration.md)