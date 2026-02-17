# Permissions Cache Implementation / Implementación de Caché de Permisos

## English Version

### Overview
This document describes the implementation of an in-memory cache for cost center permissions, improving performance by reducing DynamoDB queries.

### Implementation Details

#### Cache Configuration
The cache is configured through environment variables:
- `PERMISSIONS_CACHE_ENABLED`: Enable/disable cache (default: `true`)
- `PERMISSIONS_CACHE_TTL`: Time-to-live in seconds (default: `300` = 5 minutes)

#### Cache Structure
```python
permissions_cache = {
    'cost_center_name': {
        'data': {
            'is_authorized': bool,
            'max_concurrent_namespaces': int,
            'authorized_namespaces': list,
            ...
        },
        'timestamp': float  # Unix timestamp
    }
}
```

#### Cache Operations

##### 1. Cache Lookup (`_get_from_cache`)
- Checks if cost center exists in cache
- Validates TTL (Time To Live)
- Returns cached data if valid, None if expired or not found
- Automatically removes expired entries

##### 2. Cache Storage (`_put_in_cache`)
- Stores cost center permissions with current timestamp
- Overwrites existing entries

##### 3. Cache Invalidation (`invalidate_cache`)
- Can invalidate specific cost center or all cache
- Automatically called when permissions are updated

##### 4. Cache Statistics (`get_cache_stats`)
- Returns cache status, TTL, and number of entries
- Lists all cached cost centers

#### Modified Methods

##### `validate_cost_center_permissions(cost_center)`
**Before:**
- Always queries DynamoDB

**After:**
1. Check cache first (if enabled)
2. Return cached value if valid
3. Query DynamoDB on cache miss
4. Store result in cache
5. Cache negative results (not found) to avoid repeated lookups

##### `set_cost_center_permissions(...)`
**Before:**
- Updates DynamoDB only

**After:**
1. Updates DynamoDB
2. Invalidates cache for the cost center
3. Next validation will fetch fresh data

### New API Endpoints

#### GET `/api/cache/stats`
Get cache statistics.

**Response:**
```json
{
  "enabled": true,
  "ttl_seconds": 300,
  "cached_entries": 5,
  "entries": ["dev-center", "test-center", "prod-center"]
}
```

#### POST `/api/cache/invalidate`
Invalidate cache for specific cost center or all cache.

**Request Body:**
```json
{
  "cost_center": "dev-center"  // Optional, omit to invalidate all
}
```

**Response:**
```json
{
  "message": "Cache invalidated for cost center dev-center"
}
```

### Performance Benefits

#### Without Cache
- Every validation = 1 DynamoDB query
- 100 validations = 100 DynamoDB queries
- Higher latency (~50-200ms per query)
- Higher AWS costs

#### With Cache (5 min TTL)
- First validation = 1 DynamoDB query + cache store
- Subsequent validations = cache lookup (~1ms)
- 100 validations in 5 min = 1 DynamoDB query + 99 cache hits
- 99% reduction in DynamoDB queries
- Lower latency and costs

### Cache Behavior

#### Cache Hit Flow
```
validate_cost_center_permissions()
    ↓
Check cache
    ↓
Entry exists and not expired? → YES
    ↓
Return cached value (fast)
```

#### Cache Miss Flow
```
validate_cost_center_permissions()
    ↓
Check cache
    ↓
Entry missing or expired? → YES
    ↓
Query DynamoDB
    ↓
Store in cache
    ↓
Return value
```

#### Cache Invalidation Flow
```
set_cost_center_permissions()
    ↓
Update DynamoDB
    ↓
Invalidate cache for cost center
    ↓
Next validation will fetch fresh data
```

### Testing

#### Test Suite: `test_permissions_cache.py`

**Test Cases:**
1. Check initial cache stats
2. Setup test cost center
3. First validation (cache miss)
4. Second validation (cache hit, should be faster)
5. Check cache stats after validations
6. Update permissions and verify cache invalidation
7. Manual cache invalidation
8. Invalidate all cache

**Running Tests:**
```bash
cd kubectl-runner/src
python3 test_permissions_cache.py
```

### Configuration Examples

#### Enable cache with 10-minute TTL
```yaml
env:
- name: PERMISSIONS_CACHE_ENABLED
  value: "true"
- name: PERMISSIONS_CACHE_TTL
  value: "600"
```

#### Disable cache (always query DynamoDB)
```yaml
env:
- name: PERMISSIONS_CACHE_ENABLED
  value: "false"
```

### Monitoring

Use the `/api/cache/stats` endpoint to monitor:
- Cache hit rate (indirectly through cached entries)
- Number of cached cost centers
- Cache configuration

### Best Practices

1. **TTL Selection:**
   - Short TTL (1-5 min): More frequent updates, higher DynamoDB usage
   - Long TTL (10-30 min): Better performance, slower permission updates
   - Default (5 min): Good balance

2. **Cache Invalidation:**
   - Automatic on permission updates
   - Manual invalidation available for troubleshooting
   - Consider invalidating after bulk permission changes

3. **Monitoring:**
   - Check cache stats regularly
   - Monitor DynamoDB query reduction
   - Adjust TTL based on usage patterns

---

## Versión en Español

### Descripción General
Este documento describe la implementación de un caché en memoria para permisos de centros de costo, mejorando el rendimiento al reducir las consultas a DynamoDB.

### Detalles de Implementación

#### Configuración del Caché
El caché se configura mediante variables de entorno:
- `PERMISSIONS_CACHE_ENABLED`: Habilitar/deshabilitar caché (predeterminado: `true`)
- `PERMISSIONS_CACHE_TTL`: Tiempo de vida en segundos (predeterminado: `300` = 5 minutos)

#### Estructura del Caché
```python
permissions_cache = {
    'nombre_centro_costo': {
        'data': {
            'is_authorized': bool,
            'max_concurrent_namespaces': int,
            'authorized_namespaces': list,
            ...
        },
        'timestamp': float  # Timestamp Unix
    }
}
```

#### Operaciones del Caché

##### 1. Búsqueda en Caché (`_get_from_cache`)
- Verifica si el centro de costo existe en caché
- Valida el TTL (Time To Live)
- Retorna datos cacheados si son válidos, None si expiraron o no existen
- Elimina automáticamente entradas expiradas

##### 2. Almacenamiento en Caché (`_put_in_cache`)
- Almacena permisos del centro de costo con timestamp actual
- Sobrescribe entradas existentes

##### 3. Invalidación de Caché (`invalidate_cache`)
- Puede invalidar un centro de costo específico o todo el caché
- Se llama automáticamente cuando se actualizan permisos

##### 4. Estadísticas del Caché (`get_cache_stats`)
- Retorna estado del caché, TTL y número de entradas
- Lista todos los centros de costo cacheados

#### Métodos Modificados

##### `validate_cost_center_permissions(cost_center)`
**Antes:**
- Siempre consulta DynamoDB

**Después:**
1. Verifica caché primero (si está habilitado)
2. Retorna valor cacheado si es válido
3. Consulta DynamoDB en caso de cache miss
4. Almacena resultado en caché
5. Cachea resultados negativos (no encontrado) para evitar búsquedas repetidas

##### `set_cost_center_permissions(...)`
**Antes:**
- Solo actualiza DynamoDB

**Después:**
1. Actualiza DynamoDB
2. Invalida caché para el centro de costo
3. La próxima validación obtendrá datos frescos

### Nuevos Endpoints de API

#### GET `/api/cache/stats`
Obtener estadísticas del caché.

**Respuesta:**
```json
{
  "enabled": true,
  "ttl_seconds": 300,
  "cached_entries": 5,
  "entries": ["dev-center", "test-center", "prod-center"]
}
```

#### POST `/api/cache/invalidate`
Invalidar caché para un centro de costo específico o todo el caché.

**Cuerpo de Solicitud:**
```json
{
  "cost_center": "dev-center"  // Opcional, omitir para invalidar todo
}
```

**Respuesta:**
```json
{
  "message": "Cache invalidated for cost center dev-center"
}
```

### Beneficios de Rendimiento

#### Sin Caché
- Cada validación = 1 consulta DynamoDB
- 100 validaciones = 100 consultas DynamoDB
- Mayor latencia (~50-200ms por consulta)
- Mayores costos de AWS

#### Con Caché (TTL 5 min)
- Primera validación = 1 consulta DynamoDB + almacenamiento en caché
- Validaciones subsecuentes = búsqueda en caché (~1ms)
- 100 validaciones en 5 min = 1 consulta DynamoDB + 99 cache hits
- 99% de reducción en consultas DynamoDB
- Menor latencia y costos

### Comportamiento del Caché

#### Flujo de Cache Hit
```
validate_cost_center_permissions()
    ↓
Verificar caché
    ↓
¿Entrada existe y no expiró? → SÍ
    ↓
Retornar valor cacheado (rápido)
```

#### Flujo de Cache Miss
```
validate_cost_center_permissions()
    ↓
Verificar caché
    ↓
¿Entrada falta o expiró? → SÍ
    ↓
Consultar DynamoDB
    ↓
Almacenar en caché
    ↓
Retornar valor
```

#### Flujo de Invalidación de Caché
```
set_cost_center_permissions()
    ↓
Actualizar DynamoDB
    ↓
Invalidar caché para centro de costo
    ↓
Próxima validación obtendrá datos frescos
```

### Pruebas

#### Suite de Pruebas: `test_permissions_cache.py`

**Casos de Prueba:**
1. Verificar estadísticas iniciales del caché
2. Configurar centro de costo de prueba
3. Primera validación (cache miss)
4. Segunda validación (cache hit, debería ser más rápida)
5. Verificar estadísticas del caché después de validaciones
6. Actualizar permisos y verificar invalidación de caché
7. Invalidación manual de caché
8. Invalidar todo el caché

**Ejecutar Pruebas:**
```bash
cd kubectl-runner/src
python3 test_permissions_cache.py
```

### Ejemplos de Configuración

#### Habilitar caché con TTL de 10 minutos
```yaml
env:
- name: PERMISSIONS_CACHE_ENABLED
  value: "true"
- name: PERMISSIONS_CACHE_TTL
  value: "600"
```

#### Deshabilitar caché (siempre consultar DynamoDB)
```yaml
env:
- name: PERMISSIONS_CACHE_ENABLED
  value: "false"
```

### Monitoreo

Use el endpoint `/api/cache/stats` para monitorear:
- Tasa de cache hit (indirectamente a través de entradas cacheadas)
- Número de centros de costo cacheados
- Configuración del caché

### Mejores Prácticas

1. **Selección de TTL:**
   - TTL corto (1-5 min): Actualizaciones más frecuentes, mayor uso de DynamoDB
   - TTL largo (10-30 min): Mejor rendimiento, actualizaciones de permisos más lentas
   - Predeterminado (5 min): Buen balance

2. **Invalidación de Caché:**
   - Automática en actualizaciones de permisos
   - Invalidación manual disponible para troubleshooting
   - Considerar invalidar después de cambios masivos de permisos

3. **Monitoreo:**
   - Verificar estadísticas del caché regularmente
   - Monitorear reducción de consultas DynamoDB
   - Ajustar TTL según patrones de uso
