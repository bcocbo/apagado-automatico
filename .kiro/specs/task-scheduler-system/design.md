# Documento de Diseño - Sistema Task Scheduler

## Resumen Ejecutivo

El Sistema Task Scheduler es una plataforma especializada para la gestión automatizada de namespaces en clusters de Amazon EKS, diseñada para optimizar costos mediante el control inteligente de recursos durante horarios no hábiles. El sistema implementa un enfoque de "apagado inteligente" que permite ahorros significativos en costos de AWS mientras mantiene la flexibilidad operacional necesaria para trabajo urgente.

## Arquitectura del Sistema

### Visión General de la Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sistema Task Scheduler                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐ │
│  │   Frontend Web  │◄──►│ kubectl-namespace-ctl   │◄──►│ EKS Cluster │ │
│  │   (Nginx +      │    │ (Python Flask +  │    │             │ │
│  │   FullCalendar) │    │  kubectl + AWS)  │    │             │ │
│  └─────────────────┘    └──────────────────┘    └─────────────┘ │
│           │                       │                             │
│           └───────────────────────┼─────────────────────────────┤
│                                   │                             │
│  ┌─────────────────────────────────▼─────────────────────────┐   │
│  │                    DynamoDB                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐  │   │
│  │  │ Registros de    │  │ Configuración   │  │ Métricas │  │   │
│  │  │ Actividad       │  │ de Permisos     │  │ Sistema  │  │   │
│  │  └─────────────────┘  └─────────────────┘  └──────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes Principales

#### 1. Frontend Web
- **Tecnología**: HTML5, Bootstrap 5, FullCalendar, JavaScript ES6
- **Responsabilidades**:
  - Interfaz de usuario para gestión de namespaces
  - Visualización de estado en tiempo real
  - Calendario de activaciones programadas
  - Dashboard de métricas y costos

#### 2. kubectl-namespace-ctl (Backend)
- **Tecnología**: Python 3.9+, Flask, kubectl, AWS SDK
- **Responsabilidades**:
  - API REST para operaciones de namespace
  - Programador de tareas con cron
  - Integración con EKS y DynamoDB
  - Validación de permisos y límites

#### 3. Base de Datos DynamoDB
- **Tablas**:
  - `namespace_activity_logs`: Registros de actividad
  - `cost_center_permissions`: Permisos por centro de costo
  - `system_metrics`: Métricas operacionales

## Diseño Detallado

### Modelo de Datos

#### Tabla: namespace_activity_logs
```json
{
  "partition_key": "namespace_name",
  "sort_key": "timestamp_start",
  "attributes": {
    "namespace_name": "string",
    "timestamp_start": "number",
    "timestamp_end": "number",
    "duration_minutes": "number",
    "cost_center": "string",
    "user_id": "string",
    "operation_type": "string", // "auto_shutdown", "auto_startup", "manual_activation", "manual_deactivation"
    "status": "string", // "active", "completed", "failed"
    "error_message": "string"
  }
}
```

#### Tabla: cost_center_permissions
```json
{
  "partition_key": "cost_center",
  "attributes": {
    "cost_center": "string",
    "is_authorized": "boolean",
    "max_concurrent_namespaces": "number",
    "authorized_namespaces": ["string"],
    "created_at": "number",
    "updated_at": "number"
  }
}
```

### Flujos de Trabajo Principales

#### 1. Apagado Automático (8pm días laborales)
```
1. Scheduler ejecuta tarea cron "0 20 * * 1-5"
2. kubectl-namespace-ctl obtiene lista de namespaces activos
3. Filtra namespaces de sistema (excluye de apagado)
4. Para cada namespace de usuario:
   a. Escala deployments/statefulsets/daemonsets a 0
   b. Registra operación en DynamoDB
   c. Actualiza métricas del sistema
5. Envía notificación de completado
```

#### 2. Encendido Automático (7am días laborales)
```
1. Scheduler ejecuta tarea cron "0 7 * * 1-5"
2. kubectl-namespace-ctl consulta DynamoDB por namespaces apagados automáticamente
3. Para cada namespace a restaurar:
   a. Restaura escalado original desde metadata
   b. Actualiza registro en DynamoDB con timestamp_end
   c. Actualiza métricas del sistema
4. Envía notificación de completado
```

#### 3. Activación Manual en Horario No Hábil
```
1. Usuario envía solicitud via Frontend Web
2. kubectl-namespace-ctl valida:
   a. Horario no hábil (8pm-7am o fin de semana)
   b. Centro de costo autorizado
   c. Límite de 5 namespaces activos
3. Si validación exitosa:
   a. Activa namespace (restaura escalado)
   b. Crea registro en DynamoDB
   c. Actualiza contador de namespaces activos
4. Responde con estado de la operación
```

### Algoritmos Clave

#### Algoritmo de Validación de Horario
```python
def is_non_business_hours(timestamp, timezone='UTC'):
    """
    Determina si un timestamp está en horario no hábil
    Horario no hábil: 8pm-7am días laborales, todo el día fines de semana
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone)
    
    # Fin de semana (sábado=5, domingo=6)
    if dt.weekday() >= 5:
        return True
    
    # Días laborales: 8pm-7am
    hour = dt.hour
    return hour >= 20 or hour < 7
```

#### Algoritmo de Escalado de Recursos
```python
def scale_namespace_resources(namespace, target_replicas):
    """
    Escala todos los recursos de un namespace
    Guarda metadata original para restauración
    """
    resources = ['deployments', 'statefulsets', 'daemonsets']
    original_scales = {}
    
    for resource_type in resources:
        resources_list = kubectl.get(resource_type, namespace=namespace)
        for resource in resources_list:
            if target_replicas == 0:
                # Guardar escalado original
                original_scales[f"{resource_type}/{resource.name}"] = resource.spec.replicas
            
            # Aplicar nuevo escalado
            kubectl.scale(resource_type, resource.name, 
                         replicas=target_replicas, namespace=namespace)
    
    return original_scales
```

## Propiedades de Correctness

### Propiedades Temporales

#### Propiedad 1: Apagado Automático Puntual
**Validates: Requirements 1.1**
```python
@given(business_day_8pm_timestamps())
def test_automatic_shutdown_timing(timestamp):
    """
    PROPIEDAD: En días laborales a las 8pm, todos los namespaces de usuario 
    deben ser apagados automáticamente
    """
    # Simular llegada de timestamp 8pm día laboral
    scheduler.process_timestamp(timestamp)
    
    user_namespaces = get_user_namespaces()
    for namespace in user_namespaces:
        assert namespace.is_scaled_down()
        assert dynamodb_has_shutdown_record(namespace.name, timestamp)
```

#### Propiedad 2: Encendido Automático Puntual
**Validates: Requirements 1.2**
```python
@given(business_day_7am_timestamps())
def test_automatic_startup_timing(timestamp):
    """
    PROPIEDAD: En días laborales a las 7am, todos los namespaces previamente 
    apagados deben ser encendidos automáticamente
    """
    # Preparar: namespaces apagados la noche anterior
    setup_shutdown_namespaces(timestamp - 11*3600)  # 11 horas antes
    
    scheduler.process_timestamp(timestamp)
    
    previously_shutdown = get_previously_shutdown_namespaces(timestamp)
    for namespace in previously_shutdown:
        assert namespace.is_scaled_up()
        assert dynamodb_record_completed(namespace.name)
```

### Propiedades de Límites y Validación

#### Propiedad 3: Límite de Namespaces Activos
**Validates: Requirements 2.1, 2.2**
```python
@given(non_business_hour_timestamps(), 
       lists(namespace_activation_requests(), min_size=6, max_size=10))
def test_namespace_limit_enforcement(timestamp, activation_requests):
    """
    PROPIEDAD: Durante horarios no hábiles, máximo 5 namespaces pueden 
    estar activos simultáneamente
    """
    active_count = 0
    
    for request in activation_requests:
        response = kubectl_namespace_ctl.activate_namespace(request, timestamp)
        
        if active_count < 5:
            assert response.success == True
            active_count += 1
        else:
            assert response.success == False
            assert "limit exceeded" in response.error_message.lower()
        
        assert get_active_namespace_count() <= 5
```

#### Propiedad 4: Validación de Centro de Costo
**Validates: Requirements 3.1, 3.2**
```python
@given(cost_centers(), namespace_names())
def test_cost_center_authorization(cost_center, namespace):
    """
    PROPIEDAD: Solo centros de costo autorizados pueden activar namespaces
    """
    request = NamespaceActivationRequest(
        namespace=namespace,
        cost_center=cost_center
    )
    
    response = kubectl_namespace_ctl.activate_namespace(request)
    
    if is_authorized_cost_center(cost_center):
        assert response.success == True or response.error_reason != "unauthorized"
    else:
        assert response.success == False
        assert "unauthorized" in response.error_message.lower()
```

### Propiedades de Persistencia

#### Propiedad 5: Registro Completo de Actividad
**Validates: Requirements 4.1, 4.2, 4.3**
```python
@given(namespace_operations())
def test_complete_activity_logging(operation):
    """
    PROPIEDAD: Toda operación de namespace debe generar un registro 
    completo en DynamoDB
    """
    initial_records = count_dynamodb_records()
    
    kubectl_namespace_ctl.execute_operation(operation)
    
    final_records = count_dynamodb_records()
    assert final_records == initial_records + 1
    
    record = get_latest_record(operation.namespace)
    assert record.namespace_name == operation.namespace
    assert record.cost_center == operation.cost_center
    assert record.operation_type == operation.type
    assert record.timestamp_start > 0
    
    if operation.type in ["deactivation", "auto_shutdown"]:
        assert record.timestamp_end > record.timestamp_start
        assert record.duration_minutes > 0
```

#### Propiedad 6: Cálculo Correcto de Duración
**Validates: Requirements 4.4**
```python
@given(activation_deactivation_pairs())
def test_duration_calculation_accuracy(activation_time, deactivation_time):
    """
    PROPIEDAD: La duración calculada debe ser exacta entre activación y desactivación
    """
    assume(deactivation_time > activation_time)
    
    # Simular activación y desactivación
    kubectl_namespace_ctl.activate_namespace("test-ns", timestamp=activation_time)
    kubectl_namespace_ctl.deactivate_namespace("test-ns", timestamp=deactivation_time)
    
    record = get_namespace_record("test-ns", activation_time)
    expected_duration = (deactivation_time - activation_time) // 60  # minutos
    
    assert record.duration_minutes == expected_duration
```

### Propiedades de Resiliencia

#### Propiedad 7: Idempotencia de Operaciones
**Validates: Requirements 10.4**
```python
@given(namespace_operations())
def test_operation_idempotency(operation):
    """
    PROPIEDAD: Ejecutar la misma operación múltiples veces debe 
    producir el mismo resultado
    """
    # Ejecutar operación primera vez
    result1 = kubectl_namespace_ctl.execute_operation(operation)
    state1 = get_namespace_state(operation.namespace)
    
    # Ejecutar operación segunda vez
    result2 = kubectl_namespace_ctl.execute_operation(operation)
    state2 = get_namespace_state(operation.namespace)
    
    # Estados deben ser idénticos
    assert state1 == state2
    assert result1.success == result2.success
    
    # No debe haber registros duplicados
    records = get_namespace_records(operation.namespace)
    unique_operations = set((r.timestamp_start, r.operation_type) for r in records)
    assert len(records) == len(unique_operations)
```

#### Propiedad 8: Recuperación tras Reinicio
**Validates: Requirements 10.1, 10.3**
```python
@given(system_states_before_restart())
def test_state_recovery_after_restart(pre_restart_state):
    """
    PROPIEDAD: El sistema debe recuperar correctamente el estado 
    tras un reinicio
    """
    # Establecer estado inicial
    setup_system_state(pre_restart_state)
    
    # Simular reinicio
    kubectl_namespace_ctl.shutdown()
    kubectl_namespace_ctl.startup()
    
    # Verificar recuperación
    post_restart_state = get_current_system_state()
    
    # Estados críticos deben coincidir
    assert post_restart_state.active_namespaces == pre_restart_state.active_namespaces
    assert post_restart_state.pending_operations == pre_restart_state.pending_operations
    
    # Reconciliación debe detectar y corregir inconsistencias
    inconsistencies = detect_state_inconsistencies()
    assert len(inconsistencies) == 0
```

### Propiedades de API

#### Propiedad 9: Códigos de Estado HTTP Correctos
**Validates: Requirements 7.5**
```python
@given(api_requests())
def test_http_status_codes(request):
    """
    PROPIEDAD: La API debe devolver códigos de estado HTTP apropiados 
    para cada tipo de respuesta
    """
    response = api_client.send_request(request)
    
    if request.is_valid():
        if request.operation_successful():
            assert response.status_code in [200, 201]
        else:
            assert response.status_code in [400, 409, 422]
    else:
        assert response.status_code in [400, 401, 403]
    
    # Respuesta debe incluir mensaje descriptivo
    assert len(response.body.get('message', '')) > 0
```

## Consideraciones de Seguridad

### Autenticación y Autorización
- **Rol de AWS IAM**: Uso exclusivo de roles IAM para autenticación con AWS
- **Principio de Menor Privilegio**: Permisos mínimos necesarios para operaciones
- **Validación de Centro de Costo**: Control granular por departamento/proyecto

### Auditoría y Trazabilidad
- **Registro Completo**: Todas las operaciones se registran en DynamoDB
- **Inmutabilidad**: Los registros de auditoría no pueden ser modificados
- **Trazabilidad**: Cada operación incluye usuario, timestamp y contexto

## Consideraciones de Rendimiento

### Escalabilidad
- **Operaciones Asíncronas**: Procesamiento no bloqueante de operaciones masivas
- **Batch Processing**: Agrupación de operaciones para eficiencia
- **Caching**: Cache local de configuraciones frecuentemente accedidas

### Optimización de Costos
- **Apagado Inteligente**: Escalado a cero en lugar de eliminación de recursos
- **Programación Eficiente**: Uso de cron jobs para operaciones automáticas
- **Monitoreo de Uso**: Métricas detalladas para optimización continua

## Framework de Testing

### Property-Based Testing
- **Librería**: Hypothesis (Python)
- **Generadores Personalizados**: Timestamps, namespaces, centros de costo
- **Estrategias de Testing**: Temporal, límites, persistencia, resiliencia

### Testing de Integración
- **Entorno de Testing**: Cluster EKS dedicado para pruebas
- **DynamoDB Local**: Instancia local para testing rápido
- **Mocking**: AWS SDK mocking para testing unitario

### Métricas de Cobertura
- **Cobertura de Código**: Mínimo 90% para componentes críticos
- **Cobertura de Propiedades**: Todas las propiedades de correctness cubiertas
- **Testing de Regresión**: Suite completa ejecutada en cada deploy

## Plan de Monitoreo

### Métricas Clave
- **Operacionales**: Namespaces activos, operaciones exitosas/fallidas
- **Rendimiento**: Tiempo de respuesta API, latencia de operaciones
- **Negocio**: Ahorro de costos, uso por centro de costo

### Alertas
- **Críticas**: Fallos en apagado/encendido automático
- **Advertencias**: Límites de namespaces alcanzados
- **Informativas**: Operaciones completadas exitosamente

### Dashboards
- **Operacional**: Estado en tiempo real del sistema
- **Financiero**: Métricas de ahorro de costos
- **Auditoría**: Registros de actividad y compliance