# Documento de Requisitos - Sistema Task Scheduler

## Introducción

El Sistema Task Scheduler es una plataforma especializada para la gestión automatizada de namespaces en clusters de Amazon EKS durante horarios no hábiles. El sistema controla el encendido y apagado de namespaces para optimizar costos, permitiendo operaciones controladas fuera del horario laboral (8pm-7am) y fines de semana, con registro detallado en DynamoDB para seguimiento de costos y auditoría por centro de costo.

## Glosario

- **Sistema_Task_Scheduler**: La plataforma completa que incluye frontend web y kubectl-runner para gestión de namespaces
- **Frontend_Web**: Aplicación web con interfaz de usuario basada en HTML, Bootstrap y FullCalendar
- **kubectl_namespace_ctl**: Servicio backend que ejecuta comandos kubectl para activar/desactivar namespaces
- **Namespace_Sistema**: Namespaces críticos del sistema que nunca se apagan (kube-system, kube-public, etc.)
- **Namespace_Usuario**: Namespaces de aplicaciones de usuario que pueden ser apagados para ahorro de costos
- **Horario_No_Hábil**: Período de 8pm a 7am en días laborales y todo el día en fines de semana
- **Centro_Costo**: Identificador de departamento o proyecto responsable de los costos del namespace
- **Registro_Actividad**: Entrada en DynamoDB con detalles de encendido/apagado de namespaces
- **Límite_Namespaces**: Máximo de 5 namespaces que pueden estar activos simultáneamente en horarios no hábiles
- **Validador_Permisos**: Componente que verifica si un centro de costo tiene autorización para activar namespaces
- **DynamoDB_Logs**: Base de datos NoSQL para almacenar registros de actividad y métricas de costo
- **Rol_AWS**: Rol de IAM para autenticación con AWS sin usar tokens de acceso
- **Cluster_EKS**: Cluster de Amazon Elastic Kubernetes Service donde se gestionan los namespaces

## Requisitos

### Requisito 1: Gestión Automatizada de Namespaces por Horario

**Historia de Usuario:** Como administrador de costos, quiero que los namespaces se apaguen automáticamente en horarios no hábiles, para optimizar el gasto en recursos de AWS.

#### Criterios de Aceptación

1. CUANDO son las 8pm en días laborales, EL Sistema_Task_Scheduler DEBERÁ apagar automáticamente todos los namespaces de usuario
2. CUANDO son las 7am en días laborales, EL Sistema_Task_Scheduler DEBERÁ encender automáticamente todos los namespaces que estaban activos antes del apagado
3. DURANTE fines de semana, EL Sistema_Task_Scheduler DEBERÁ mantener apagados todos los namespaces de usuario por defecto
4. PARA TODOS los namespaces de sistema, EL Sistema_Task_Scheduler DEBERÁ mantenerlos siempre activos sin importar el horario
5. CUANDO se apaga un namespace, EL kubectl_namespace_ctl DEBERÁ escalar a cero todos los deployments, statefulsets y daemonsets del namespace

### Requisito 2: Control de Namespaces en Horarios No Hábiles

**Historia de Usuario:** Como desarrollador, quiero poder activar hasta 5 namespaces durante horarios no hábiles, para realizar trabajo urgente o mantenimiento fuera del horario laboral.

#### Criterios de Aceptación

1. CUANDO un usuario solicita activar un namespace en horario no hábil, EL Sistema_Task_Scheduler DEBERÁ verificar que no se exceda el límite de 5 namespaces activos
2. CUANDO se alcanza el límite de 5 namespaces activos, EL Sistema_Task_Scheduler DEBERÁ rechazar nuevas solicitudes de activación
3. CUANDO un usuario desactiva un namespace manualmente, EL Sistema_Task_Scheduler DEBERÁ permitir activar otro namespace respetando el límite
4. PARA TODAS las activaciones en horario no hábil, EL Sistema_Task_Scheduler DEBERÁ registrar la actividad en DynamoDB
5. CUANDO se activa un namespace, EL kubectl_namespace_ctl DEBERÁ restaurar el escalado original de todos los recursos del namespace

### Requisito 3: Validación de Centro de Costo y Permisos

**Historia de Usuario:** Como administrador financiero, quiero que solo centros de costo autorizados puedan activar namespaces, para controlar y auditar el gasto por departamento.

#### Criterios de Aceptación

1. CUANDO un usuario solicita activar un namespace, EL Validador_Permisos DEBERÁ verificar que el centro de costo tenga permisos válidos
2. CUANDO un centro de costo no tiene permisos, EL Sistema_Task_Scheduler DEBERÁ rechazar la solicitud con mensaje explicativo
3. EL Sistema_Task_Scheduler DEBERÁ mantener una lista configurable de centros de costo autorizados
4. CUANDO se actualiza la lista de permisos, EL Sistema_Task_Scheduler DEBERÁ aplicar los cambios sin reinicio
5. PARA TODAS las validaciones de permisos, EL Sistema_Task_Scheduler DEBERÁ registrar intentos exitosos y fallidos

### Requisito 4: Registro Detallado en DynamoDB

**Historia de Usuario:** Como auditor de costos, quiero registros detallados de todas las actividades de namespaces, para calcular costos precisos y generar reportes de uso.

#### Criterios de Aceptación

1. CUANDO se activa un namespace, EL Sistema_Task_Scheduler DEBERÁ crear un registro en DynamoDB con timestamp de inicio, centro de costo y namespace
2. CUANDO se desactiva un namespace, EL Sistema_Task_Scheduler DEBERÁ actualizar el registro con timestamp de fin y calcular duración en minutos
3. PARA TODOS los registros, EL Sistema_Task_Scheduler DEBERÁ incluir información de usuario, centro de costo, namespace y tipo de operación
4. EL Sistema_Task_Scheduler DEBERÁ calcular automáticamente el tiempo empleado en minutos entre activación y desactivación
5. CUANDO ocurre un error en el registro, EL Sistema_Task_Scheduler DEBERÁ reintentar la escritura a DynamoDB hasta 3 veces

### Requisito 5: Interfaz Web para Gestión de Namespaces

**Historia de Usuario:** Como usuario del sistema, quiero una interfaz web intuitiva, para solicitar activación de namespaces y monitorear el estado actual.

#### Criterios de Aceptación

1. CUANDO un usuario accede al frontend, EL Frontend_Web DEBERÁ mostrar el estado actual de todos los namespaces (activo/inactivo)
2. CUANDO un usuario completa el formulario de activación, EL Frontend_Web DEBERÁ validar el centro de costo antes del envío
3. CUANDO se muestra el formulario, EL Frontend_Web DEBERÁ indicar claramente cuántos namespaces están activos del límite de 5
4. EL Frontend_Web DEBERÁ mostrar un calendario con las activaciones programadas y horarios de apagado automático
5. CUANDO un namespace está activo, EL Frontend_Web DEBERÁ mostrar el tiempo transcurrido desde la activación

### Requisito 6: Autenticación con Rol de AWS

**Historia de Usuario:** Como administrador de seguridad, quiero que el sistema use roles de AWS en lugar de tokens, para mejorar la seguridad y seguir mejores prácticas de AWS.

#### Criterios de Aceptación

1. EL kubectl_namespace_ctl DEBERÁ autenticarse con AWS usando un rol de IAM asignado al ServiceAccount de Kubernetes
2. CUANDO se ejecutan operaciones en DynamoDB, EL Sistema_Task_Scheduler DEBERÁ usar el rol de AWS para autenticación
3. EL sistema DEBERÁ configurarse sin tokens de acceso hardcodeados en variables de entorno o código
4. CUANDO el rol de AWS no tiene permisos suficientes, EL Sistema_Task_Scheduler DEBERÁ reportar errores específicos de autorización
5. EL Rol_AWS DEBERÁ tener permisos mínimos necesarios para operaciones de EKS y DynamoDB únicamente

### Requisito 7: API REST para Operaciones de Namespace

**Historia de Usuario:** Como desarrollador, quiero una API REST bien definida, para integrar el sistema con otras herramientas de automatización y monitoreo.

#### Criterios de Aceptación

1. EL kubectl_namespace_ctl DEBERÁ exponer endpoints REST para activar, desactivar y consultar estado de namespaces
2. CUANDO se realiza una solicitud de activación, EL kubectl_namespace_ctl DEBERÁ validar permisos y límites antes de proceder
3. EL kubectl_namespace_ctl DEBERÁ proporcionar endpoints para consultar registros de DynamoDB por centro de costo y rango de fechas
4. CUANDO se consulta el estado de namespaces, EL kubectl_namespace_ctl DEBERÁ devolver información en tiempo real del cluster
5. PARA TODAS las respuestas de la API, EL kubectl_namespace_ctl DEBERÁ incluir códigos de estado HTTP apropiados y mensajes descriptivos

### Requisito 8: Monitoreo y Alertas

**Historia de Usuario:** Como administrador de sistemas, quiero monitoreo proactivo del sistema, para detectar problemas y asegurar el funcionamiento correcto de las operaciones automatizadas.

#### Criterios de Aceptación

1. EL Sistema_Task_Scheduler DEBERÁ exponer métricas de health check que incluyan estado de conexión a EKS y DynamoDB
2. CUANDO falla una operación de apagado/encendido automático, EL Sistema_Task_Scheduler DEBERÁ registrar el error y continuar con otros namespaces
3. EL Sistema_Task_Scheduler DEBERÁ mantener métricas de namespaces activos, operaciones exitosas y fallidas
4. CUANDO se detecta una inconsistencia entre el estado esperado y real, EL Sistema_Task_Scheduler DEBERÁ intentar reconciliar automáticamente
5. EL kubectl_namespace_ctl DEBERÁ proporcionar endpoints para consultar métricas operacionales y estado del sistema

### Requisito 9: Configuración y Despliegue

**Historia de Usuario:** Como ingeniero DevOps, quiero que el sistema sea fácil de configurar y desplegar, para mantener operaciones estables y actualizaciones sin interrupciones.

#### Criterios de Aceptación

1. EL Sistema_Task_Scheduler DEBERÁ configurarse mediante variables de entorno para horarios, límites y configuración de AWS
2. CUANDO se despliega el sistema, EL kubectl_namespace_ctl DEBERÁ verificar automáticamente conectividad con EKS y DynamoDB
3. EL sistema DEBERÁ soportar configuración de zona horaria para cálculos correctos de horarios hábiles/no hábiles
4. CUANDO se actualiza la configuración, EL Sistema_Task_Scheduler DEBERÁ aplicar cambios sin reiniciar servicios
5. EL despliegue DEBERÁ incluir la creación automática de tablas de DynamoDB con los índices necesarios

### Requisito 10: Persistencia y Recuperación

**Historia de Usuario:** Como administrador de sistemas, quiero que el sistema mantenga estado consistente, para recuperarse correctamente de interrupciones y mantener operaciones confiables.

#### Criterios de Aceptación

1. CUANDO el kubectl_namespace_ctl se reinicia, EL Sistema_Task_Scheduler DEBERÁ recuperar el estado actual de namespaces desde el cluster EKS
2. EL Sistema_Task_Scheduler DEBERÁ mantener un registro local de operaciones pendientes para completar tras interrupciones
3. CUANDO se detecta una inconsistencia tras reinicio, EL Sistema_Task_Scheduler DEBERÁ reconciliar el estado basado en DynamoDB y EKS
4. EL Sistema_Task_Scheduler DEBERÁ implementar idempotencia en todas las operaciones para evitar duplicados
5. PARA TODAS las operaciones críticas, EL Sistema_Task_Scheduler DEBERÁ usar transacciones o mecanismos de rollback apropiados