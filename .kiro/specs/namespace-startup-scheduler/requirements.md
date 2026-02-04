# Documento de Requisitos

## Introducción

Sistema MVP para programar el auto-encendido de namespaces en un cluster de Kubernetes con autoscaling. El sistema permite a los administradores programar el encendido automático de namespaces específicos cuando el cluster está escalado a 0, con un límite de máximo 5 namespaces adicionales además de los namespaces de sistema.

## Glosario

- **Sistema**: El sistema de programación de auto-encendido de namespaces
- **Cluster**: El cluster de Kubernetes con capacidad de autoscaling
- **Namespace_Sistema**: Namespaces críticos del sistema (kube-system, kube-public, etc.)
- **Namespace_Usuario**: Namespaces de aplicaciones de usuario que pueden ser programados
- **Programador**: Administrador que configura los horarios de encendido
- **Programación**: Configuración que incluye namespace, fecha/hora de encendido, fecha/hora de apagado, usuario responsable, proyecto y centro de costo
- **Interfaz_Web**: La interfaz gráfica web para configurar programaciones


## Requisitos

### Requisito 1: Pipeline CI/CD con OIDC

**User Story:** Como DevOps engineer, quiero un pipeline de CI/CD seguro y funcional, para que las imágenes Docker se construyan y publiquen correctamente en ECR sin usar access keys.

#### Criterios de Aceptación

1. CUANDO se ejecuta el workflow de GitHub Actions, EL Pipeline DEBERÁ autenticarse usando OIDC sin access keys
2. CUANDO se construyen imágenes Docker, EL Pipeline DEBERÁ usar Dockerfiles optimizados para controlador y frontend
3. CUANDO se referencian outputs de steps, EL Pipeline DEBERÁ usar sintaxis y nombres de variables correctos
4. CUANDO se validan archivos YAML, EL Pipeline DEBERÁ validar todos los manifiestos de Kubernetes completamente
5. CUANDO existen políticas Kyverno, EL Pipeline DEBERÁ validarlas opcionalmente sin fallar si no existen
6. CUANDO se escanean vulnerabilidades de seguridad, EL Pipeline DEBERÁ analizar tanto código como imágenes de contenedor
7. CUANDO se actualizan manifiestos, EL Pipeline DEBERÁ usar rutas de archivos correctas y desplegar directamente con kubectl
8. CUANDO el pipeline falla, EL Pipeline DEBERÁ proporcionar mensajes de error claros y capacidades de rollback con kubectl

### Requisito 2: Infraestructura de Contenedores Segura

**User Story:** Como developer, quiero Dockerfiles optimizados y seguros, para que las aplicaciones se ejecuten eficientemente en contenedores.

#### Criterios de Aceptación

1. CUANDO se construye la imagen del controlador, EL Dockerfile_Controlador DEBERÁ crear un build multi-stage con superficie de ataque mínima
2. CUANDO se construye la imagen del frontend, EL Dockerfile_Frontend DEBERÁ servir archivos estáticos a través de nginx con headers de seguridad
3. CUANDO los contenedores inician, LAS Imágenes_Contenedor DEBERÁN ejecutarse como usuarios no-root con privilegios mínimos
4. CUANDO se escanean imágenes, EL Escáner_Seguridad DEBERÁ detectar y reportar vulnerabilidades antes del despliegue
5. DONDE se configuran health checks, LAS Imágenes_Contenedor DEBERÁN responder a probes de liveness y readiness

### Requisito 3: Monitoreo y Observabilidad

**User Story:** Como administrador del sistema, quiero monitoreo completo del sistema para detectar problemas y optimizar el rendimiento.

#### Criterios de Aceptación

1. CUANDO el sistema ejecuta operaciones, EL Sistema DEBERÁ generar logs estructurados con correlation IDs
2. CUANDO ocurren errores, EL Sistema DEBERÁ registrar detalles completos del error con contexto
3. EL Sistema DEBERÁ exponer métricas Prometheus para monitoreo de rendimiento
4. EL Sistema DEBERÁ mantener health checks para liveness y readiness
5. CUANDO se ejecutan programaciones, EL Sistema DEBERÁ registrar métricas de éxito/fallo y tiempo de ejecución
6. EL Sistema DEBERÁ proporcionar dashboards básicos para visualización de métricas

### Requisito 4: Resilencia y Manejo de Errores

**User Story:** Como administrador del sistema, quiero que el sistema sea resiliente a fallos y se recupere automáticamente cuando sea posible.

#### Criterios de Aceptación

1. CUANDO falla la conexión a DynamoDB, EL Sistema DEBERÁ implementar retry con backoff exponencial
2. CUANDO falla la conexión a EKS, EL Sistema DEBERÁ implementar circuit breaker para evitar cascadas de fallos
3. CUANDO ocurren errores repetidos, EL Sistema DEBERÁ implementar degradación elegante
4. EL Sistema DEBERÁ mantener caché local para continuidad de servicio durante fallos temporales
5. CUANDO se recupera de un fallo, EL Sistema DEBERÁ procesar operaciones pendientes automáticamente

### Requisito 5: Interfaz de Programación de Encendido

**User Story:** Como administrador del cluster, quiero programar el encendido de namespaces específicos en fechas y horas determinadas, para que las aplicaciones estén disponibles cuando se necesiten.

#### Criterios de Aceptación

1. CUANDO un programador accede a la interfaz web, EL Sistema DEBERÁ mostrar una lista de namespaces disponibles para programar
2. CUANDO un programador selecciona un namespace, EL Sistema DEBERÁ permitir configurar fecha, hora de encendido, hora de apagado, usuario, proyecto y centro de costo
3. CUANDO un programador guarda una programación, EL Sistema DEBERÁ validar que todos los campos requeridos estén completos, que la fecha/hora de encendido sea futura y desde las 8:00 AM, que la hora de apagado sea máximo hasta las 3:00 AM del día siguiente, y que el centro de costo esté autorizado para el namespace seleccionado
4. CUANDO un programador selecciona un namespace, EL Sistema DEBERÁ mostrar solo los centros de costo válidos para ese namespace
5. CUANDO un programador intenta programar más de 5 namespaces de usuario, EL Sistema DEBERÁ rechazar la configuración y mostrar un mensaje de error
6. EL Sistema DEBERÁ persistir todas las programaciones configuradas

### Requisito 6: Gestión de Límites de Namespaces

**User Story:** Como administrador del sistema, quiero limitar el número de namespaces de usuario que pueden ser encendidos automáticamente, para controlar el uso de recursos del cluster.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ permitir máximo 5 namespaces de usuario programados simultáneamente
2. CUANDO se alcanza el límite de 5 namespaces, EL Sistema DEBERÁ prevenir la adición de nuevas programaciones
3. CUANDO un programador elimina una programación existente, EL Sistema DEBERÁ permitir agregar nuevas programaciones hasta el límite
4. EL Sistema DEBERÁ mostrar el contador actual de namespaces programados en la interfaz

### Requisito 7: Encendido Automático de Namespaces

**User Story:** Como administrador del cluster, quiero que los namespaces se enciendan automáticamente en las fechas/horas programadas, para que las aplicaciones estén disponibles sin intervención manual.

#### Criterios de Aceptación

1. CUANDO llega la fecha/hora programada para un namespace, EL Sistema DEBERÁ iniciar el proceso de encendido del cluster si está en escala 0
2. CUANDO el cluster se enciende, EL Sistema DEBERÁ asegurar que todos los namespaces de sistema se inicien primero
3. CUANDO los namespaces de sistema están activos, EL Sistema DEBERÁ iniciar los namespaces de usuario programados
4. CUANDO un namespace se enciende exitosamente, EL Sistema DEBERÁ marcar la programación como completada
5. SI el encendido de un namespace falla, EL Sistema DEBERÁ registrar el error y continuar con los demás namespaces programados

### Requisito 8: Monitoreo del Estado del Cluster

**User Story:** Como administrador del sistema, quiero monitorear el estado actual del cluster y los namespaces, para entender cuándo es necesario el auto-encendido.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ verificar periódicamente si el cluster está en escala 0
2. EL Sistema DEBERÁ identificar automáticamente cuáles son los namespaces de sistema requeridos
3. CUANDO el cluster está activo, EL Sistema DEBERÁ mostrar el estado actual de todos los namespaces en la interfaz
4. EL Sistema DEBERÁ mantener un registro de las últimas actividades de encendido

### Requisito 9: Interfaz Web Simple

**User Story:** Como programador, quiero una interfaz web intuitiva y simple, para configurar programaciones de encendido sin complejidad técnica.

#### Criterios de Aceptación

1. LA Interfaz_Web DEBERÁ mostrar una vista principal con todas las programaciones activas
2. CUANDO un programador hace clic en "Nueva Programación", LA Interfaz_Web DEBERÁ mostrar un formulario con campos de namespace, fecha, hora de encendido, hora de apagado, usuario, proyecto y centro de costo
3. LA Interfaz_Web DEBERÁ validar los datos del formulario antes de enviarlos al servidor
4. CUANDO se completa una acción, LA Interfaz_Web DEBERÁ mostrar mensajes de confirmación o error claros
5. LA Interfaz_Web DEBERÁ ser responsive y funcionar en navegadores web modernos

### Requisito 10: Persistencia de Configuraciones

**User Story:** Como administrador del sistema, quiero que las programaciones se mantengan persistentes, para que no se pierdan al reiniciar el sistema.

#### Criterios de Aceptación

1. CUANDO se crea una programación, EL Sistema DEBERÁ almacenarla en almacenamiento persistente
2. CUANDO el sistema se reinicia, EL Sistema DEBERÁ cargar todas las programaciones 
3. CUANDO se modifica una programación, EL Sistema DEBERÁ actualizar el almacenamiento inmediatamente
4. CUANDO se elimina una programación, EL Sistema DEBERÁ removerla del almacenamiento persistente
5. EL Sistema DEBERÁ mantener un respaldo de las configuraciones críticas

### Requisito 11: Validación de Centros de Costo

**User Story:** Como administrador del sistema, quiero que el sistema valide que solo se usen centros de costo autorizados para cada namespace, para mantener el control de costos y permisos.

#### Criterios de Aceptación

1. EL Sistema DEBERÁ cargar un archivo de configuración que mapee namespaces con centros de costo permitidos
2. CUANDO un programador selecciona un namespace, EL Sistema DEBERÁ filtrar y mostrar solo los centros de costo válidos para ese namespace
3. CUANDO se intenta guardar una programación con un centro de costo no autorizado, EL Sistema DEBERÁ rechazar la operación y mostrar un mensaje de error
4. CUANDO se actualiza el archivo de configuración, EL Sistema DEBERÁ recargar las validaciones sin reiniciar
5. SI el archivo de configuración no está disponible, EL Sistema DEBERÁ registrar un error y prevenir la creación de nuevas programaciones

### Requisito 13: Despliegue GitOps con ArgoCD

**User Story:** Como DevOps engineer, quiero usar ArgoCD para despliegue GitOps, para tener control declarativo y versionado de las aplicaciones en Kubernetes.

#### Criterios de Aceptación

1. CUANDO se configura ArgoCD, EL Sistema DEBERÁ crear dos aplicaciones separadas: frontend y backend
2. CUANDO se actualiza el código, EL Pipeline DEBERÁ actualizar los manifiestos en el repositorio Git
3. CUANDO ArgoCD detecta cambios en Git, DEBERÁ sincronizar automáticamente las aplicaciones
4. CUANDO ocurre un fallo de despliegue, ArgoCD DEBERÁ permitir rollback a versiones anteriores
5. EL Sistema DEBERÁ mantener configuraciones separadas para frontend y backend en ArgoCD
6. CUANDO se despliega, ArgoCD DEBERÁ validar la salud de las aplicaciones antes de marcar como exitoso
7. EL Sistema DEBERÁ proporcionar visibilidad del estado de despliegue a través de la UI de ArgoCD

### Requisito 14: Restricciones de Horarios de Operación

**User Story:** Como administrador del sistema, quiero establecer ventanas de tiempo permitidas para el encendido y apagado de namespaces, para optimizar el uso de recursos y cumplir con políticas operacionales.

#### Criterios de Aceptación

1. CUANDO un programador configura una hora de encendido, EL Sistema DEBERÁ validar que sea desde las 8:00 AM en adelante
2. CUANDO un programador configura una programación, EL Sistema DEBERÁ solicitar obligatoriamente una hora de apagado
3. CUANDO un programador configura una hora de apagado, EL Sistema DEBERÁ validar que sea máximo hasta las 3:00 AM del día siguiente
4. CUANDO se valida una programación, EL Sistema DEBERÁ asegurar que la hora de apagado sea posterior a la hora de encendido
5. EL Sistema DEBERÁ ejecutar automáticamente el apagado de namespaces en la hora programada
