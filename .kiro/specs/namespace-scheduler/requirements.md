# Namespace Scheduler - Requisitos

## Descripción del Proyecto

Sistema de programación automática de namespaces en Kubernetes que permite activar y desactivar namespaces según horarios programados, con límites durante horarios no laborales y gestión por centros de costo.

## Arquitectura

- **Frontend**: Interfaz web con calendario para programar tareas
- **Backend**: API Flask que ejecuta comandos kubectl y gestiona tareas
- **Base de Datos**: DynamoDB para logs y permisos
- **Despliegue**: ArgoCD para CI/CD
- **Construcción**: GitHub Actions para build de imágenes

## Historias de Usuario

### 1. Gestión de Namespaces
**Como** administrador del cluster
**Quiero** poder activar y desactivar namespaces manualmente desde la interfaz web
**Para** controlar el uso de recursos en tiempo real

**Criterios de Aceptación:**
1.1 La interfaz debe mostrar una lista de todos los namespaces disponibles
1.2 Debe permitir activar un namespace seleccionado con un centro de costo
1.3 Debe permitir desactivar un namespace activo
1.4 Debe mostrar el estado actual de cada namespace (activo/inactivo)
1.5 Debe validar permisos del centro de costo antes de activar

### 2. Programación de Tareas
**Como** administrador del cluster
**Quiero** programar tareas de activación/desactivación de namespaces usando expresiones cron
**Para** automatizar la gestión de recursos según horarios de trabajo

**Criterios de Aceptación:**
2.1 Debe permitir crear tareas programadas con expresiones cron
2.2 Debe soportar tareas de activación y desactivación de namespaces
2.3 Debe mostrar las tareas en un calendario visual
2.4 Debe ejecutar las tareas automáticamente según la programación
2.5 Debe registrar el resultado de cada ejecución

### 3. Control de Horarios No Laborales
**Como** administrador del cluster
**Quiero** limitar a máximo 5 namespaces activos durante horarios no laborales
**Para** controlar costos y uso de recursos

**Criterios de Aceptación:**
3.1 Debe detectar automáticamente horarios no laborales (8pm-7am y fines de semana)
3.2 Debe limitar a máximo 5 namespaces activos durante estos horarios
3.3 Debe mostrar el contador actual de namespaces activos
3.4 Debe mostrar el estado del horario (laboral/no laboral)
3.5 Debe rechazar activaciones que excedan el límite

### 4. Gestión de Centros de Costo
**Como** administrador del cluster
**Quiero** asociar cada operación con un centro de costo
**Para** tener trazabilidad y control de gastos

**Criterios de Aceptación:**
4.1 Debe requerir selección de centro de costo para cada operación
4.2 Debe validar permisos del centro de costo
4.3 Debe registrar todas las actividades con su centro de costo asociado
4.4 Debe permitir consultar actividades por centro de costo

### 5. Monitoreo y Logs
**Como** administrador del cluster
**Quiero** ver logs detallados de todas las operaciones con capacidades de auditoría avanzadas
**Para** monitorear el sistema, diagnosticar problemas y mantener trazabilidad completa

**Criterios de Aceptación:**
5.1 Debe mostrar logs de ejecución en tiempo real
5.2 Debe registrar todas las operaciones en DynamoDB con información completa de auditoría
5.3 Debe mostrar estadísticas del dashboard (tareas activas, completadas, fallidas)
5.4 Debe permitir filtrar logs por fecha, centro de costo, cluster y usuario solicitante
5.5 Debe rastrear qué usuario solicitó cada operación para auditoría
5.6 Debe permitir consultas por cluster específico para análisis de actividad
5.7 Debe generar reportes de actividad por usuario y cluster

### 6. Despliegue con ArgoCD
**Como** DevOps engineer
**Quiero** que el sistema se despliegue automáticamente usando ArgoCD
**Para** tener un proceso de CI/CD confiable

**Criterios de Aceptación:**
6.1 Debe tener manifiestos de Kubernetes organizados con Kustomize
6.2 Debe configurar ArgoCD para sincronizar automáticamente
6.3 Debe incluir configuración de RBAC para kubectl-runner
6.4 Debe configurar ingress para acceso externo

### 7. Build Automático con GitHub Actions
**Como** desarrollador
**Quiero** que las imágenes se construyan automáticamente en cada push
**Para** tener un proceso de integración continua

**Criterios de Aceptación:**
7.1 Debe construir imagen del frontend automáticamente
7.2 Debe construir imagen del backend automáticamente
7.3 Debe subir las imágenes a ECR
7.4 Debe actualizar los tags en los manifiestos de Kubernetes

### 8. Auditoría y Trazabilidad Avanzada
**Como** administrador de seguridad
**Quiero** tener capacidades completas de auditoría y trazabilidad de operaciones
**Para** cumplir con requisitos de compliance y seguridad

**Criterios de Aceptación:**
8.1 Debe registrar el usuario que solicita cada operación
8.2 Debe registrar el cluster donde se ejecuta cada operación
8.3 Debe permitir consultar todas las operaciones por usuario solicitante
8.4 Debe permitir consultar todas las operaciones por cluster
8.5 Debe generar reportes de auditoría por usuario y cluster
8.6 Debe mantener trazabilidad completa de la cadena de aprobación
8.7 Debe permitir exportar logs de auditoría para análisis externos

### 9. Vista Semanal del Dashboard
**Como** administrador del cluster
**Quiero** ver una vista semanal completa de 7 días x 24 horas mostrando qué namespaces están programados para estar activos
**Para** entender rápidamente la programación de todos los namespaces durante toda la semana y optimizar el uso de recursos

**Criterios de Aceptación:**
9.1 Debe mostrar una grilla de 7 días (Lunes a Domingo) como columnas
9.2 Debe mostrar 24 horas (00:00 a 23:00) como filas para cada día
9.3 Debe ser la vista principal del dashboard al cargar la aplicación
9.4 Debe reemplazar las estadísticas básicas actuales como interfaz principal
9.5 Debe mostrar la semana actual por defecto
9.6 Debe mostrar los nombres de los namespaces programados en cada slot de tiempo
9.7 Debe mostrar múltiples namespaces cuando estén programados para el mismo horario
9.8 Debe usar indicadores visuales distintos (colores, iconos) para diferenciar namespaces
9.9 Debe conectar visualmente los slots de tiempo cuando un namespace tenga programación continua

### 10. Navegación Temporal en Vista Semanal
**Como** administrador del cluster
**Quiero** navegar entre diferentes semanas en la vista semanal
**Para** revisar programaciones pasadas y planificar programaciones futuras

**Criterios de Aceptación:**
10.1 Debe proporcionar controles para navegar a la semana anterior
10.2 Debe proporcionar controles para navegar a la semana siguiente
10.3 Debe actualizar los datos de programación al cambiar de semana
10.4 Debe mostrar prominentemente el rango de la semana actual (fecha inicio - fecha fin)
10.5 Debe proporcionar un botón "Semana Actual" para regresar rápidamente

### 11. Integración de Datos para Vista Semanal
**Como** desarrollador del sistema
**Quiero** que la vista semanal utilice los datos existentes del sistema
**Para** mantener consistencia y evitar duplicación de información

**Criterios de Aceptación:**
11.1 Debe obtener datos de programación desde la base de datos DynamoDB existente
11.2 Debe usar los endpoints de la API Flask existente o crear nuevos siguiendo los mismos patrones
11.3 Debe reflejar cambios cuando los datos de programación se actualicen
11.4 Debe mantener compatibilidad con el sistema de autenticación y permisos existente
11.5 Debe manejar estados de carga y mostrar indicadores apropiados

### 12. Responsividad y Usabilidad de Vista Semanal
**Como** usuario del sistema
**Quiero** que la vista semanal sea fácil de usar y se adapte a diferentes tamaños de pantalla
**Para** acceder a la información desde cualquier dispositivo

**Criterios de Aceptación:**
12.1 Debe ser responsiva y adaptarse a diferentes tamaños de pantalla (escritorio, tablet, móvil)
12.2 Debe proporcionar scroll horizontal o layouts alternativos en pantallas pequeñas
12.3 Debe mantener legibilidad de nombres de namespaces e información de tiempo en todos los tamaños
12.4 Debe mostrar detalles adicionales al hacer hover o click en un slot de tiempo
12.5 Debe proporcionar feedback visual claro para interacciones del usuario

### 13. Rendimiento de Vista Semanal
**Como** usuario del sistema
**Quiero** que la vista semanal cargue rápidamente y maneje eficientemente grandes cantidades de datos
**Para** tener una experiencia fluida

**Criterios de Aceptación:**
13.1 Debe cargar y mostrar información semanal en menos de 3 segundos bajo condiciones normales de red
13.2 Debe implementar caché eficiente para evitar llamadas innecesarias a la API al navegar entre semanas
13.3 Debe implementar paginación o carga lazy cuando los datos semanales sean grandes
13.4 Debe proporcionar manejo de errores y mecanismos de reintento para solicitudes fallidas
13.5 Debe mostrar estados de carga apropiados sin bloquear la interacción del usuario

### 14. Marcado de Festivos Colombianos
**Como** administrador del cluster
**Quiero** que el sistema identifique y marque visualmente los días festivos en Colombia en la vista semanal
**Para** permitir activación de namespaces en festivos pero con diferenciación visual clara

**Criterios de Aceptación:**
14.1 Debe identificar automáticamente los días festivos oficiales de Colombia
14.2 Debe marcar visualmente los días festivos con un color o indicador diferente en la vista semanal
14.3 Debe permitir la activación de namespaces durante días festivos sin restricciones adicionales
14.4 Debe mostrar claramente que un día es festivo mediante tooltips o etiquetas
14.5 Debe incluir tanto festivos fijos como festivos móviles del calendario colombiano
14.6 Debe actualizar automáticamente la lista de festivos para el año en curso

### 15. Reporte Semanal de Horas por Namespace y Centro de Costo
**Como** administrador financiero
**Quiero** generar reportes semanales que muestren las horas de uso de cada namespace y su centro de costo asociado
**Para** realizar seguimiento de costos y optimizar el uso de recursos

**Criterios de Aceptación:**
15.1 Debe generar un reporte semanal mostrando las horas totales de actividad por namespace
15.2 Debe asociar cada namespace con su centro de costo correspondiente en el reporte
15.3 Debe calcular automáticamente las horas de uso basado en los horarios programados y ejecuciones reales
15.4 Debe permitir exportar el reporte en formato CSV o Excel
15.5 Debe mostrar el reporte directamente en la interfaz web con tablas organizadas
15.6 Debe incluir totales por centro de costo y gran total de horas
15.7 Debe permitir generar reportes para semanas específicas, no solo la semana actual
15.8 Debe diferenciar entre horas programadas y horas realmente ejecutadas

## Restricciones Técnicas

- El backend debe usar Python Flask
- El frontend debe ser una SPA con JavaScript vanilla
- Debe usar DynamoDB para persistencia
- Debe ejecutarse en un cluster EKS
- Debe usar kubectl para operaciones de Kubernetes
- Las imágenes deben almacenarse en ECR

## Definición de Terminado

Una funcionalidad está terminada cuando:
- El código está implementado y funciona correctamente
- Se puede desplegar usando ArgoCD
- Las imágenes se construyen automáticamente con GitHub Actions
- La funcionalidad es accesible desde la interfaz web
- Se registran logs apropiados en DynamoDB