# Namespace Scheduler - Lista de Tareas

## 1. Infraestructura y Configuración Base

### 1.1 Configurar repositorios ECR
- [x] Crear repositorio ECR para frontend
- [x] Crear repositorio ECR para backend
- [x] Configurar políticas de acceso para GitHub Actions
- [x] Actualizar scripts de build para usar ECR

### 1.2 Configurar GitHub Actions
- [x] Crear workflow para build del frontend
- [x] Crear workflow para build del backend
- [x] Configurar secrets de AWS en GitHub
- [x] Configurar push automático a ECR
- [x] Configurar actualización de tags en manifiestos
### 1.3 Configurar DynamoDB
- [x] Crear tabla `task-scheduler-logs` con índices apropiados
- [x] Crear tabla `cost-center-permissions` para validación
- [x] Configurar IAM roles para acceso desde EKS
- [x] Poblar tabla de permisos con centros de costo iniciales
- [x] Probar conectividad desde kubectl-runner

### 1.4 Arreglar RBAC de Kubernetes
- [x] Revisar y actualizar ClusterRole para kubectl-runner
- [x] Agregar permisos para scale de deployments/statefulsets
- [x] Configurar ServiceAccount correctamente
- [x] Probar permisos con comandos kubectl
- [x] Documentar permisos mínimos requeridos

## 2. Backend - Correcciones y Mejoras

### 2.1 Completar validación de centros de costo y auditoría
- [x] Implementar endpoint para validar centro de costo
- [x] Agregar validación en activación de namespaces
- [x] Agregar validación en desactivación de namespaces
- [x] Agregar validación en creación de tareas programadas
- [x] Implementar cache de permisos para mejor performance
- [x] Agregar logs de auditoría para validaciones
- [x] Implementar captura de usuario solicitante en todas las operaciones
- [x] Implementar captura de cluster name en todas las operaciones
- [x] Agregar endpoints para consultas de auditoría por usuario y cluster

### 2.2 Arreglar gestión de namespaces
- [x] Corregir lógica de conteo de namespaces activos
- [x] Implementar detección correcta de horarios no laborales
- [x] Arreglar escalado de recursos (deployments, statefulsets)
- [x] Agregar manejo de errores robusto
- [x] Implementar rollback en caso de fallas

### 2.3 Completar sistema de tareas programadas
- [x] Arreglar cálculo de próxima ejecución con croniter
- [x] Implementar ejecución de tareas en background threads
- [x] Agregar manejo de timeouts y reintentos
- [x] Implementar persistencia de estado de tareas
- [x] Agregar logs detallados de ejecución

## 3. Frontend - Correcciones y Mejoras

### 3.1 Arreglar conexión con Backend
- [x] Corregir llamadas API que fallan (fetch errors)
- [x] Implementar manejo de errores en todas las llamadas
- [x] Agregar indicadores de carga (loading spinners)
- [x] Implementar retry automático para llamadas fallidas
- [x] Agregar validación de respuestas del servidor

### 3.2 Completar interfaz de gestión de namespaces
- [x] Arreglar carga de lista de namespaces
- [x] Agregar estados de carga y error en selectores de namespaces
- [x] Implementar actualización en tiempo real del estado
- [x] Agregar validación de centro de costo antes de operaciones
- [x] Mejorar feedback visual de operaciones exitosas/fallidas
- [x] Implementar confirmación para operaciones críticas
  - [x] Modal de confirmación para activación de namespaces
  - [x] Modal de advertencia para desactivación de namespaces
  - [x] Integración con Bootstrap Modal
  - [x] Manejo de eventos de confirmación/cancelación

### 3.3 Completar interfaz de programación de tareas
- [x] Arreglar integración con FullCalendar
- [x] Implementar carga de tareas con formateo consistente
- [x] Agregar código de colores por estado de tarea
- [x] Implementar formulario completo de creación de tareas
- [x] Agregar validación de expresiones cron
- [x] Implementar edición y eliminación de tareas
- [x] Agregar vista de historial de ejecuciones

### 3.4 Mejorar dashboard y monitoreo con capacidades de auditoría
- [ ] Arreglar cálculo de estadísticas en tiempo real
- [ ] Implementar gráficos de uso de namespaces
- [ ] Agregar alertas visuales para límites excedidos
- [ ] Implementar filtros en logs por fecha, centro de costo, cluster y usuario
- [ ] Agregar exportación de reportes de auditoría
- [ ] Implementar vista de actividad por usuario solicitante
- [ ] Implementar vista de actividad por cluster
- [ ] Agregar reportes de trazabilidad de operaciones

## 4. Despliegue y CI/CD

### 4.1 Configurar ArgoCD
- [x] Crear ArgoCD Application para el proyecto
- [x] Configurar sincronización automática
- [ ] Configurar health checks apropiados
- [ ] Implementar rollback automático en caso de fallas
- [ ] Documentar proceso de despliegue

### 4.2 Actualizar manifiestos de Kubernetes
- [x] Revisar y actualizar deployment del backend
- [x] Revisar y actualizar deployment del frontend
- [ ] Configurar ingress con TLS
- [ ] Agregar ConfigMaps para configuración
- [ ] Configurar Secrets para credenciales

### 4.3 Configurar monitoreo
- [ ] Agregar health checks a ambos servicios
- [ ] Configurar logging estructurado
- [ ] Implementar métricas de Prometheus (opcional)
- [ ] Configurar alertas básicas
- [ ] Documentar troubleshooting

## 5. Validación y Testing

### 5.1 Testing de integración
- [ ] Probar flujo completo de activación/desactivación
- [ ] Probar creación y ejecución de tareas programadas
- [ ] Probar validación de centros de costo
- [ ] Probar límites de horarios no laborales
- [ ] Probar manejo de errores y recuperación

### 5.2 Testing de despliegue
- [ ] Probar despliegue completo con ArgoCD
- [ ] Probar build automático con GitHub Actions
- [ ] Probar rollback de versiones
- [ ] Probar configuración de RBAC en cluster limpio
- [ ] Documentar proceso de testing

## 6. Documentación y Finalización

### 6.1 Documentación técnica
- [ ] Documentar API endpoints con ejemplos
- [ ] Crear guía de instalación paso a paso
- [ ] Documentar configuración de variables de entorno
- [ ] Crear troubleshooting guide
- [ ] Documentar arquitectura y decisiones técnicas

### 6.2 Documentación de usuario
- [ ] Crear manual de usuario para la interfaz web
- [ ] Documentar sintaxis de expresiones cron
- [ ] Crear ejemplos de uso común
- [ ] Documentar centros de costo y permisos
- [ ] Crear FAQ de problemas comunes

## Notas de Implementación

### Configuración de Imágenes
- Los manifiestos base usan nombres genéricos de imágenes (`task-scheduler-frontend:latest`)
- El overlay de producción reemplaza estos nombres con URLs completas de ECR usando Kustomize
- GitHub Actions debe actualizar los tags en `manifests/overlays/production/kustomization.yaml`
- Ver documentación detallada en `docs/deployment-configuration.md`

### Prioridad Alta (MVP Core)
- Tareas 1.1, 1.2, 1.3, 1.4 (Infraestructura base)
- Tareas 2.1, 2.2 (Backend core)
- Tareas 3.1, 3.2 (Frontend core)
- Tarea 4.1 (ArgoCD)

### Prioridad Media (MVP Extended)
- Tareas 2.3, 3.3, 3.4 (Funcionalidades avanzadas)
- Tareas 4.2, 4.3 (Configuración completa)
- Tarea 5.1 (Testing básico)

### Prioridad Baja (Post-MVP)
- Tarea 5.2 (Testing avanzado)
- Tareas 6.1, 6.2 (Documentación completa)

### Dependencias Críticas
- 1.1 → 1.2 (ECR debe existir antes de GitHub Actions)
- 1.3 → 2.1 (DynamoDB debe estar listo para validaciones)
- 1.4 → 2.2 (RBAC debe funcionar para operaciones de namespaces)
- 2.x → 3.x (Backend debe estar estable antes de frontend)
- 4.1 requiere que 1.2 y 4.2 estén completos