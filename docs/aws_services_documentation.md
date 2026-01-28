# Documentación de Servicios AWS

*Generado automáticamente el 2026-01-27 22:18:25*

## Resumen de Servicios

El sistema de apagado automático de namespaces utiliza los siguientes servicios AWS optimizados para costo y seguridad:


## Amazon Elastic Container Registry (ECR)

**Propósito**: Almacenamiento de imágenes Docker

**Uso en el Sistema**: Repositorios para controller y frontend

### 💰 Optimización de Costos
- Lifecycle policies para eliminar imágenes antiguas (7 días)
- Compresión de imágenes con multi-stage builds
- Escaneo de vulnerabilidades automático

### 🔧 Mejores Prácticas
- Usar tags inmutables
- Implementar escaneo de vulnerabilidades
- Configurar políticas de ciclo de vida
- Usar OIDC en lugar de access keys

## Amazon DynamoDB (DynamoDB)

**Propósito**: Base de datos NoSQL para schedules

**Uso en el Sistema**: Tabla NamespaceSchedules con modelo pay-per-request

### 💰 Optimización de Costos
- Modelo pay-per-request para cargas variables
- Point-in-time recovery habilitado
- Consultas eficientes con partition key

### 🔧 Mejores Prácticas
- Usar partition key eficiente (namespace)
- Implementar retry con exponential backoff
- Habilitar encryption at rest
- Configurar backup automático

## Amazon CloudWatch (CloudWatch)

**Propósito**: Monitoreo y logging

**Uso en el Sistema**: Logs del controller y métricas personalizadas

### 💰 Optimización de Costos
- Retención de logs configurada (30 días)
- Métricas personalizadas solo las necesarias
- Log groups organizados por componente

### 🔧 Mejores Prácticas
- Usar structured logging
- Configurar alertas basadas en métricas
- Implementar dashboards personalizados
- Usar log insights para análisis

## Amazon Simple Notification Service (SNS)

**Propósito**: Notificaciones y alertas

**Uso en el Sistema**: Entrega de alertas a Slack y email

### 💰 Optimización de Costos
- Filtros de mensajes para reducir volumen
- Batching de notificaciones cuando sea posible
- Uso eficiente de topics

### 🔧 Mejores Prácticas
- Configurar dead letter queues
- Implementar retry policies
- Usar filtros de mensajes
- Monitorear delivery failures

## AWS Identity and Access Management (IAM)

**Propósito**: Autenticación y autorización

**Uso en el Sistema**: OIDC provider y roles con permisos mínimos

### 💰 Optimización de Costos
- Sin costos adicionales
- Elimina necesidad de access keys
- Tokens de corta duración

### 🔧 Mejores Prácticas
- Principio de menor privilegio
- Usar OIDC en lugar de access keys
- Roles específicos por servicio
- Auditoría regular de permisos

## 💰 Estimación de Costos Mensual

| Servicio | Uso Estimado | Costo Mensual |
|----------|--------------|---------------|
| **ECR** | 2 repositorios, 1GB storage, lifecycle policies | $0.10 |
| **DynamoDB** | 1 tabla, pay-per-request, ~1000 ops/día | $1.25 |
| **CloudWatch** | Logs (5GB/mes), métricas personalizadas | $2.50 |
| **SNS** | 1,000 notificaciones/mes | $0.50 |
| **IAM/STS** | OIDC provider, roles, tokens | $0.00 |
| **Total Estimado** | | **~$4.35/mes** |

*Costos pueden variar según uso real y región AWS*

## 🔒 Consideraciones de Seguridad

### Autenticación
- **OIDC Provider**: Elimina necesidad de access keys de larga duración
- **Tokens temporales**: Duración máxima de 15 minutos
- **Principio de menor privilegio**: Cada rol tiene permisos mínimos necesarios

### Cifrado
- **DynamoDB**: Encryption at rest habilitado por defecto
- **ECR**: Imágenes cifradas en reposo
- **CloudWatch**: Logs cifrados en tránsito y reposo

### Auditoría
- **CloudTrail**: Registro de todas las llamadas API
- **CloudWatch Logs**: Logs estructurados para auditoría
- **Access Analyzer**: Análisis de permisos y accesos

## 📊 Monitoreo y Alertas

### Métricas Clave
- `namespace_scaling_operations_total`: Operaciones de escalado
- `controller_errors_total`: Errores del controlador
- `dynamodb_consumed_capacity`: Capacidad consumida de DynamoDB
- `ecr_repository_size`: Tamaño de repositorios ECR

### Alertas Configuradas
- **Controller Down**: Si el controlador no responde por 5 minutos
- **High Error Rate**: Si la tasa de errores supera 10% por 2 minutos
- **DynamoDB Throttling**: Si hay throttling en DynamoDB
- **ECR Storage Limit**: Si el almacenamiento ECR supera límites

## 🚀 Próximos Pasos

### Optimizaciones Futuras
1. **Implementar AWS Cost Explorer API** para tracking automático de costos
2. **Configurar AWS Config** para compliance automático
3. **Añadir AWS X-Ray** para tracing distribuido
4. **Implementar AWS Secrets Manager** para gestión de secretos

### Escalabilidad
1. **Multi-región**: Despliegue en múltiples regiones AWS
2. **Cross-account**: Soporte para múltiples cuentas AWS
3. **Auto-scaling**: Escalado automático del controlador basado en carga
4. **Disaster Recovery**: Plan de recuperación ante desastres

---

*Esta documentación se actualiza automáticamente con cada despliegue del sistema.*
