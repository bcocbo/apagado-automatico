# Implementación de Rollback Automático - Namespace Scheduler

## Descripción

Este documento describe la implementación del sistema de rollback automático para operaciones de escalado de recursos en el Namespace Scheduler. El sistema garantiza que las operaciones de escalado sean atómicas y reversibles en caso de fallos parciales.

## Problema que Resuelve

Cuando se escalan múltiples recursos en un namespace (deployments, statefulsets), existe el riesgo de que algunas operaciones fallen mientras otras tienen éxito. Esto puede dejar el namespace en un estado inconsistente:

- **Escalado parcial**: Algunos recursos escalados, otros no
- **Estado inconsistente**: Difícil determinar qué recursos fueron modificados
- **Recuperación manual**: Requiere intervención manual para restaurar el estado original
- **Pérdida de información**: No hay registro de qué se intentó hacer

## Arquitectura de Rollback

### Componentes Principales

1. **`scale_namespace_resources()`**: Método principal con soporte de rollback integrado
2. **`_rollback_scaling()`**: Método privado que ejecuta el rollback
3. **Tracking de operaciones**: Registro de cada operación exitosa para posible rollback
4. **Detección de fallos**: Identificación automática de errores que requieren rollback

### Flujo de Operación

```
1. Inicio de escalado
   ↓
2. Para cada recurso:
   - Escalar recurso
   - Si éxito: agregar a lista de escalados
   - Si fallo: iniciar rollback
   ↓
3. Si ocurre fallo:
   - Detener procesamiento de nuevos recursos
   - Ejecutar rollback de recursos exitosos
   - Retornar resultado con información de rollback
   ↓
4. Fin de operación
```

## Implementación Técnica

### Método Principal: `scale_namespace_resources()`

```python
def scale_namespace_resources(self, namespace, target_replicas, enable_rollback=True):
    """Scale all scalable resources in a namespace with rollback support
    
    Args:
        namespace: The namespace to scale
        target_replicas: Target replica count (0 to scale down, None to restore, or specific number)
        enable_rollback: If True, rollback changes on partial failure (default: True)
    
    Returns:
        dict with success status, scaled resources info, rollback info, and any errors
    """
```

#### Parámetros

- **namespace** (str): Nombre del namespace a escalar
- **target_replicas** (int|None): 
  - `0`: Escalar a cero (desactivar)
  - `None`: Restaurar réplicas originales
  - `N`: Escalar a N réplicas específicas
- **enable_rollback** (bool): Habilitar rollback automático (default: `True`)

#### Valor de Retorno

```python
{
    'success': bool,                    # True si todas las operaciones exitosas
    'scaled_resources': [               # Lista de recursos escalados exitosamente
        {
            'type': 'deployment',
            'name': 'my-app',
            'from_replicas': 3,
            'to_replicas': 0,
            'status': 'success'
        }
    ],
    'failed_resources': [               # Lista de recursos que fallaron
        {
            'type': 'statefulset',
            'name': 'my-db',
            'status': 'failed',
            'error': 'timeout'
        }
    ],
    'total_scaled': 2,                  # Número de recursos escalados
    'total_failed': 1,                  # Número de recursos fallidos
    'rollback_performed': True,         # Si se ejecutó rollback
    'rollback_results': [               # Resultados del rollback (si aplica)
        {
            'type': 'deployment',
            'name': 'my-app',
            'restored_replicas': 3,
            'status': 'success'
        }
    ],
    'rollback_success_count': 2,        # Rollbacks exitosos
    'rollback_failed_count': 0,         # Rollbacks fallidos
    'errors': ['error message']         # Lista de errores (si aplica)
}
```

### Método de Rollback: `_rollback_scaling()`

```python
def _rollback_scaling(self, namespace, scaled_resources):
    """Rollback scaling operations by reverting to original replica counts
    
    Args:
        namespace: The namespace where scaling occurred
        scaled_resources: List of successfully scaled resources to rollback
    
    Returns:
        list: Results of rollback operations
    """
```

#### Características del Rollback

1. **Restauración a estado original**: Usa el valor `from_replicas` guardado
2. **Procesamiento completo**: Intenta rollback de todos los recursos, incluso si algunos fallan
3. **Logging detallado**: Registra cada operación de rollback
4. **Manejo de errores**: Captura y registra errores sin detener el proceso
5. **Skip de recursos no modificados**: No intenta rollback de recursos que fueron "skipped"

## Escenarios de Activación del Rollback

### 1. Fallo en Escalado de Recurso

```python
# Si un recurso falla al escalar
if not scale_result['success']:
    logger.error(f"Failed to scale {resource_type}/{resource_name}")
    failed_resources.append({...})
    
    # Activar rollback si hay recursos exitosos
    if enable_rollback and len(scaled_resources) > 0:
        logger.warning(f"Failure detected, initiating rollback")
        rollback_results = self._rollback_scaling(namespace, scaled_resources)
        rollback_performed = True
        break  # Detener procesamiento
```

### 2. Error de Parsing JSON

```python
except json.JSONDecodeError as e:
    error_msg = f"Failed to parse JSON for {resource_type}: {e}"
    logger.error(error_msg)
    errors.append(error_msg)
    
    # Rollback en error de parsing
    if enable_rollback and len(scaled_resources) > 0:
        logger.warning(f"JSON parse error detected, initiating rollback")
        rollback_results = self._rollback_scaling(namespace, scaled_resources)
        rollback_performed = True
    break
```

### 3. Excepción Inesperada

```python
except Exception as e:
    error_msg = f"Error processing {resource_type}: {e}"
    logger.error(error_msg)
    errors.append(error_msg)
    
    # Rollback en error inesperado
    if enable_rollback and len(scaled_resources) > 0:
        logger.warning(f"Unexpected error detected, initiating rollback")
        rollback_results = self._rollback_scaling(namespace, scaled_resources)
        rollback_performed = True
    break
```

## Garantías y Comportamiento

### Garantías Proporcionadas

1. **Atomicidad**: O todos los recursos se escalan, o ninguno queda modificado
2. **Trazabilidad**: Registro completo de qué se intentó y qué se revirtió
3. **Información completa**: Resultado detallado de cada operación y rollback
4. **Logging exhaustivo**: Todos los eventos registrados para auditoría

### Comportamiento en Casos Especiales

#### Rollback Deshabilitado

```python
# Llamar con enable_rollback=False
result = scale_namespace_resources(namespace, 0, enable_rollback=False)

# Resultado: operaciones exitosas permanecen, no hay rollback
{
    'success': False,
    'scaled_resources': [...],  # Recursos que se escalaron
    'failed_resources': [...],  # Recursos que fallaron
    'rollback_performed': False
}
```

#### Sin Recursos Exitosos

```python
# Si el primer recurso falla, no hay nada que revertir
{
    'success': False,
    'scaled_resources': [],
    'failed_resources': [{'type': 'deployment', 'name': 'app', 'status': 'failed'}],
    'rollback_performed': False  # No hay nada que revertir
}
```

#### Fallo en Rollback

```python
# Si el rollback falla parcialmente
{
    'success': False,
    'rollback_performed': True,
    'rollback_results': [
        {'type': 'deployment', 'name': 'app1', 'status': 'success'},
        {'type': 'deployment', 'name': 'app2', 'status': 'failed', 'error': 'timeout'}
    ],
    'rollback_success_count': 1,
    'rollback_failed_count': 1
}
```

## Integración con Endpoints

### Endpoint de Desactivación

```python
@app.route('/api/namespaces/<namespace>/deactivate', methods=['POST'])
def deactivate_namespace(namespace):
    # Validar permisos...
    
    # Escalar a cero con rollback habilitado
    scale_result = task_scheduler.scale_namespace_resources(
        namespace=namespace,
        target_replicas=0,
        enable_rollback=True  # Rollback automático en caso de fallo
    )
    
    if scale_result['success']:
        return jsonify({
            'success': True,
            'message': f'Namespace {namespace} deactivated',
            'scaled_resources': scale_result['scaled_resources']
        })
    else:
        # Incluir información de rollback si ocurrió
        response = {
            'success': False,
            'message': f'Failed to deactivate namespace {namespace}',
            'error': scale_result.get('errors', [])
        }
        
        if scale_result.get('rollback_performed'):
            response['rollback_info'] = {
                'performed': True,
                'success_count': scale_result.get('rollback_success_count', 0),
                'failed_count': scale_result.get('rollback_failed_count', 0)
            }
        
        return jsonify(response), 500
```

### Endpoint de Activación

```python
@app.route('/api/namespaces/<namespace>/activate', methods=['POST'])
def activate_namespace(namespace):
    # Validar permisos...
    
    # Restaurar réplicas originales con rollback habilitado
    scale_result = task_scheduler.scale_namespace_resources(
        namespace=namespace,
        target_replicas=None,  # None = restaurar originales
        enable_rollback=True
    )
    
    # Similar manejo de respuesta...
```

## Logging y Auditoría

### Logs de Rollback

```
[WARNING] Failure detected, initiating rollback of 3 successfully scaled resources
[INFO] Starting rollback of 3 resources in namespace my-namespace
[INFO] Rolling back deployment/app1 to 3 replicas
[INFO] Successfully rolled back deployment/app1
[INFO] Rolling back deployment/app2 to 2 replicas
[INFO] Successfully rolled back deployment/app2
[INFO] Rolling back statefulset/db to 1 replicas
[ERROR] Failed to rollback statefulset/db: timeout
[INFO] Rollback completed: 3 operations performed
```

### Registro en DynamoDB

```python
# Registrar operación de rollback en logs de auditoría
dynamodb_table.put_item(Item={
    'timestamp': int(time.time()),
    'event_type': 'rollback_performed',
    'namespace': namespace,
    'cluster_name': os.getenv('EKS_CLUSTER_NAME'),
    'original_operation': 'scale_down',
    'resources_rolled_back': len(rollback_results),
    'rollback_success_count': successful_rollbacks,
    'rollback_failed_count': failed_rollbacks,
    'details': json.dumps(rollback_results)
})
```

## Testing

### Unit Tests

```python
def test_rollback_on_partial_failure():
    """Test that rollback occurs when some resources fail"""
    # Mock: primer deployment éxito, segundo fallo
    # Verificar: rollback del primero
    pass

def test_rollback_disabled():
    """Test that rollback can be disabled"""
    # Llamar con enable_rollback=False
    # Verificar: no se ejecuta rollback
    pass

def test_rollback_with_no_successful_operations():
    """Test rollback when first operation fails"""
    # Mock: primer recurso falla
    # Verificar: no se intenta rollback (nada que revertir)
    pass

def test_rollback_failure_handling():
    """Test handling of rollback failures"""
    # Mock: rollback falla para algunos recursos
    # Verificar: se registran fallos pero continúa
    pass
```

### Integration Tests

```python
def test_rollback_integration():
    """Test rollback with real cluster"""
    # 1. Crear namespace de prueba con recursos
    # 2. Simular fallo en escalado
    # 3. Verificar que recursos se revierten
    # 4. Limpiar namespace de prueba
    pass
```

## Consideraciones de Performance

### Impacto en Latencia

- **Operación normal**: Sin impacto (rollback solo en fallo)
- **Con rollback**: Tiempo adicional = N × tiempo_de_escalar_un_recurso
- **Ejemplo**: 3 recursos escalados + fallo = ~3-6 segundos adicionales para rollback

### Optimizaciones

1. **Rollback paralelo** (futura mejora):
   ```python
   # Ejecutar rollbacks en paralelo usando threads
   with ThreadPoolExecutor(max_workers=5) as executor:
       futures = [executor.submit(rollback_resource, r) for r in scaled_resources]
       results = [f.result() for f in futures]
   ```

2. **Timeout configurables**:
   ```python
   # Agregar timeout para operaciones de rollback
   rollback_result = self.execute_kubectl_command(
       f'scale {resource_type} {resource_name} --replicas={original_replicas}',
       timeout=30  # 30 segundos máximo
   )
   ```

## Mejores Prácticas

### Para Desarrolladores

1. **Siempre habilitar rollback en producción**:
   ```python
   # BIEN
   scale_namespace_resources(ns, 0, enable_rollback=True)
   
   # EVITAR (solo para testing)
   scale_namespace_resources(ns, 0, enable_rollback=False)
   ```

2. **Verificar resultado de rollback**:
   ```python
   result = scale_namespace_resources(ns, 0)
   if result.get('rollback_performed'):
       logger.error(f"Rollback was necessary: {result['rollback_results']}")
       # Alertar al equipo de operaciones
   ```

3. **Monitorear fallos de rollback**:
   ```python
   if result.get('rollback_failed_count', 0) > 0:
       # CRÍTICO: rollback falló, intervención manual requerida
       send_alert("Rollback failed", result)
   ```

### Para Operadores

1. **Monitorear logs de rollback**: Buscar patrones de `"initiating rollback"`
2. **Alertas automáticas**: Configurar alertas para rollbacks frecuentes
3. **Revisión post-rollback**: Verificar estado del namespace después de rollback
4. **Documentar incidentes**: Registrar qué causó la necesidad de rollback

## Limitaciones Conocidas

1. **No transaccional**: Kubernetes no soporta transacciones, el rollback es "best effort"
2. **Rollback secuencial**: Los rollbacks se ejecutan uno por uno (no en paralelo)
3. **Sin retry automático**: Si el rollback falla, requiere intervención manual
4. **Estado intermedio**: Hay un período breve donde el namespace está en estado inconsistente

## Futuras Mejoras

### 1. Rollback Paralelo
```python
# Ejecutar múltiples rollbacks simultáneamente
def _rollback_scaling_parallel(self, namespace, scaled_resources):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(self._rollback_single_resource, namespace, r): r 
            for r in scaled_resources
        }
        return [future.result() for future in as_completed(futures)]
```

### 2. Retry Automático
```python
# Reintentar rollback fallido
def _rollback_with_retry(self, namespace, resource, max_retries=3):
    for attempt in range(max_retries):
        result = self._rollback_single_resource(namespace, resource)
        if result['status'] == 'success':
            return result
        time.sleep(2 ** attempt)  # Exponential backoff
    return result
```

### 3. Snapshot de Estado
```python
# Guardar snapshot completo antes de operación
def _create_namespace_snapshot(self, namespace):
    return {
        'deployments': self._get_all_deployments(namespace),
        'statefulsets': self._get_all_statefulsets(namespace),
        'timestamp': time.time()
    }
```

### 4. Dry-Run Mode
```python
# Simular operación sin ejecutar
def scale_namespace_resources(self, namespace, target_replicas, dry_run=False):
    if dry_run:
        return self._simulate_scaling(namespace, target_replicas)
    # ... operación real
```

## Referencias

- [Kubernetes API - Scale](https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/scale-v1/)
- [kubectl scale](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_scale/)
- [Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy)

## Changelog

### v1.0.0 - Implementación Inicial de Rollback
- ✅ Agregado parámetro `enable_rollback` a `scale_namespace_resources()`
- ✅ Implementado método `_rollback_scaling()` para reversión automática
- ✅ Tracking de operaciones exitosas para rollback
- ✅ Detección automática de fallos que requieren rollback
- ✅ Logging detallado de operaciones de rollback
- ✅ Información completa de rollback en respuesta
- ✅ Manejo de errores durante rollback
- ✅ Documentación completa de la funcionalidad
