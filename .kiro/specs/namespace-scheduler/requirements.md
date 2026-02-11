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
**Quiero** ver logs detallados de todas las operaciones
**Para** monitorear el sistema y diagnosticar problemas

**Criterios de Aceptación:**
5.1 Debe mostrar logs de ejecución en tiempo real
5.2 Debe registrar todas las operaciones en DynamoDB
5.3 Debe mostrar estadísticas del dashboard (tareas activas, completadas, fallidas)
5.4 Debe permitir filtrar logs por fecha y centro de costo

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