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

### 2.4 Implementar API para Vista Semanal
- [x] Crear endpoint /api/weekly-schedule/{week_start_date}
  - [x] Obtener todas las tareas programadas para una semana
  - [x] Procesar datos de croniter para generar slots de tiempo
  - [x] Formatear respuesta para consumo del frontend
  - [x] Implementar cache de datos semanales
- [ ] Crear endpoint /api/holidays/{year}
  - [ ] Integrar con API de festivos colombianos
  - [ ] Implementar cache de festivos por año
  - [ ] Manejar festivos fijos y móviles
- [ ] Crear endpoint /api/weekly-report/{week_start_date}
  - [ ] Calcular horas de uso por namespace y centro de costo
  - [ ] Generar estadísticas de eficiencia
  - [ ] Soportar exportación en diferentes formatos
- [ ] Crear endpoint /api/namespace-usage/{namespace_id}
  - [ ] Obtener detalles de uso para namespace específico
  - [ ] Calcular horas programadas vs ejecutadas
  - [ ] Incluir información de centro de costo

### 2.5 Optimizar Performance para Vista Semanal
- [ ] Implementar cache Redis para datos semanales (opcional)
- [ ] Optimizar queries a DynamoDB para rangos de fechas
- [ ] Implementar paginación para datos grandes
- [ ] Agregar índices apropiados para consultas semanales
- [ ] Implementar compresión de respuestas para datos grandes

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

### 3.5 Implementar Vista Semanal del Dashboard
- [x] Crear componente WeeklyDashboard principal
  - [x] Diseñar estructura HTML para grilla 7x24
  - [x] Implementar CSS responsivo para la grilla semanal
  - [x] Integrar con la clase TaskScheduler existente
- [x] Implementar WeeklyGrid component
  - [x] Renderizar grilla de 7 días x 24 horas
  - [x] Mostrar namespaces programados en cada slot de tiempo
  - [x] Aplicar colores diferenciados por namespace/centro de costo
  - [x] Conectar visualmente slots continuos del mismo namespace
- [x] Crear NamespaceScheduleService
  - [x] Implementar obtención de datos de programación semanal
  - [x] Procesar y formatear datos para la vista de grilla
  - [x] Implementar cache de datos semanales
  - [x] Manejar estados de carga y errores

### 3.6 Implementar Navegación Temporal
- [x] Crear NavigationControls component
  - [x] Botones para semana anterior/siguiente
  - [x] Botón "Semana Actual" para reset rápido
  - [x] Mostrar rango de fechas de la semana actual
- [x] Implementar lógica de navegación
  - [x] Calcular fechas de inicio/fin de semana
  - [x] Actualizar datos al cambiar de semana
  - [x] Mantener estado de semana seleccionada
  - [x] Implementar navegación con teclado (opcional)

### 3.7 Integrar Marcado de Festivos Colombianos
- [ ] Crear HolidayService component
  - [ ] Implementar obtención de festivos colombianos
  - [ ] Cache de datos de festivos por año
  - [ ] Identificar si una fecha es festivo
- [ ] Implementar marcado visual de festivos
  - [ ] Aplicar estilos diferenciados a días festivos
  - [ ] Mostrar tooltips con información del festivo
  - [ ] Mantener funcionalidad normal en días festivos
- [ ] Integrar con vista semanal
  - [ ] Marcar columnas de días festivos
  - [ ] Actualizar automáticamente para el año actual

### 3.8 Implementar Sistema de Reportes Semanales
- [ ] Crear ReportService component
  - [ ] Calcular horas de uso por namespace
  - [ ] Agrupar datos por centro de costo
  - [ ] Generar totales y estadísticas
- [ ] Implementar interfaz de reportes
  - [ ] Tabla de reporte semanal en la interfaz
  - [ ] Exportación a CSV
  - [ ] Exportación a Excel (opcional)
  - [ ] Filtros por semana específica
- [ ] Integrar con vista semanal
  - [ ] Botón para generar reporte de semana actual
  - [ ] Mostrar resumen de horas en la vista
  - [ ] Enlazar datos de grilla con reporte

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

### 5.2 Testing de Vista Semanal
- [ ] Probar carga de datos semanales
  - [ ] Verificar datos correctos para semana actual
  - [ ] Probar navegación entre semanas
  - [ ] Validar cache de datos semanales
- [ ] Probar marcado de festivos
  - [ ] Verificar identificación correcta de festivos colombianos
  - [ ] Probar marcado visual en la grilla
  - [ ] Validar tooltips de información de festivos
- [ ] Probar generación de reportes
  - [ ] Verificar cálculos de horas por namespace
  - [ ] Probar agrupación por centro de costo
  - [ ] Validar exportación de reportes
- [ ] Probar responsividad
  - [ ] Verificar funcionamiento en móviles
  - [ ] Probar scroll horizontal en pantallas pequeñas
  - [ ] Validar legibilidad en diferentes tamaños

### 5.3 Testing de despliegue
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
- [ ] Documentar nuevos endpoints de vista semanal
- [ ] Crear guía de integración con API de festivos colombianos

### 6.2 Documentación de usuario
- [ ] Crear manual de usuario para la interfaz web
- [ ] Documentar sintaxis de expresiones cron
- [ ] Crear ejemplos de uso común
- [ ] Documentar centros de costo y permisos
- [ ] Crear FAQ de problemas comunes
- [ ] Documentar uso de la vista semanal
- [ ] Crear guía de interpretación de reportes semanales

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

### Prioridad Alta - Vista Semanal (Nueva Funcionalidad Principal)
- Tarea 2.4 (API para vista semanal)
- Tareas 3.5, 3.6 (Componentes principales de vista semanal)
- Tareas 3.7, 3.8 (Festivos colombianos y reportes semanales)
- Tarea 5.2 (Testing de vista semanal)

### Prioridad Media - Vista Semanal (Optimizaciones)
- Tarea 2.5 (Optimizaciones de performance)
- Documentación actualizada (6.1, 6.2)

### Prioridad Baja (Post-MVP)
- Tarea 5.3 (Testing avanzado)
- Documentación completa restante

### Dependencias Críticas
- 1.1 → 1.2 (ECR debe existir antes de GitHub Actions)
- 1.3 → 2.1 (DynamoDB debe estar listo para validaciones)
- 1.4 → 2.2 (RBAC debe funcionar para operaciones de namespaces)
- 2.x → 3.x (Backend debe estar estable antes de frontend)
- 4.1 requiere que 1.2 y 4.2 estén completos

### Dependencias Vista Semanal
- 2.4 → 3.5 (API de vista semanal debe estar lista antes del frontend)
- 3.5 → 3.6 (Componente principal debe existir antes de navegación)
- 2.4 → 3.7 (API de festivos debe estar lista antes del marcado)
- 3.5, 2.4 → 3.8 (Vista semanal y API deben estar listas para reportes)
- 3.5, 3.6, 3.7, 3.8 → 5.2 (Todos los componentes deben estar completos para testing)