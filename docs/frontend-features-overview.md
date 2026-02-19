# Frontend - Resumen de Funcionalidades

## Descripción General

El frontend del Task Scheduler es una aplicación web de página única (SPA) construida con HTML, CSS (Bootstrap 5), y JavaScript vanilla. Proporciona una interfaz intuitiva para gestionar namespaces de Kubernetes y programar tareas automatizadas.

## Arquitectura

### Estructura de Archivos

```
frontend/
├── src/
│   ├── index.html          # Estructura HTML principal
│   ├── app.js              # Lógica principal de la aplicación
│   ├── api.js              # Cliente API para comunicación con backend
│   ├── notifications.js    # Sistema de notificaciones
│   ├── loading.js          # Indicadores de carga
│   └── styles.css          # Estilos personalizados
├── nginx.conf              # Configuración del servidor web
└── Dockerfile              # Imagen Docker para despliegue
```

### Tecnologías Utilizadas

- **Bootstrap 5**: Framework CSS para diseño responsive
- **FullCalendar 6**: Librería para calendario de tareas
- **Font Awesome**: Iconos
- **Fetch API**: Comunicación con backend
- **Nginx**: Servidor web para producción

## Secciones Principales

### 1. Dashboard

Panel de control que muestra estadísticas en tiempo real:

- **Tareas Activas**: Número de tareas programadas actualmente activas
- **Completadas Hoy**: Tareas ejecutadas exitosamente en el día actual
- **Pendientes**: Tareas en cola esperando ejecución
- **Fallidas**: Tareas que fallaron en su última ejecución

### 2. Programador (Scheduler)

Sección principal para gestión de tareas y namespaces.

#### 2.1 Calendario de Tareas

- Visualización de tareas programadas en formato calendario
- Integración con FullCalendar para vista mensual/semanal/diaria
- Permite crear, editar y eliminar tareas
- Soporte para campos de calendario (`start` y `allDay`) para mejor visualización temporal
- Modal de detalles mejorado para cada tarea con:
  - Información completa con badges y formato visual
  - Estadísticas de ejecución (total, exitosas, fallidas)
  - Próxima ejecución con tiempo relativo
  - Historial de las últimas 10 ejecuciones
  - Botones de acción (Editar/Eliminar)

**Mejoras de Carga de Tareas:**
- Limpieza automática de eventos existentes antes de cargar nuevas tareas
- Formateo consistente de tareas para FullCalendar con `addTaskToCalendar()`
- Código de colores por estado de tarea:
  - Amarillo (#ffc107): Tareas pendientes
  - Azul (#17a2b8): Tareas en ejecución
  - Verde (#28a745): Tareas completadas
  - Rojo (#dc3545): Tareas fallidas
- Propiedades extendidas incluyen: status, operation_type, namespace, cost_center, schedule, run_count, success_count, error_count, next_run
- Fallback a localStorage si la carga desde API falla

#### 2.2 Formulario de Nueva Tarea

Permite crear tareas programadas con los siguientes campos:

- **Nombre de la Tarea**: Identificador descriptivo
- **Descripción**: Campo opcional para detalles adicionales
- **Tipo de Tarea**: 
  - Comando kubectl personalizado
  - Activar namespace
  - Desactivar namespace
- **Comando kubectl**: Campo de texto para comandos personalizados
- **Programación (Cron)**: Expresión cron para definir frecuencia
- **Namespace**: Selector de namespace objetivo
- **Centro de Costo**: Selector de centro de costo para validación
- **Fecha de Inicio**: Campo opcional para especificar cuándo debe comenzar la tarea (para visualización en calendario)
- **Todo el Día**: Checkbox opcional para marcar tareas que duran todo el día (para visualización en calendario)

**Mejoras de UX Implementadas:**
- Validación de centro de costo antes de crear la tarea
- Botón deshabilitado durante validación y creación
- Estados de carga con spinners y texto descriptivo:
  - "Validando..." durante validación de centro de costo
  - "Creando tarea..." durante creación de la tarea
- Manejo robusto de errores con try-catch-finally
- Limpieza automática del formulario después de creación exitosa
- Feedback visual con indicadores de validación (válido/inválido)
- Garantía de rehabilitación del botón incluso si ocurre un error
- **Validación en tiempo real de expresiones cron** ✨ NUEVO:
  - Validación automática mientras el usuario escribe
  - Soporte para sintaxis estándar de 5 campos: `minuto hora día mes día-semana`
  - Validación de valores individuales, rangos (1-5), listas (1,3,5), pasos (*/5) y comodines (*)
  - Descripción en lenguaje natural de la expresión (ej: "Se ejecutará cada 5 minutos")
  - Feedback visual inmediato con clases Bootstrap (is-valid/is-invalid)
  - Mensajes de error específicos indicando qué campo es inválido y por qué
  - Iconos de Font Awesome para indicar estado (✓ válido, ✗ inválido)

#### 2.3 Gestión de Namespaces

Panel para activar/desactivar namespaces manualmente:

- **Contador de Namespaces Activos**: Muestra X/5 namespaces activos
- **Barra de Progreso**: Visualización del límite de namespaces
- **Estado de Horario**: Indica si es horario laboral o no laboral
- **Selector de Namespace**: Dropdown con todos los namespaces disponibles
- **Selector de Centro de Costo**: Para validación de permisos
- **Botones de Acción**: Activar y Desactivar namespace

**Mejoras de UX Implementadas:**
- Los botones se deshabilitan durante operaciones para prevenir clics múltiples
- Spinners de carga aparecen en los botones durante el procesamiento
- Feedback visual inmediato con animaciones de éxito/error
- Manejo robusto de errores con mensajes descriptivos
- Actualización automática de la lista de estado después de operaciones
- Validación de centro de costo integrada en el flujo
- **Diálogos de confirmación para operaciones críticas** (activar/desactivar namespaces)
  - Modal de confirmación antes de activar namespace con detalles de namespace y centro de costo
  - Modal de advertencia antes de desactivar namespace con alerta sobre escalado a 0 réplicas
  - Botones contextuales según el tipo de operación (éxito/advertencia)

#### 2.4 Lista de Estado de Namespaces ✨ NUEVO

Panel visual que muestra el estado en tiempo real de todos los namespaces:

**Características:**
- Lista scrollable con todos los namespaces de usuario
- Badge de estado (Activo/Inactivo) con código de colores
- Información de recursos por namespace:
  - Número de pods activos
  - Cantidad de deployments
  - Cantidad de statefulsets
- Filtrado automático de namespaces del sistema
- Botón de actualización manual
- Timestamp de última actualización
- Actualización automática después de operaciones

**Implementación:**
- Función: `updateNamespaceStatusList()`
- Integración con: `loadNamespacesStatus()`, `activateNamespace()`, `deactivateNamespace()`
- Endpoint: `/api/namespaces/status`

Ver documentación detallada en: [frontend-namespace-status-list.md](./frontend-namespace-status-list.md)

### 3. Logs

Sección para visualizar el historial de ejecuciones:

- Tabla de logs con información detallada
- Filtros por fecha, centro de costo, cluster y usuario
- Botón de actualización manual
- Exportación de reportes (planificado)

## Funcionalidades Implementadas

### ✅ UI/UX Improvements - Operaciones de Namespace

**Prevención de Operaciones Concurrentes:**
- Los botones de Activar/Desactivar se deshabilitan durante operaciones
- Texto del botón cambia a "Procesando..." con spinner animado
- Previene múltiples clics accidentales y operaciones concurrentes

**Feedback Visual Mejorado:**
- Spinners de Bootstrap integrados en botones durante operaciones
- Animaciones de éxito/error en la lista de namespaces
- Clases CSS `operation-success` y `operation-error` aplicadas temporalmente
- Logs en consola con símbolos visuales (✓ para éxito, ✗ para error)

**Manejo de Errores Robusto:**
- Estructura try-catch-finally en todas las operaciones
- Garantiza que los botones se rehabiliten incluso si ocurre un error
- Mensajes de error descriptivos para el usuario
- Logging detallado para debugging

**Flujo de Operación:**
1. Usuario hace clic en Activar/Desactivar
2. Validación inicial de campos requeridos (namespace y centro de costo)
3. **Modal de confirmación aparece con detalles de la operación**
4. Si el usuario confirma, los botones se deshabilitan inmediatamente
5. Validación de centro de costo en el backend
6. Ejecución de operación con feedback visual
7. Actualización automática de lista de estado
8. Rehabilitación de botones (garantizada por finally)

### ✅ Gestión de Namespaces

- [x] Carga dinámica de lista de namespaces desde el backend
- [x] Activación manual de namespaces con validación de centro de costo
- [x] Desactivación manual de namespaces
- [x] Visualización de límite de namespaces activos (5 en horario no laboral)
- [x] Detección de horario laboral vs no laboral
- [x] Estados de carga y error en selectores
- [x] Actualización en tiempo real del estado de namespaces
- [x] Lista visual de estado de todos los namespaces
- [x] Botones deshabilitados durante operaciones en progreso
- [x] Indicadores visuales de carga con spinners en botones
- [x] Feedback visual de éxito/error en operaciones
- [x] Manejo robusto de errores con try-catch-finally
- [x] Diálogos de confirmación para operaciones críticas (activar/desactivar)

### ✅ Sistema de Notificaciones

- [x] Notificaciones toast para operaciones exitosas
- [x] Alertas de error con mensajes descriptivos
- [x] Indicadores de carga durante operaciones asíncronas
- [x] Validación de respuestas del servidor

### ✅ Manejo de Errores

- [x] Retry automático para llamadas API fallidas
- [x] Mensajes de error amigables para el usuario
- [x] Logging de errores en consola para debugging
- [x] Fallback para datos no disponibles

### ✅ Calendario de Tareas

- [x] Carga de tareas desde API con limpieza automática de eventos previos
- [x] Formateo consistente de tareas para FullCalendar
- [x] Código de colores por estado de tarea (pending, running, completed, failed)
- [x] Propiedades extendidas para información detallada de tareas
- [x] Fallback a localStorage para resiliencia

### ✅ Creación de Tareas

- [x] Validación de centro de costo antes de crear tarea
- [x] Botón deshabilitado durante operaciones en progreso
- [x] Estados de carga con spinners y texto descriptivo
- [x] Manejo robusto de errores con try-catch-finally
- [x] Limpieza automática del formulario después de creación exitosa
- [x] Feedback visual con indicadores de validación
- [x] Soporte para campo de descripción opcional
- [x] Garantía de rehabilitación del botón incluso si ocurre un error
- [x] **Campos de calendario integrados** ✨ NUEVO
  - Campo `start` opcional para especificar fecha/hora de inicio de la tarea
  - Campo `allDay` opcional para marcar tareas de todo el día
  - Mejora la visualización y organización en el calendario FullCalendar
- [x] **Validación en tiempo real de expresiones cron** ✨ NUEVO
  - Validación automática mientras el usuario escribe (eventos `input` y `blur`)
  - Soporte completo para sintaxis cron de 5 campos (minuto hora día mes día-semana)
  - Validación de rangos, listas, pasos (*/n) y comodines (*)
  - Descripción en lenguaje natural de la expresión cron
  - Feedback visual con clases Bootstrap (is-valid/is-invalid)
  - Mensajes de error específicos por campo inválido
  - Iconos de estado (check/exclamation) para mejor UX

### ✅ Edición y Eliminación de Tareas

- [x] **Edición de tareas existentes** ✨ NUEVO
  - Modal de edición con formulario pre-poblado
  - Actualización de todos los campos de la tarea (nombre, descripción, tipo, namespace, programación, centro de costo)
  - Soporte para cambio de tipo de tarea con visibilidad dinámica del campo de comando
  - Actualización automática del calendario después de guardar cambios
  - Validación y manejo de errores durante la actualización
- [x] **Eliminación de tareas**
  - Diálogo de confirmación antes de eliminar
  - Eliminación desde el modal de detalles de tarea
  - Actualización automática del calendario y estadísticas

### ✅ Vista de Historial de Ejecuciones ✨ NUEVO

- [x] **Modal de detalles de tarea mejorado**
  - Información completa de la tarea con badges y formato mejorado
  - Sección de estadísticas con totales de ejecuciones (total, exitosas, fallidas)
  - Cálculo y visualización de próxima ejecución con tiempo relativo
  - Tabla de historial de ejecuciones (últimas 10)
  - Columnas: Fecha/Hora, Estado, Duración, Mensaje
  - Badges de estado con código de colores (success/failed/warning)
  - Tabla scrollable con altura máxima de 300px
  - Mensaje informativo cuando no hay ejecuciones registradas
  - Formato mejorado con iconos de Font Awesome
  - Diseño responsive con clases Bootstrap

**Características del Historial:**
- Muestra las últimas 10 ejecuciones de cada tarea
- Timestamps formateados en formato local
- Estados visuales con badges de colores
- Duración de ejecución en segundos
- Mensajes de error o éxito de cada ejecución
- Tabla con encabezado fijo (sticky) para mejor navegación

**Información de Próxima Ejecución:**
- Fecha y hora exacta de la próxima ejecución
- Tiempo relativo hasta la próxima ejecución:
  - "en X día(s)" para más de 24 horas
  - "en X hora(s)" para más de 60 minutos
  - "en X minuto(s)" para más de 1 minuto
  - "muy pronto" para menos de 1 minuto
  - "pendiente" para ejecuciones pasadas

### ⏳ Funcionalidades Pendientes
- [ ] Gráficos de uso de namespaces
- [ ] Alertas visuales para límites excedidos
- [ ] Filtros avanzados en logs
- [ ] Exportación de reportes de auditoría
- [ ] Vista de actividad por usuario
- [ ] Vista de actividad por cluster

## API Endpoints Utilizados

### Namespaces

- `GET /api/namespaces` - Lista de namespaces disponibles
- `GET /api/namespaces/status` - Estado detallado de namespaces
- `POST /api/namespaces/activate` - Activar namespace
- `POST /api/namespaces/deactivate` - Desactivar namespace

### Tareas

- `GET /api/tasks` - Lista de tareas programadas
- `POST /api/tasks` - Crear nueva tarea (incluye campos `start` y `allDay` para calendario)
- `GET /api/tasks/{id}` - Detalles de tarea específica
- `PUT /api/tasks/{id}` - Actualizar tarea existente
- `DELETE /api/tasks/{id}` - Eliminar tarea

### Validación

- `GET /api/cost-centers/{cost_center}/validate` - Validar permisos de centro de costo

### Logs

- `GET /api/logs` - Historial de ejecuciones
- `GET /api/logs/audit` - Logs de auditoría

## Configuración

### Variables de Entorno

El frontend se conecta al backend usando la URL base configurada en `api.js`:

```javascript
const API_BASE_URL = window.location.origin;
```

En desarrollo local, puede configurarse manualmente:

```javascript
const API_BASE_URL = 'http://localhost:5000';
```

### Despliegue

El frontend se despliega como una imagen Docker usando Nginx:

1. Build de imagen: `docker build -t task-scheduler-frontend .`
2. Push a ECR: Automatizado con GitHub Actions
3. Despliegue en Kubernetes: Gestionado por ArgoCD

Ver: [deployment-configuration.md](./deployment-configuration.md)

## Mejoras Futuras

### Corto Plazo

1. Completar validación de centro de costo en todas las operaciones
2. Agregar confirmaciones para operaciones críticas
3. Mejorar feedback visual de operaciones
4. Implementar filtros en lista de namespaces

### Mediano Plazo

1. Integración completa con FullCalendar
2. Editor visual de expresiones cron
3. Dashboard con gráficos y métricas
4. Sistema de alertas en tiempo real

### Largo Plazo

1. Modo oscuro
2. Personalización de temas
3. Soporte multi-idioma
4. Aplicación móvil (PWA)
5. Notificaciones push

## Relación con Tareas del Spec

### Completadas

- ✅ Tarea 3.1: Arreglar conexión con Backend
- ✅ Tarea 3.2: Completar interfaz de gestión de namespaces
  - ✅ Carga de lista de namespaces
  - ✅ Estados de carga y error
  - ✅ Actualización en tiempo real del estado
  - ✅ Validación de centro de costo antes de operaciones
  - ✅ Feedback visual mejorado con spinners y animaciones
  - ✅ Confirmaciones para operaciones críticas
- ✅ Tarea 3.3: Completar interfaz de programación de tareas
  - ✅ Integración con FullCalendar mejorada
  - ✅ Carga de tareas con formateo consistente
  - ✅ Código de colores por estado
  - ✅ Formulario completo de creación implementado
  - ✅ Validación de centro de costo en creación de tareas
  - ✅ Limpieza automática del formulario después de creación
  - ✅ Estados de carga y manejo robusto de errores
  - ✅ Validación de expresiones cron en tiempo real
  - ✅ Edición y eliminación de tareas implementada
  - ✅ Vista de historial de ejecuciones en modal de detalles

### Pendientes

- ⏳ Tarea 3.4: Mejorar dashboard y monitoreo con capacidades de auditoría

## Soporte y Troubleshooting

### Problemas Comunes

**Error: "Failed to fetch"**
- Verificar que el backend esté corriendo
- Verificar configuración de CORS en el backend
- Revisar URL base en `api.js`

**Namespaces no se cargan**
- Verificar permisos RBAC del backend
- Revisar logs del backend para errores
- Verificar conectividad con Kubernetes API

**Operaciones fallan silenciosamente**
- Abrir consola del navegador para ver errores
- Verificar que el centro de costo tenga permisos
- Revisar logs de auditoría en el backend

### Debugging

Para habilitar logs detallados en el navegador:

```javascript
// En la consola del navegador
localStorage.setItem('debug', 'true');
```

## Referencias

- [Lista de Estado de Namespaces](./frontend-namespace-status-list.md)
- [Configuración de Despliegue](./deployment-configuration.md)
- [GitHub Actions Setup](./github-actions-setup.md)
- [API Backend](./cost-center-validation-api.md)
