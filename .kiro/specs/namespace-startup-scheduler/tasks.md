# Plan de Implementación: Sistema MVP de Auto-Encendido de Namespaces

## Resumen

Implementación de un sistema web completo para programar encendido y apagado automático de namespaces en AWS EKS. Stack: Python/FastAPI + DynamoDB + frontend React + scheduler + CI/CD + monitoreo.

## Tareas

- [x] 1. Configurar infraestructura básica de AWS
  - Crear tabla DynamoDB `programaciones-namespaces` con partition key `id`
  - Crear GSI `estado-fecha_encendido-index` para consultas por estado
  - Configurar bucket S3 para archivo de configuración de centros de costo
  - Configurar permisos IAM para acceso a DynamoDB, S3 y EKS
  - _Requisitos: 10.1, 11.1_

- [x] 2. Crear Dockerfiles optimizados y seguros
  - [x] 2.1 Crear Dockerfile para controlador FastAPI
    - Build multi-stage con imagen base Python 3.11-slim
    - Usuario no-root con UID/GID específicos
    - Health checks y tini como init system
    - Instalación de kubectl para comandos EKS
    - _Requisitos: 2.1, 2.3, 2.5_
  
  - [x] 2.2 Crear Dockerfile para frontend React
    - Build multi-stage con nginx para servir archivos estáticos
    - Headers de seguridad configurados
    - Usuario no-root y permisos mínimos
    - Health checks y configuración optimizada
    - _Requisitos: 2.2, 2.3, 2.5_
  
  - [ ]* 2.3 Escribir tests de seguridad para contenedores
    - Validar que contenedores no ejecutan como root
    - Verificar superficie de ataque mínima
    - Test de vulnerabilidades con Trivy
    - _Requisitos: 2.4_

- [x] 3. Configurar Pipeline CI/CD con OIDC y GitOps
  - [x] 3.1 Crear workflow de GitHub Actions
    - Autenticación OIDC con AWS sin access keys
    - Build y push de imágenes Docker a ECR
    - Validación de manifiestos Kubernetes
    - Escaneo de seguridad con Trivy y Bandit
    - _Requisitos: 1.1, 1.2, 1.5_
  
  - [x] 3.2 Configurar validaciones automáticas
    - Linting de código Python y TypeScript
    - Validación de archivos YAML
    - Tests unitarios y de integración
    - Análisis de vulnerabilidades
    - _Requisitos: 1.3, 1.4, 1.5_
  
  - [x] 3.3 Implementar GitOps con ArgoCD
    - Actualización automática de manifiestos en Git
    - Configuración de aplicaciones ArgoCD separadas
    - Rollback automático via Git revert
    - _Requisitos: 1.6, 1.7, 13.2, 13.3_

- [ ] 4. Implementar API básica con FastAPI
  - [ ] 4.1 Crear estructura del proyecto Python con FastAPI
    - Configurar dependencias: fastapi, boto3, pydantic, uvicorn
    - Crear modelos Pydantic para Programacion
    - Configurar cliente DynamoDB con boto3
    - Implementar logging estructurado con correlation IDs
    - _Requisitos: 5.1, 10.1, 3.1, 3.2_
  
  - [ ]* 4.2 Escribir test de propiedad para validación de entrada
    - **Propiedad 1: Validación Básica de Entrada**
    - **Valida: Requisitos 5.3, 12.1, 12.2, 12.3, 12.4**
  
  - [ ] 4.3 Implementar endpoints básicos de CRUD
    - GET /programaciones - listar todas las programaciones
    - POST /programaciones - crear nueva programación con validaciones
    - DELETE /programaciones/{id} - eliminar programación
    - GET /health - health check con métricas básicas
    - _Requisitos: 5.1, 5.3, 5.5, 5.6, 3.4_
  
  - [ ]* 4.4 Escribir tests unitarios para endpoints CRUD
    - Test creación exitosa con datos válidos
    - Test rechazo por campos faltantes
    - Test rechazo por horarios inválidos
    - Test health check endpoint
    - _Requisitos: 5.3, 12.1, 12.2, 12.3, 3.4_

- [ ] 5. Implementar monitoreo y observabilidad
  - [ ] 5.1 Configurar métricas Prometheus
    - Métricas de operaciones de programación (creación, eliminación)
    - Métricas de ejecución de scheduler (éxito, fallo, tiempo)
    - Métricas de sistema (conexiones DynamoDB, EKS)
    - Endpoint /metrics para Prometheus
    - _Requisitos: 3.3, 3.5_
  
  - [ ] 5.2 Implementar logging estructurado avanzado
    - Correlation IDs para trazabilidad
    - Contexto de operación en todos los logs
    - Niveles de log configurables por ambiente
    - Formato JSON para agregación
    - _Requisitos: 3.1, 3.2_
  
  - [ ] 5.3 Crear dashboards básicos de monitoreo
    - Dashboard de estado de programaciones
    - Dashboard de métricas de ejecución
    - Dashboard de salud del sistema
    - _Requisitos: 3.6_

- [ ] 6. Implementar resilencia y manejo de errores
  - [ ] 6.1 Implementar circuit breaker para servicios externos
    - Circuit breaker para DynamoDB con estados OPEN/CLOSED/HALF_OPEN
    - Circuit breaker para EKS API
    - Configuración de umbrales y timeouts
    - _Requisitos: 4.2, 4.3_
  
  - [ ] 6.2 Implementar retry logic con backoff exponencial
    - Retry para operaciones DynamoDB
    - Retry para comandos kubectl
    - Backoff exponencial con jitter
    - _Requisitos: 4.1_
  
  - [ ] 6.3 Implementar caché local y degradación elegante
    - Caché local para configuraciones críticas
    - Modo degradado durante fallos de servicios
    - Cola de operaciones pendientes
    - _Requisitos: 4.3, 4.4, 4.5_

- [ ] 7. Implementar validaciones de negocio
  - [ ] 7.1 Crear validador de centros de costo
    - Cargar configuración desde S3 con retry
    - Implementar función obtener_centros_costo_validos(namespace)
    - Implementar función validar_centro_costo(namespace, centro_costo)
    - Cache de configuración con TTL
    - _Requisitos: 5.4, 11.1, 11.2, 11.3_
  
  - [ ]* 7.2 Escribir test de propiedad para centros de costo por namespace
    - **Propiedad 3: Centros de Costo por Namespace**
    - **Valida: Requisitos 5.4, 11.2**
  
  - [ ] 7.3 Implementar validación de límite de 5 namespaces
    - Función contar_programaciones_activas() con cache
    - Validación en endpoint POST /programaciones
    - Métricas de uso de límites
    - _Requisitos: 5.5, 6.1, 6.2_
  
  - [ ]* 7.4 Escribir test de propiedad para límite de namespaces
    - **Propiedad 2: Límite de 5 Namespaces**
    - **Valida: Requisitos 5.5, 6.1, 6.2**

- [ ] 8. Checkpoint - Validar API básica con monitoreo
  - Asegurar que todos los tests pasen
  - Verificar métricas Prometheus funcionando
  - Validar logs estructurados
  - Confirmar health checks operativos
  - Preguntar al usuario si surgen dudas

- [ ] 9. Implementar validaciones de concurrencia
  - [ ] 9.1 Crear función de detección de conflictos de namespace
    - Implementar existe_conflicto_namespace(nueva_programacion)
    - Implementar horarios_solapan(prog1, prog2)
    - Integrar validación en endpoint POST con métricas
    - _Requisitos: 5.1, 6.1_
  
  - [ ]* 9.2 Escribir test de propiedad para concurrencia de namespaces
    - **Propiedad 3.1: Concurrencia de Namespaces Diferentes**
    - **Valida: Requisitos 5.1, 5.4, 6.1**
  
  - [ ] 9.3 Agregar endpoints auxiliares
    - GET /namespaces - listar namespaces disponibles de EKS
    - GET /centros-costo/{namespace} - obtener centros de costo válidos
    - GET /metrics - métricas Prometheus
    - _Requisitos: 5.1, 5.4, 3.3_
  
  - [ ]* 9.4 Escribir tests unitarios para validaciones de concurrencia
    - Test permitir namespaces diferentes con horarios solapados
    - Test rechazar mismo namespace con horarios solapados
    - Test permitir mismo namespace con horarios no solapados
    - _Requisitos: 5.1, 6.1_

- [ ] 10. Implementar frontend web completo
  - [ ] 10.1 Crear páginas React con Material-UI
    - Página principal con lista de programaciones
    - Formulario para nueva programación con validación
    - Página de monitoreo con métricas en tiempo real
    - CSS responsive y accesible
    - _Requisitos: 9.1, 9.2, 9.5_
  
  - [ ] 10.2 Implementar integración con API
    - Cliente HTTP con manejo de errores
    - Validación del lado cliente
    - Manejo de estados de carga y error
    - Actualización en tiempo real con WebSockets
    - _Requisitos: 9.3, 9.4_
  
  - [ ] 10.3 Implementar dashboard de monitoreo
    - Gráficos de métricas de sistema
    - Estado en tiempo real de programaciones
    - Alertas visuales para errores
    - _Requisitos: 3.6_
  
  - [ ]* 10.4 Escribir tests de frontend
    - Tests unitarios de componentes React
    - Tests de integración con API
    - Tests de accesibilidad
    - _Requisitos: 9.3, 9.4_

- [ ] 11. Implementar scheduler para ejecución automática
  - [ ] 11.1 Crear función Lambda/ECS para scheduler
    - Configurar trigger cada minuto con EventBridge
    - Consultar programaciones pendientes en DynamoDB
    - Implementar lógica de encendido/apagado con kubectl
    - Integrar circuit breaker y retry logic
    - _Requisitos: 7.1, 7.4, 12.5, 4.1, 4.2_
  
  - [ ]* 11.2 Escribir test de propiedad para ejecución automática
    - **Propiedad 4: Ejecución Automática**
    - **Valida: Requisitos 7.1, 12.5**
  
  - [ ] 11.3 Implementar comandos de EKS con resilencia
    - Función encender_namespace() con retry y circuit breaker
    - Función apagar_namespace() con validación
    - Actualización de estados en DynamoDB con métricas
    - Manejo de errores con degradación elegante
    - _Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 4.1, 4.2, 4.3_
  
  - [ ]* 11.4 Escribir tests unitarios para scheduler
    - Test detección de programaciones pendientes
    - Test actualización de estados con métricas
    - Test manejo de errores de EKS
    - Test circuit breaker y retry logic
    - _Requisitos: 7.1, 7.4, 7.5, 4.1, 4.2_

- [ ] 12. Implementar persistencia y recuperación avanzada
  - [ ] 12.1 Optimizar operaciones de DynamoDB
    - Implementar paginación para listado de programaciones
    - Optimizar consultas con GSI y filtros
    - Manejo de errores con retry y circuit breaker
    - Cache de consultas frecuentes
    - _Requisitos: 10.1, 10.2, 10.3, 10.4, 4.1, 4.4_
  
  - [ ]* 12.2 Escribir test de propiedad para persistencia básica
    - **Propiedad 5: Persistencia Básica**
    - **Valida: Requisitos 5.6, 10.1**
  
  - [ ]* 12.3 Escribir tests de integración para persistencia
    - Test recuperación después de reinicio
    - Test eliminación persistente
    - Test modificación de programaciones
    - Test resilencia durante fallos de DynamoDB
    - _Requisitos: 10.2, 10.3, 10.4, 4.1, 4.4_

- [x] 13. Configurar ArgoCD y despliegue GitOps
  - [x] 13.1 Crear aplicaciones ArgoCD separadas
    - Aplicación ArgoCD para backend con manifiestos en manifests/backend/
    - Aplicación ArgoCD para frontend con manifiestos en manifests/frontend/
    - Bootstrap application usando App of Apps pattern
    - Configuración de sync automático y self-healing
    - _Requisitos: 13.1, 13.2, 13.5_
  
  - [x] 13.2 Configurar manifiestos Kubernetes separados
    - Manifiestos de backend: deployment, service, servicemonitor
    - Manifiestos de frontend: deployment, service, ingress
    - Variables de imagen que serán reemplazadas por CI/CD
    - _Requisitos: 13.2, 13.5_
  
  - [x] 13.3 Configurar monitoreo y health checks en ArgoCD
    - Health checks automáticos de aplicaciones
    - Rollback automático en caso de fallo
    - Visibilidad de estado en UI de ArgoCD
    - _Requisitos: 13.4, 13.6, 13.7_

- [ ] 14. Configurar despliegue completo en AWS
  - [ ] 14.1 Configurar archivo de centros de costo en S3
    - Crear archivo config.json con mapeo namespace-centros
    - Subir a bucket S3 con versionado
    - Configurar permisos de lectura con IAM
    - Script de actualización automática
    - _Requisitos: 11.1, 11.2, 11.3_
  
  - [ ] 14.2 Configurar alertas y monitoreo
    - Alertas Prometheus para fallos críticos
    - Dashboards Grafana para visualización
    - Logs centralizados con CloudWatch
    - _Requisitos: 3.3, 3.6_

- [ ] 15. Checkpoint final - Validar sistema completo con ArgoCD
  - Asegurar que todos los tests pasen
  - Verificar pipeline CI/CD funcionando con GitOps
  - Validar aplicaciones ArgoCD sincronizando correctamente
  - Confirmar rollback automático funcionando
  - Preguntar al usuario si surgen dudas

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia los requisitos específicos que implementa
- Los checkpoints aseguran validación incremental con monitoreo
- Los tests de propiedades validan las 5 propiedades principales del diseño
- El sistema incluye resilencia, monitoreo, CI/CD y GitOps con ArgoCD para producción
- Secuencia optimizada: **CI/CD → ArgoCD → Infraestructura → Monitoreo → Resilencia → API → Validaciones → Frontend → Scheduler → Despliegue**

## Orden de Requisitos Actualizado

1. **Requisitos 1-4**: CI/CD, Infraestructura, Monitoreo, Resilencia (Base técnica)
2. **Requisitos 5-8**: Funcionalidad core del sistema (API y lógica de negocio)
3. **Requisitos 9-12**: Interfaz, persistencia y validaciones (Completitud del sistema)
4. **Requisitos 13-14**: GitOps con ArgoCD y restricciones operacionales (Despliegue y operación)