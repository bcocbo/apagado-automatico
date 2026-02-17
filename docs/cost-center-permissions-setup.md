# Cost Center Permissions Setup

Este documento explica cómo configurar la tabla `cost-center-permissions` para validación de centros de costo en el Namespace Scheduler.

## Descripción

La tabla `cost-center-permissions` almacena la configuración de permisos para cada centro de costo, incluyendo:

- **cost_center**: Identificador único del centro de costo (clave primaria)
- **is_authorized**: Si el centro de costo está autorizado para operar
- **max_concurrent_namespaces**: Máximo número de namespaces concurrentes permitidos
- **authorized_namespaces**: Lista de patrones de namespaces autorizados (soporta wildcards)
- **description**: Descripción del centro de costo
- **created_at/updated_at**: Timestamps de creación y actualización

## Creación de la Tabla

### Opción 1: CloudFormation (Recomendado)

```bash
# Crear ambas tablas (logs y permissions)
./scripts/create-dynamodb-tables.sh production

# O usar un entorno específico
./scripts/create-dynamodb-tables.sh development
```

### Opción 2: Script Python

```bash
# Crear solo la tabla de permisos
python3 scripts/create_dynamodb_table.py --table permissions

# Crear ambas tablas
python3 scripts/create_dynamodb_table.py --table all

# Usar un entorno específico
python3 scripts/create_dynamodb_table.py --environment development --table permissions
```

## Población con Datos Iniciales

Una vez creada la tabla, poblarla con centros de costo iniciales. Hay dos opciones:

### Opción 1: Kubernetes Job (Recomendado para Producción)

Ejecutar el Job de Kubernetes que poblará automáticamente la tabla:

```bash
# Aplicar el Job
kubectl apply -f manifests/base/populate-permissions-job.yaml

# Verificar el estado del Job
kubectl get jobs -n task-scheduler

# Ver los logs de ejecución
kubectl logs -n task-scheduler job/populate-cost-center-permissions
```

El Job:
- Usa la imagen `python:3.11-slim` con boto3
- Se ejecuta con el ServiceAccount `kubectl-runner` (que tiene permisos IAM para DynamoDB)
- Se auto-elimina después de 5 minutos (ttlSecondsAfterFinished: 300)
- Puebla la tabla `cost-center-permissions-production` con los centros de costo iniciales
- Es idempotente: no sobrescribe registros existentes

### Opción 2: Script Local

Ejecutar el script Python localmente (requiere credenciales AWS configuradas):

```bash
# Poblar con datos por defecto
python3 scripts/populate-cost-center-permissions.py

# Usar un entorno específico
python3 scripts/populate-cost-center-permissions.py --environment development
```

### Centros de Costo Iniciales

El script crea los siguientes centros de costo por defecto:

| Centro de Costo | Autorizado | Max NS | Patrones Autorizados | Descripción |
|-----------------|------------|--------|---------------------|-------------|
| IT-DEVELOPMENT | ✅ | 10 | dev-*, test-*, staging-* | Desarrollo de TI |
| IT-PRODUCTION | ✅ | 5 | prod-*, production-* | Producción de TI |
| QA-TESTING | ✅ | 8 | qa-*, test-*, e2e-* | Testing y QA |
| DEVOPS-INFRA | ✅ | 15 | * | Infraestructura DevOps |
| DEMO-SANDBOX | ✅ | 3 | demo-*, sandbox-* | Demos y sandbox |
| EXTERNAL-CONTRACTOR | ❌ | 2 | contractor-* | Contratistas externos |

## Gestión de Permisos

### Vía API

```bash
# Autorizar un centro de costo
curl -X POST http://localhost:8080/api/cost-centers/IT-DEVELOPMENT/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "is_authorized": true,
    "max_concurrent_namespaces": 10,
    "authorized_namespaces": ["dev-*", "test-*"]
  }'

# Desautorizar un centro de costo
curl -X POST http://localhost:8080/api/cost-centers/EXTERNAL-CONTRACTOR/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "is_authorized": false,
    "max_concurrent_namespaces": 0,
    "authorized_namespaces": []
  }'
```

### Vía DynamoDB Console

También puedes gestionar los permisos directamente desde la consola de AWS DynamoDB:

1. Ir a DynamoDB Console
2. Seleccionar la tabla `cost-center-permissions-{environment}`
3. Editar items existentes o crear nuevos

## Patrones de Namespaces

Los patrones de namespaces soportan wildcards:

- `*`: Coincide con cualquier cadena
- `dev-*`: Coincide con namespaces que empiecen con "dev-"
- `*-prod`: Coincide con namespaces que terminen con "-prod"
- `test-*-env`: Coincide con namespaces como "test-api-env", "test-db-env"

## Validación

El sistema valida automáticamente:

1. **Centro de costo autorizado**: `is_authorized = true`
2. **Límite de namespaces**: No exceder `max_concurrent_namespaces`
3. **Patrones de namespace**: El namespace debe coincidir con al menos un patrón en `authorized_namespaces`

## Troubleshooting

### Error: Tabla no existe

```bash
# Verificar que la tabla existe
aws dynamodb describe-table --table-name cost-center-permissions-production

# Si no existe, crearla
python3 scripts/create_dynamodb_table.py --table permissions
```

### Error: Kubernetes Job falla

```bash
# Ver logs del Job
kubectl logs -n task-scheduler job/populate-cost-center-permissions

# Verificar que el ServiceAccount tiene permisos IAM
kubectl describe serviceaccount kubectl-runner -n task-scheduler

# Verificar que la anotación IAM role está presente
kubectl get serviceaccount kubectl-runner -n task-scheduler -o yaml | grep eks.amazonaws.com/role-arn

# Re-ejecutar el Job (primero eliminar el anterior)
kubectl delete job populate-cost-center-permissions -n task-scheduler
kubectl apply -f manifests/base/populate-permissions-job.yaml
```

### Error: Centro de costo no autorizado

1. Verificar que el centro de costo existe en la tabla
2. Verificar que `is_authorized = true`
3. Verificar que el namespace coincide con los patrones autorizados

### Error: Límite de namespaces excedido

1. Verificar cuántos namespaces están activos para ese centro de costo
2. Ajustar `max_concurrent_namespaces` si es necesario
3. Desactivar namespaces no utilizados

## Variables de Entorno

Asegúrate de configurar estas variables en el deployment:

```yaml
env:
- name: PERMISSIONS_TABLE_NAME
  value: "cost-center-permissions-production"
- name: AWS_REGION
  value: "us-east-1"
- name: PERMISSIONS_CACHE_ENABLED
  value: "true"
- name: PERMISSIONS_CACHE_TTL
  value: "300"
```

### Configuración de Cache

El backend implementa un cache en memoria para permisos de centros de costo:

- **PERMISSIONS_CACHE_ENABLED**: Habilitar/deshabilitar cache (default: "true")
- **PERMISSIONS_CACHE_TTL**: Tiempo de vida del cache en segundos (default: 300 = 5 minutos)

El cache reduce las operaciones de lectura a DynamoDB y mejora el rendimiento. Se invalida automáticamente cuando se actualizan permisos vía API.

## Monitoreo

Para monitorear el uso de la tabla:

```bash
# Ver estadísticas de la tabla
aws dynamodb describe-table --table-name cost-center-permissions-production \
  --query 'Table.{ItemCount: ItemCount, TableSizeBytes: TableSizeBytes}'

# Listar todos los centros de costo
aws dynamodb scan --table-name cost-center-permissions-production \
  --projection-expression "cost_center, is_authorized, max_concurrent_namespaces"
```

### Monitoreo del Cache

Para verificar el estado del cache de permisos:

```bash
# Ver estadísticas del cache
curl http://localhost:8080/api/cache/stats

# Respuesta esperada:
# {
#   "enabled": true,
#   "ttl_seconds": 300,
#   "cached_entries": 5,
#   "entries": ["IT-DEVELOPMENT", "IT-PRODUCTION", "QA-TESTING", "DEVOPS-INFRA", "DEMO-SANDBOX"]
# }

# Invalidar cache para un centro de costo específico
curl -X POST http://localhost:8080/api/cache/invalidate/IT-DEVELOPMENT

# Invalidar todo el cache
curl -X POST http://localhost:8080/api/cache/invalidate
```