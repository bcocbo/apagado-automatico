# Infraestructura AWS - Sistema MVP de Auto-Encendido de Namespaces

Este directorio contiene la configuración de infraestructura AWS necesaria para el sistema MVP de auto-encendido de namespaces, trabajando con la infraestructura existente del proyecto.

## Arquitectura de Contenedores

### Controlador (Backend)
El controlador utiliza un Dockerfile optimizado que cumple con los requisitos de seguridad:

**Imagen Base**: `python:3.11-slim`
- Multi-stage build para minimizar superficie de ataque
- Usuario no-root (`appuser:1001`) con permisos mínimos
- kubectl v1.29.0 integrado y verificado con checksums
- Tini como init system para manejo apropiado de señales
- Health checks automáticos en puerto 8080
- Soporte multi-arquitectura (AMD64/ARM64)

**Variables de Entorno de Producción**:
```bash
PYTHONPATH=/app
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PIP_NO_CACHE_DIR=1
PIP_DISABLE_PIP_VERSION_CHECK=1
```

**Puertos y Health Checks**:
- Puerto 8080: API FastAPI y métricas Prometheus
- Health check: `GET /health` cada 30s con timeout 10s
- Readiness: Verificación de conexiones DynamoDB y EKS

## Componentes de Infraestructura

### 1. DynamoDB
- **Tabla**: `NamespaceSchedules` (existente)
- **GSI**: `estado-fecha_encendido-index` (nuevo)
- **Propósito**: Almacenar programaciones de encendido/apagado

### 2. S3
- **Bucket**: `namespace-scheduler-config-{environment}-{account-id}`
- **Archivo**: `config.json`
- **Propósito**: Configuración de centros de costo por namespace

### 3. IAM
- **Rol**: `NamespaceControllerRole` (existente)
- **Políticas adicionales**: Permisos para S3 y DynamoDB GSI

## Proceso de Configuración Automatizada

El script de infraestructura (`create-infrastructure.sh`) realiza las siguientes operaciones de forma automatizada:

### 1. Verificación y Configuración de DynamoDB
- Verifica si la tabla `NamespaceSchedules` existe
- Crea la tabla si no existe con configuración pay-per-request
- Verifica y crea el GSI `estado-fecha_encendido-index` si no existe
- Configura tags apropiados para el entorno

### 2. Configuración de S3
- Crea bucket con nombre único: `namespace-scheduler-config-{environment}-{account-id}`
- Configura encriptación AES256 automática
- Habilita versionado para control de cambios
- Bloquea acceso público por seguridad
- Crea archivo de configuración inicial con mapeo de centros de costo

### 3. Gestión de Permisos IAM
- Verifica existencia del rol `NamespaceControllerRole`
- Crea y adjunta política S3 si no existe
- Valida permisos DynamoDB existentes
- Proporciona resumen de configuración de permisos

### 4. Validación y Resumen
- Muestra resumen completo de recursos creados
- Proporciona variables de entorno necesarias para deployment
- Lista próximos pasos para completar la configuración

## Archivos

### `deploy.sh`
Script principal de despliegue que:
- Verifica conexión a Kubernetes y AWS
- Crea la infraestructura AWS faltante
- Actualiza el deployment existente
- Configura variables de entorno

### `dynamodb-table.yaml`
- ConfigMap con script completo para crear/verificar infraestructura AWS
- Job de Kubernetes para ejecutar el script de configuración
- Incluye verificación y creación de tabla DynamoDB con GSI
- Configuración automática de bucket S3 con encriptación y versionado
- Validación y actualización de permisos IAM
- Creación de archivo de configuración inicial con mapeo de centros de costo

### `configmap.yaml`
- ConfigMap con configuración del sistema
- Secret template para notificaciones

### `update-deployment.yaml`
- Patch para actualizar el deployment existente
- Nuevas variables de entorno necesarias

## Despliegue

### Prerrequisitos
1. Acceso al cluster EKS donde está desplegado el sistema
2. AWS CLI configurado con permisos administrativos
3. kubectl configurado para el cluster correcto
4. El namespace `encendido-eks` debe existir
5. El deployment `namespace-scaler` debe estar desplegado por ArgoCD

### Ejecutar Despliegue
```bash
cd infrastructure
./deploy.sh
```

### Variables de Entorno
El script usa las siguientes variables (opcionales):
- `AWS_REGION`: Región de AWS (default: us-east-1)
- `ENVIRONMENT`: Entorno (default: prod)

Ejemplo:
```bash
AWS_REGION=us-west-2 ENVIRONMENT=staging ./deploy.sh
```

## Verificación Post-Despliegue

### 0. Verificar Imagen Docker (Nuevo)
```bash
# Verificar que la imagen se construyó correctamente
docker images | grep namespace-startup-scheduler-controller

# Verificar usuario no-root
docker run --rm namespace-startup-scheduler-controller:local id

# Verificar kubectl integrado
docker run --rm namespace-startup-scheduler-controller:local kubectl version --client

# Escanear vulnerabilidades
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image namespace-startup-scheduler-controller:local
```

### 1. Verificar Infraestructura AWS
```bash
# Verificar tabla DynamoDB
aws dynamodb describe-table --table-name NamespaceSchedules

# Verificar bucket S3
aws s3 ls s3://namespace-scheduler-config-prod-{account-id}/

# Verificar archivo de configuración
aws s3 cp s3://namespace-scheduler-config-prod-{account-id}/config.json -
```

### 2. Verificar Deployment
```bash
# Estado del deployment
kubectl get deployment namespace-scaler -n encendido-eks

# Logs del pod
kubectl logs -n encendido-eks -l app=namespace-scaler

# Health check
kubectl port-forward -n encendido-eks svc/namespace-scaler-service 8081:8081
curl http://localhost:8081/health
```

### 3. Verificar Frontend
```bash
# Acceder al frontend
kubectl port-forward -n encendido-eks svc/namespace-scaler-service 8081:8081
# Abrir http://localhost:8081/frontend en el navegador
```

## Configuración de Centros de Costo

El archivo `config.json` en S3 contiene el mapeo de namespaces a centros de costo:

```json
{
  "namespace-centros": {
    "production-app": ["CC001", "CC002", "CC003"],
    "staging-app": ["CC001", "CC002"],
    "development-app": ["CC001"]
  },
  "configuracion": {
    "version": "1.0",
    "limite_namespaces": 5,
    "horario_minimo_encendido": "08:00",
    "horario_maximo_apagado": "03:00"
  }
}
```

Para actualizar la configuración:
```bash
# Descargar archivo actual
aws s3 cp s3://namespace-scheduler-config-prod-{account-id}/config.json config.json

# Editar archivo
nano config.json

# Subir archivo actualizado
aws s3 cp config.json s3://namespace-scheduler-config-prod-{account-id}/config.json
```

## Notificaciones (Opcional)

Para habilitar notificaciones de rollback:

### Slack
```bash
kubectl patch secret notification-secrets -n encendido-eks --patch '
{
  "stringData": {
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  }
}'
```

### Email
```bash
kubectl patch secret notification-secrets -n encendido-eks --patch '
{
  "stringData": {
    "smtp_server": "smtp.gmail.com",
    "smtp_user": "your-email@domain.com",
    "smtp_password": "your-app-password",
    "notification_email": "admin@domain.com"
  }
}'
```

## Troubleshooting

### Error: Job de infraestructura falló
```bash
# Ver logs del job
kubectl logs job/aws-infrastructure-setup -n encendido-eks

# Verificar permisos IAM
aws iam get-role --role-name NamespaceControllerRole
```

### Error: Deployment no se actualiza
```bash
# Verificar que el deployment existe
kubectl get deployment namespace-scaler -n encendido-eks

# Forzar recreación del pod
kubectl rollout restart deployment/namespace-scaler -n encendido-eks
```

### Error: Health check falla
```bash
# Ver logs detallados
kubectl logs -n encendido-eks -l app=namespace-scaler --tail=50

# Verificar variables de entorno
kubectl describe pod -n encendido-eks -l app=namespace-scaler
```

## Limpieza

Para eliminar la infraestructura creada:
```bash
# Eliminar bucket S3 (cuidado: esto elimina todos los datos)
aws s3 rb s3://namespace-scheduler-config-prod-{account-id} --force

# Eliminar GSI de DynamoDB (opcional)
aws dynamodb update-table --table-name NamespaceSchedules \
  --global-secondary-index-updates 'Delete={IndexName=estado-fecha_encendido-index}'

# Eliminar ConfigMap y Secret
kubectl delete configmap namespace-scheduler-config -n encendido-eks
kubectl delete secret notification-secrets -n encendido-eks
```

## Próximos Pasos

Una vez completada la infraestructura:
1. Continuar con la tarea 2: Implementar API básica con FastAPI
2. Verificar que las validaciones de centros de costo funcionen
3. Probar la creación de programaciones desde el frontend
4. Implementar las propiedades de corrección con tests