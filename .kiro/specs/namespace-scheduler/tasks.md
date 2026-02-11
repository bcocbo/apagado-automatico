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
- [ ] Crear tabla `task-scheduler-logs` con índices apropiados
- [ ] Crear tabla `cost-center-permissions` para validación
- [ ] Configurar IAM roles para acceso desde EKS
- [ ] Poblar tabla de permisos con centros de costo iniciales
- [ ] Probar conectividad desde kubectl-runner

### 1.4 Arreglar RBAC de Kubernetes
- [ ] Revisar y actualizar ClusterRole para kubectl-runner
- [ ] Agregar permisos para scale de deployments/statefulsets
- [ ] Configurar ServiceAccount correctamente
- [ ] Probar permisos con comandos kubectl
- [ ] Documentar permisos mínimos requeridos

## 2. Backend - Correcciones y Mejoras

### 2.1 Completar validación de centros de costo
- [ ] Implementar endpoint para validar centro de costo
- [ ] Agregar validación en activación/desactivación de namespaces
- [ ] Agregar validación en creación de tareas programadas
- [ ] Implementar cache de permisos para mejor performance
- [ ] Agregar logs de auditoría para validaciones

### 2.2 Arreglar gestión de namespaces
- [ ] Corregir lógica de conteo de namespaces activos
- [ ] Implementar detección correcta de horarios no laborales
- [ ] Arreglar escalado de recursos (deployments, statefulsets)
- [ ] Agregar manejo de errores robusto
- [ ] Implementar rollback en caso de fallas

### 2.3 Completar sistema de tareas programadas
- [ ] Arreglar cálculo de próxima ejecución con croniter
- [ ] Implementar ejecución de tareas en background threads
- [ ] Agregar manejo de timeouts y reintentos
- [ ] Implementar persistencia de estado de tareas
- [ ] Agregar logs detallados de ejecución

## 3. Frontend - Correcciones y Mejoras

### 3.1 Arreglar conexión con Backend
- [ ] Corregir llamadas API que fallan (fetch errors)
- [ ] Implementar manejo de errores en todas las llamadas
- [ ] Agregar indicadores de carga (loading spinners)
- [ ] Implementar retry automático para llamadas fallidas
- [ ] Agregar validación de respuestas del servidor

### 3.2 Completar interfaz de gestión de namespaces
- [ ] Arreglar carga de lista de namespaces
- [ ] Implementar actualización en tiempo real del estado
- [ ] Agregar validación de centro de costo antes de operaciones
- [ ] Mejorar feedback visual de operaciones exitosas/fallidas
- [ ] Implementar confirmación para operaciones críticas

### 3.3 Completar interfaz de programación de tareas
- [ ] Arreglar integración con FullCalendar
- [ ] Implementar formulario completo de creación de tareas
- [ ] Agregar validación de expresiones cron
- [ ] Implementar edición y eliminación de tareas
- [ ] Agregar vista de historial de ejecuciones

### 3.4 Mejorar dashboard y monitoreo
- [ ] Arreglar cálculo de estadísticas en tiempo real
- [ ] Implementar gráficos de uso de namespaces
- [ ] Agregar alertas visuales para límites excedidos
- [ ] Implementar filtros en logs por fecha y centro de costo
- [ ] Agregar exportación de reportes

## 4. Despliegue y CI/CD

### 4.1 Configurar ArgoCD
- [ ] Crear ArgoCD Application para el proyecto
- [ ] Configurar sincronización automática
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