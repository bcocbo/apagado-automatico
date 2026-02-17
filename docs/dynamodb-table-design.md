# DynamoDB Table Design

Este documento describe el diseño de las tablas DynamoDB utilizadas por el Namespace Scheduler.

## Tabla de Configuración: cost-center-permissions

### Estructura de la Tabla

La tabla `cost-center-permissions` almacena la configuración de permisos y límites para cada centro de costo.

#### Esquema de Claves

- **Hash Key (Partition Key)**: `cost_center` (String)

#### Atributos

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `cost_center` | String | Identificador único del centro de costo (Hash Key) |
| `is_authorized` | Boolean | Si el centro de costo está autorizado para usar el sistema |
| `max_concurrent_namespaces` | Number | Número máximo de namespaces activos simultáneamente |
| `allowed_clusters` | List | Lista de clusters donde puede operar (opcional) |
| `contact_email` | String | Email de contacto del responsable del centro de costo |
| `description` | String | Descripción del centro de costo |
| `created_at` | String | Timestamp de creación del registro |
| `updated_at` | String | Timestamp de última actualización |

### Configuración de la Tabla

- **Modo de Facturación**: PAY_PER_REQUEST (On-Demand)
- **Point-in-Time Recovery**: Habilitado
- **Nombre**: `cost-center-permissions-{Environment}`

### Patrones de Consulta

#### 1. Validar Centro de Costo
```python
# Verificar si un centro de costo está autorizado
response = dynamodb.get_item(
    TableName='cost-center-permissions-production',
    Key={'cost_center': {'S': 'CC-001'}}
)

if response.get('Item') and response['Item']['is_authorized']['BOOL']:
    max_namespaces = response['Item']['max_concurrent_namespaces']['N']
```

#### 2. Listar Centros de Costo Autorizados
```python
# Obtener todos los centros de costo autorizados
response = dynamodb.scan(
    TableName='cost-center-permissions-production',
    FilterExpression='is_authorized = :auth',
    ExpressionAttributeValues={':auth': {'BOOL': True}}
)
```

### Ejemplo de Registro
```json
{
  "cost_center": "CC-001",
  "is_authorized": true,
  "max_concurrent_namespaces": 5,
  "allowed_clusters": ["production-cluster", "staging-cluster"],
  "contact_email": "team-lead@company.com",
  "description": "Development Team Alpha",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

## Tabla Principal: task-scheduler-logs

### Estructura de la Tabla

La tabla `task-scheduler-logs` almacena todas las actividades de activación y desactivación de namespaces.

#### Esquema de Claves

- **Hash Key (Partition Key)**: `namespace_name` (String)
- **Range Key (Sort Key)**: `timestamp_start` (Number - Unix timestamp)

#### Atributos

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `namespace_name` | String | Nombre del namespace (Hash Key) |
| `timestamp_start` | Number | Timestamp de inicio de la operación (Range Key) |
| `operation_type` | String | Tipo de operación: "activate", "deactivate", "command" |
| `cost_center` | String | Centro de costo asociado a la operación |
| `cluster_name` | String | Nombre del cluster donde se ejecuta la operación |
| `requested_by` | String | Usuario que solicita la operación |
| `approved_by` | String | Usuario que aprueba la operación (opcional) |
| `user_id` | String | ID del usuario que ejecutó la operación (legacy) |
| `status` | String | Estado: "active", "completed", "failed" |
| `timestamp_end` | Number | Timestamp de finalización (opcional) |
| `duration_minutes` | Number | Duración en minutos (calculado) |

### Índices Secundarios Globales (GSI)

#### 1. cost-center-timestamp-index

- **Hash Key**: `cost_center` (String)
- **Range Key**: `timestamp_start` (Number)
- **Proyección**: ALL (todos los atributos)

**Casos de uso:**
- Consultar actividades por centro de costo
- Filtrar logs por centro de costo y rango de fechas
- Generar reportes por centro de costo

#### 2. operation-type-timestamp-index

- **Hash Key**: `operation_type` (String)
- **Range Key**: `timestamp_start` (Number)
- **Proyección**: ALL (todos los atributos)

**Casos de uso:**
- Consultar todas las activaciones o desactivaciones
- Analizar patrones de uso por tipo de operación
- Generar estadísticas por tipo de operación

#### 3. cluster-timestamp-index

- **Hash Key**: `cluster_name` (String)
- **Range Key**: `timestamp_start` (Number)
- **Proyección**: ALL (todos los atributos)

**Casos de uso:**
- Consultar actividades por cluster específico
- Filtrar logs por cluster y rango de fechas
- Generar reportes por cluster
- Monitorear actividad en clusters específicos

#### 4. requested-by-timestamp-index

- **Hash Key**: `requested_by` (String)
- **Range Key**: `timestamp_start` (Number)
- **Proyección**: ALL (todos los atributos)

**Casos de uso:**
- Consultar actividades por usuario solicitante
- Auditoría de operaciones por usuario
- Generar reportes de actividad por usuario
- Rastrear solicitudes de usuarios específicos

## Patrones de Consulta Soportados

### 1. Consultas por Namespace
```python
# Obtener todas las actividades de un namespace
response = dynamodb.query(
    TableName='task-scheduler-logs',
    KeyConditionExpression='namespace_name = :ns',
    ExpressionAttributeValues={':ns': 'my-namespace'}
)

# Obtener actividades de un namespace en un rango de tiempo
response = dynamodb.query(
    TableName='task-scheduler-logs',
    KeyConditionExpression='namespace_name = :ns AND timestamp_start BETWEEN :start AND :end',
    ExpressionAttributeValues={
        ':ns': 'my-namespace',
        ':start': 1640995200,
        ':end': 1672531199
    }
)
```

### 2. Consultas por Centro de Costo
```python
# Obtener todas las actividades de un centro de costo
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='cost-center-timestamp-index',
    KeyConditionExpression='cost_center = :cc',
    ExpressionAttributeValues={':cc': 'CC-001'}
)
```

### 3. Consultas por Cluster
```python
# Obtener todas las actividades de un cluster
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='cluster-timestamp-index',
    KeyConditionExpression='cluster_name = :cluster',
    ExpressionAttributeValues={':cluster': 'production-cluster'}
)

# Obtener actividades de un cluster en un rango de tiempo
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='cluster-timestamp-index',
    KeyConditionExpression='cluster_name = :cluster AND timestamp_start BETWEEN :start AND :end',
    ExpressionAttributeValues={
        ':cluster': 'production-cluster',
        ':start': 1640995200,
        ':end': 1672531199
    }
)
```

### 4. Consultas por Usuario Solicitante
```python
# Obtener todas las solicitudes de un usuario
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='requested-by-timestamp-index',
    KeyConditionExpression='requested_by = :user',
    ExpressionAttributeValues={':user': 'john.doe@company.com'}
)

# Obtener solicitudes de un usuario en un rango de tiempo
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='requested-by-timestamp-index',
    KeyConditionExpression='requested_by = :user AND timestamp_start BETWEEN :start AND :end',
    ExpressionAttributeValues={
        ':user': 'john.doe@company.com',
        ':start': 1640995200,
        ':end': 1672531199
    }
)
```

### 5. Consultas por Tipo de Operación
```python
# Obtener todas las activaciones
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='operation-type-timestamp-index',
    KeyConditionExpression='operation_type = :op',
    ExpressionAttributeValues={':op': 'activate'}
)
```

### 6. Consultas de Estado Actual
```python
# Obtener namespaces actualmente activos
response = dynamodb.scan(
    TableName='task-scheduler-logs',
    FilterExpression='#status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={':status': 'active'}
)
```

### 7. Consultas con Filtros Combinados
```python
# Obtener actividades de un cluster con aprobador específico
response = dynamodb.query(
    TableName='task-scheduler-logs',
    IndexName='cluster-timestamp-index',
    KeyConditionExpression='cluster_name = :cluster',
    FilterExpression='approved_by = :approver',
    ExpressionAttributeValues={
        ':cluster': 'production-cluster',
        ':approver': 'manager@company.com'
    }
)
```

## Configuración de la Tabla

### Modo de Facturación
- **Modo**: PAY_PER_REQUEST (On-Demand)
- **Ventaja**: No requiere planificación de capacidad
- **Ideal para**: Cargas de trabajo impredecibles

### Características Adicionales

#### DynamoDB Streams
- **Habilitado**: Sí
- **Tipo de Vista**: NEW_AND_OLD_IMAGES
- **Uso**: Triggers para notificaciones en tiempo real

#### Point-in-Time Recovery
- **Habilitado**: Sí
- **Ventana**: 35 días
- **Uso**: Backup y recuperación de datos

## Scripts de Creación

### Opción 1: CloudFormation
```bash
./scripts/create-dynamodb-tables.sh production
```

### Opción 2: Python/Boto3
```bash
python scripts/create_dynamodb_table.py --environment production
```

## Consideraciones de Performance

### Distribución de Claves
- La clave de partición `namespace_name` debe distribuirse uniformemente
- Evitar "hot partitions" usando nombres de namespace diversos
- Los nuevos GSI por `cluster_name` y `requested_by` también deben tener buena distribución

### Límites de DynamoDB
- Tamaño máximo de item: 400 KB
- Throughput por partición: 3,000 RCU / 1,000 WCU
- Número máximo de GSI: 20 por tabla (actualmente usando 4)

### Optimizaciones
- Usar proyecciones específicas en GSI si no se necesitan todos los atributos
- Considerar TTL para logs antiguos si es necesario
- Monitorear métricas de throttling

## Monitoreo

### Métricas Clave
- `ConsumedReadCapacityUnits`
- `ConsumedWriteCapacityUnits`
- `ThrottledRequests`
- `SystemErrors`

### Alertas Recomendadas
- Throttling > 0
- Errores del sistema > 1%
- Latencia P99 > 100ms

## Ejemplo de Registro Completo

```json
{
  "namespace_name": "my-app-dev",
  "timestamp_start": 1640995200,
  "operation_type": "activate",
  "cost_center": "CC-001",
  "cluster_name": "production-cluster",
  "requested_by": "john.doe@company.com",
  "approved_by": "manager@company.com",
  "user_id": "admin@company.com",
  "status": "completed",
  "timestamp_end": 1640995260,
  "duration_minutes": 1
}
```

## Casos de Uso de Auditoría

### 1. Rastreo de Solicitudes por Usuario
- Consultar todas las operaciones solicitadas por un usuario específico
- Identificar patrones de uso por usuario
- Generar reportes de actividad individual

### 2. Seguimiento de Aprobaciones
- Identificar qué operaciones requirieron aprobación
- Rastrear quién aprobó cada operación
- Generar reportes de cadena de aprobación

### 3. Monitoreo por Cluster
- Analizar actividad en clusters específicos
- Identificar clusters con mayor actividad
- Planificar recursos por cluster

### 4. Auditoría de Centros de Costo
- Rastrear uso de recursos por centro de costo
- Generar reportes de facturación
- Identificar centros de costo con mayor actividad