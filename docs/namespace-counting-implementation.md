# Implementación de Conteo de Namespaces - Namespace Scheduler

## Descripción

Este documento describe la implementación mejorada del sistema de conteo de namespaces activos en el Namespace Scheduler, que reemplaza el contador manual con un sistema dinámico basado en consultas en tiempo real a Kubernetes.

## Problema Anterior

La implementación anterior mantenía un contador manual (`active_namespaces_count`) que se actualizaba manualmente cuando se activaban o desactivaban namespaces. Este enfoque tenía varios problemas:

- **Inconsistencias**: El contador podía desincronizarse con el estado real del cluster
- **Falta de visibilidad**: No proporcionaba información detallada sobre qué recursos estaban activos
- **Errores de sincronización**: Fallos en operaciones podían dejar el contador en estado incorrecto
- **Limitaciones de auditoría**: No permitía análisis detallado del uso de recursos

## Nueva Implementación

### Arquitectura

La nueva implementación utiliza un enfoque dinámico que consulta directamente el estado del cluster de Kubernetes para determinar qué namespaces están activos.

#### Componentes Principales

1. **`get_active_namespaces_count()`**: Método principal que calcula el conteo dinámicamente
2. **`is_system_namespace()`**: Filtro para excluir namespaces del sistema
3. **`is_namespace_active()`**: Lógica para determinar si un namespace está activo
4. **`get_namespace_details()`**: Información detallada de recursos por namespace

### Criterios de Namespace Activo

Un namespace se considera **activo** si cumple alguno de estos criterios:

1. **Pods en ejecución**: Tiene al menos un pod en estado `Running`
2. **Deployments escalados**: Tiene deployments con `replicas > 0`
3. **StatefulSets escalados**: Tiene statefulsets con `replicas > 0`

### Namespaces Excluidos del Conteo

Los siguientes namespaces del sistema se excluyen automáticamente del conteo:

```python
system_namespaces = [
    'kube-system', 
    'kube-public', 
    'kube-node-lease', 
    'default',
    'kube-apiserver',
    'kube-controller-manager',
    'kube-scheduler',
    'kube-proxy',
    'coredns',
    'calico-system',
    'tigera-operator',
    'amazon-cloudwatch',
    'aws-node',
    'cert-manager',
    'ingress-nginx',
    'monitoring',
    'logging',
    'argocd',
    'task-scheduler'  # Nuestro propio namespace
]
```

## Implementación Técnica

### Método Principal: `get_active_namespaces_count()`

```python
def get_active_namespaces_count(self):
    """Get the actual count of active namespaces by querying Kubernetes"""
    try:
        # Obtener todos los namespaces
        result = self.execute_kubectl_command('get namespaces -o json')
        if not result['success']:
            logger.error(f"Failed to get namespaces: {result['stderr']}")
            return 0
        
        namespaces_data = json.loads(result['stdout'])
        active_count = 0
        
        for item in namespaces_data['items']:
            namespace_name = item['metadata']['name']
            
            # Saltar namespaces del sistema
            if self.is_system_namespace(namespace_name):
                continue
            
            # Verificar si el namespace tiene recursos activos
            if self.is_namespace_active(namespace_name):
                active_count += 1
        
        return active_count
        
    except Exception as e:
        logger.error(f"Error getting active namespaces count: {e}")
        return 0
```

### Detección de Actividad: `is_namespace_active()`

```python
def is_namespace_active(self, namespace_name):
    """Check if a namespace is active (has running pods or scaled deployments)"""
    try:
        # Método 1: Verificar pods en ejecución
        pods_result = self.execute_kubectl_command(
            f'get pods -n {namespace_name} --field-selector=status.phase=Running -o json'
        )
        
        if pods_result['success']:
            pods_data = json.loads(pods_result['stdout'])
            if len(pods_data.get('items', [])) > 0:
                return True
        
        # Método 2: Verificar deployments con replicas > 0
        deployments_result = self.execute_kubectl_command(
            f'get deployments -n {namespace_name} -o json'
        )
        
        if deployments_result['success']:
            deployments_data = json.loads(deployments_result['stdout'])
            for deployment in deployments_data.get('items', []):
                replicas = deployment.get('spec', {}).get('replicas', 0)
                if replicas > 0:
                    return True
        
        # Método 3: Verificar statefulsets con replicas > 0
        statefulsets_result = self.execute_kubectl_command(
            f'get statefulsets -n {namespace_name} -o json'
        )
        
        if statefulsets_result['success']:
            statefulsets_data = json.loads(statefulsets_result['stdout'])
            for statefulset in statefulsets_data.get('items', []):
                replicas = statefulset.get('spec', {}).get('replicas', 0)
                if replicas > 0:
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking if namespace {namespace_name} is active: {e}")
        return False
```

### Información Detallada: `get_namespace_details()`

```python
def get_namespace_details(self, namespace_name):
    """Get detailed information about a namespace's active resources"""
    try:
        details = {
            'name': namespace_name,
            'is_active': False,
            'is_system': self.is_system_namespace(namespace_name),
            'active_pods': 0,
            'deployments': [],
            'statefulsets': [],
            'daemonsets': []
        }
        
        # Obtener información de pods activos
        # Obtener información de deployments
        # Obtener información de statefulsets
        # Obtener información de daemonsets
        
        # Determinar si el namespace está activo
        details['is_active'] = self.is_namespace_active(namespace_name)
        
        return details
        
    except Exception as e:
        logger.error(f"Error getting namespace details for {namespace_name}: {e}")
        return {
            'name': namespace_name,
            'is_active': False,
            'is_system': self.is_system_namespace(namespace_name),
            'active_pods': 0,
            'deployments': [],
            'statefulsets': [],
            'daemonsets': [],
            'error': str(e)
        }
```

## Beneficios de la Nueva Implementación

### 1. Precisión
- **Estado real**: Siempre refleja el estado actual del cluster
- **Sin desincronización**: No hay riesgo de contadores manuales incorrectos
- **Información completa**: Proporciona detalles sobre qué recursos están activos

### 2. Robustez
- **Manejo de errores**: Graceful degradation en caso de fallos de API
- **Logging detallado**: Registra errores para debugging
- **Fallback seguro**: Retorna 0 en caso de error para evitar comportamientos inesperados

### 3. Observabilidad
- **Información detallada**: Permite análisis granular del uso de recursos
- **Auditoría mejorada**: Facilita el tracking de qué namespaces están consumiendo recursos
- **Debugging**: Información detallada para troubleshooting

### 4. Flexibilidad
- **Criterios configurables**: Fácil modificación de qué constituye un namespace "activo"
- **Filtros extensibles**: Fácil adición de nuevos namespaces del sistema
- **Información rica**: Estructura de datos extensible para futuras mejoras

## Impacto en Performance

### Consideraciones
- **Latencia**: Cada consulta requiere llamadas a la API de Kubernetes
- **Frecuencia**: El método se llama bajo demanda, no en background
- **Caching**: Futuras mejoras pueden incluir caching temporal

### Optimizaciones Implementadas
- **Consultas específicas**: Uso de field selectors para filtrar pods por estado
- **Manejo de errores**: Evita reintentos innecesarios en caso de fallos
- **Logging eficiente**: Solo registra errores, no operaciones exitosas

### Recomendaciones de Uso
- **Llamadas bajo demanda**: No llamar en loops frecuentes
- **Caching temporal**: Considerar implementar cache de 30-60 segundos para uso intensivo
- **Monitoreo**: Supervisar latencia de las consultas en producción

## Integración con Endpoints Existentes

### Endpoint de Estadísticas
```python
@app.route('/api/stats', methods=['GET'])
def get_stats():
    # Usar el nuevo método dinámico
    active_count = task_scheduler.get_active_namespaces_count()
    
    return jsonify({
        'active_namespaces': active_count,
        'total_namespaces': get_total_namespaces_count(),
        'system_namespaces': len(SYSTEM_NAMESPACES),
        'user_namespaces': get_total_namespaces_count() - len(SYSTEM_NAMESPACES)
    })
```

### Endpoint de Detalles de Namespaces
```python
@app.route('/api/namespaces/<namespace>/details', methods=['GET'])
def get_namespace_details_endpoint(namespace):
    details = task_scheduler.get_namespace_details(namespace)
    return jsonify(details)
```

### Endpoint de Lista de Namespaces
```python
@app.route('/api/namespaces', methods=['GET'])
def list_namespaces():
    # Obtener todos los namespaces con información detallada
    result = []
    namespaces = get_all_namespaces()
    
    for ns in namespaces:
        details = task_scheduler.get_namespace_details(ns.metadata.name)
        result.append({
            'name': ns.metadata.name,
            'is_active': details['is_active'],
            'is_system': details['is_system'],
            'active_pods': details['active_pods'],
            'deployments_count': len(details['deployments']),
            'statefulsets_count': len(details['statefulsets']),
            'can_scale': not details['is_system']
        })
    
    return jsonify(result)
```

## Testing

### Unit Tests
```python
def test_get_active_namespaces_count():
    # Mock kubectl responses
    # Test various scenarios:
    # - Namespaces with running pods
    # - Namespaces with scaled deployments
    # - System namespaces (should be excluded)
    # - Empty namespaces (should not count)
    # - Error scenarios
    pass

def test_is_namespace_active():
    # Test individual namespace activity detection
    pass

def test_is_system_namespace():
    # Test system namespace filtering
    pass
```

### Integration Tests
```python
def test_namespace_counting_integration():
    # Test with real cluster
    # Verify counts match expected state
    # Test after scaling operations
    pass
```

## Monitoreo y Alertas

### Métricas Recomendadas
- **Latencia de consultas**: Tiempo de respuesta de `get_active_namespaces_count()`
- **Errores de API**: Fallos en consultas a Kubernetes
- **Conteo de namespaces**: Trending del número de namespaces activos

### Logs de Auditoría
```python
# Registrar cambios en conteo de namespaces activos
def log_namespace_count_change(old_count, new_count):
    logger.info(f"Active namespaces count changed: {old_count} -> {new_count}")
    
    # Opcional: registrar en DynamoDB para auditoría
    dynamodb_table.put_item(Item={
        'event_type': 'namespace_count_change',
        'timestamp': int(time.time()),
        'old_count': old_count,
        'new_count': new_count,
        'cluster_name': os.getenv('EKS_CLUSTER_NAME')
    })
```

## Futuras Mejoras

### 1. Caching Inteligente
```python
class NamespaceCountCache:
    def __init__(self, ttl_seconds=60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_cached_count(self):
        now = time.time()
        if 'count' in self.cache and (now - self.cache['timestamp']) < self.ttl:
            return self.cache['count']
        return None
    
    def set_cached_count(self, count):
        self.cache = {
            'count': count,
            'timestamp': time.time()
        }
```

### 2. Métricas de Prometheus
```python
from prometheus_client import Gauge, Counter

active_namespaces_gauge = Gauge('active_namespaces_total', 'Number of active namespaces')
namespace_query_duration = Gauge('namespace_query_duration_seconds', 'Time spent querying namespace info')
namespace_query_errors = Counter('namespace_query_errors_total', 'Number of namespace query errors')
```

### 3. Webhooks de Kubernetes
- Implementar webhooks para recibir notificaciones de cambios en tiempo real
- Reducir la necesidad de polling activo
- Mejorar la responsividad del sistema

### 4. Análisis Predictivo
- Tracking de patrones de uso de namespaces
- Predicción de picos de actividad
- Optimización proactiva de recursos

## Referencias

- [Kubernetes API Reference](https://kubernetes.io/docs/reference/kubernetes-api/)
- [kubectl Command Reference](https://kubernetes.io/docs/reference/kubectl/)
- [Field Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/)
- [Label Selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)

## Changelog

### v2.0.0 - Implementación Dinámica
- ✅ Reemplazado contador manual con consultas dinámicas
- ✅ Agregado método `get_active_namespaces_count()`
- ✅ Implementado filtrado de namespaces del sistema
- ✅ Agregada detección multi-criterio de actividad
- ✅ Implementado método `get_namespace_details()` para información detallada
- ✅ Mejorado manejo de errores y logging
- ✅ Documentación completa de la nueva implementación

### v1.0.0 - Implementación Original
- ❌ Contador manual `active_namespaces_count`
- ❌ Actualización manual en operaciones
- ❌ Riesgo de desincronización
- ❌ Información limitada sobre recursos activos