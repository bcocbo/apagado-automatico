# Frontend - Lista de Estado de Namespaces

## Descripción General

La interfaz web del Task Scheduler incluye una lista visual en tiempo real que muestra el estado de todos los namespaces disponibles en el cluster de Kubernetes. Esta funcionalidad permite a los usuarios monitorear rápidamente qué namespaces están activos o inactivos, junto con información sobre sus recursos.

## Ubicación en la Interfaz

La lista de estado de namespaces se encuentra en la sección "Programador" (Scheduler), en el panel lateral derecho, debajo de la tarjeta de "Gestión de Namespaces".

## Características

### Visualización de Estado

Cada namespace en la lista muestra:

- **Nombre del namespace**: Identificador único del namespace
- **Badge de estado**: 
  - Verde ("Activo") para namespaces activos
  - Gris ("Inactivo") para namespaces desactivados
- **Información de recursos** (cuando está disponible):
  - Número de pods activos
  - Cantidad de deployments
  - Cantidad de statefulsets

### Filtrado Automático

La lista filtra automáticamente los namespaces del sistema (como `kube-system`, `kube-public`, etc.) para mostrar únicamente los namespaces de usuario, proporcionando una vista más limpia y relevante.

### Actualización en Tiempo Real

La lista se actualiza automáticamente cuando:
- Se carga el estado de namespaces desde el backend
- Se activa o desactiva un namespace
- El usuario hace clic en el botón "Actualizar"

## Implementación Técnica

### Función Principal

```javascript
updateNamespaceStatusList()
```

Esta función:
1. Obtiene el contenedor HTML con id `namespace-status-list`
2. Recupera los datos de namespaces desde `this.namespacesStatus.namespaces`
3. Filtra los namespaces del sistema usando la propiedad `is_system`
4. Genera HTML dinámico para cada namespace con su información
5. Actualiza el contenedor con el contenido generado

### Estructura de Datos

Cada namespace en la lista espera los siguientes campos del backend:

```javascript
{
  name: string,           // Nombre del namespace
  is_active: boolean,     // Estado activo/inactivo
  is_system: boolean,     // Si es namespace del sistema
  active_pods: number,    // Número de pods activos
  deployments: array,     // Lista de deployments
  statefulsets: array     // Lista de statefulsets
}
```

### Integración con el Backend

La lista se actualiza automáticamente cuando se llama a:
- `loadNamespacesStatus()`: Carga el estado inicial desde el endpoint `/api/namespaces/status`
- `activateNamespace()`: Después de activar un namespace
- `deactivateNamespace()`: Después de desactivar un namespace

## Interfaz de Usuario

### Elementos Visuales

- **Card Header**: Incluye el título "Estado de Namespaces", timestamp de última actualización, y botón de actualización manual
- **Card Body**: Contenedor scrollable (máximo 400px de altura) con la lista de namespaces
- **List Items**: Cada namespace se muestra como un item de lista con diseño flex para alinear información

### Estados de la Lista

1. **Cargando**: Muestra mensaje "Cargando estado de namespaces..."
2. **Sin namespaces**: Muestra "No hay namespaces disponibles"
3. **Sin namespaces de usuario**: Muestra "No hay namespaces de usuario"
4. **Con datos**: Muestra la lista completa de namespaces con su información

## Casos de Uso

### Monitoreo Rápido

Los usuarios pueden ver de un vistazo:
- Cuántos namespaces están activos vs inactivos
- Qué namespaces tienen recursos desplegados
- El estado general del cluster

### Validación de Operaciones

Después de activar o desactivar un namespace, los usuarios pueden verificar visualmente que la operación se completó correctamente observando el cambio en el badge de estado.

### Planificación de Recursos

La información de pods, deployments y statefulsets ayuda a los usuarios a:
- Identificar namespaces con alta utilización
- Planificar activaciones/desactivaciones
- Detectar namespaces que pueden estar consumiendo recursos innecesariamente

## Mejoras Futuras

Posibles mejoras para esta funcionalidad:

1. **Filtros adicionales**: Permitir filtrar por estado (activo/inactivo)
2. **Ordenamiento**: Ordenar por nombre, estado, o número de recursos
3. **Búsqueda**: Campo de búsqueda para encontrar namespaces específicos
4. **Acciones rápidas**: Botones inline para activar/desactivar directamente desde la lista
5. **Información adicional**: Mostrar centro de costo, última modificación, etc.
6. **Indicadores visuales**: Gráficos o barras de progreso para uso de recursos

## Relación con Tareas del Spec

Esta implementación contribuye a:

- **Tarea 3.2**: Completar interfaz de gestión de namespaces
  - ✅ Implementar actualización en tiempo real del estado
  - Pendiente: Agregar validación de centro de costo antes de operaciones
  - Pendiente: Mejorar feedback visual de operaciones exitosas/fallidas

## Notas de Desarrollo

- La función se llama automáticamente desde `updateNamespaceStatus()` después de actualizar los contadores
- El filtrado de namespaces del sistema mejora la experiencia del usuario al reducir el ruido visual
- La lista es responsive y se adapta al tamaño del contenedor
- El scroll automático permite manejar un gran número de namespaces sin afectar el layout
