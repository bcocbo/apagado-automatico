# 🚀 Namespace Startup Scheduler

Sistema MVP para programar el auto-encendido de namespaces en un cluster de Kubernetes con autoscaling.

## 📋 Descripción

Este sistema permite a los administradores programar el encendido automático de namespaces específicos cuando el cluster está escalado a 0, con un límite de máximo 5 namespaces adicionales además de los namespaces de sistema.

## 🏗️ Arquitectura

- **Backend**: FastAPI + DynamoDB + boto3
- **Frontend**: React + TypeScript + Material-UI  
- **Scheduler**: Lambda/ECS Task para ejecución automática
- **Storage**: DynamoDB para programaciones, S3 para configuración

## 📁 Estructura del Proyecto

```
├── .kiro/specs/namespace-startup-scheduler/  # Especificaciones del proyecto
│   ├── requirements.md                       # Requisitos detallados
│   ├── design.md                            # Diseño y arquitectura
│   └── tasks.md                             # Plan de implementación
├── infrastructure/                          # Configuración AWS
│   ├── dynamodb-table.yaml                 # Setup DynamoDB
│   ├── configmap.yaml                      # Configuración K8s
│   └── deploy.sh                           # Script de despliegue
├── controller/                             # Backend API
│   ├── simple_controller.py                # Base Flask (a convertir a FastAPI)
│   └── requirements.txt                    # Dependencias Python
├── frontend/                               # Frontend React
│   ├── src/                               # Código fuente
│   └── package.json                       # Dependencias Node.js
├── tests/                                  # Tests del sistema
│   └── properties/                         # Property-based tests
└── oldversion/                            # Respaldo del proyecto anterior
```

## 🎯 Estado Actual

### ✅ Completado
- [x] **Infraestructura AWS**: DynamoDB, S3, IAM configurados
- [x] **Dockerfiles**: Controlador y frontend con seguridad optimizada
- [x] **Pipeline CI/CD**: GitHub Actions con OIDC, escaneo de seguridad
- [x] **GitOps ArgoCD**: Aplicaciones separadas frontend/backend, sync automático
- [x] **Manifiestos K8s**: Deployments, services, ingress separados por componente
- [x] **Framework Frontend**: React + TypeScript + Material-UI configurado
- [x] **Base Backend**: Flask simple con DynamoDB (a convertir a FastAPI)
- [x] **Monitoreo**: Configuración Prometheus/Grafana
- [x] **Desarrollo Local**: Docker Compose para desarrollo
- [x] **Pipeline CI/CD**: GitHub Actions con OIDC, despliegue directo a EKS, escaneo de seguridad
- [x] **Framework Frontend**: React + TypeScript + Material-UI configurado
- [x] **Base Backend**: Flask simple con DynamoDB (a convertir a FastAPI)
- [x] **Monitoreo**: Configuración Prometheus/Grafana
- [x] **Desarrollo Local**: Docker Compose para desarrollo

### 🔄 En Progreso
- [ ] **Dockerfile Frontend**: Optimización con nginx y headers de seguridad
- [ ] **API FastAPI**: Conversión de Flask a FastAPI con logging estructurado
- [ ] **Validaciones**: Centros de costo, límites, horarios, resilencia
- [ ] **Frontend**: Páginas e integración con API
- [ ] **Scheduler**: Automatización de encendido/apagado con circuit breaker
- [ ] **Tests**: Property-based tests y tests de integración

## 🚀 Próximos Pasos

1. **Crear Dockerfile Frontend optimizado** (Tarea 2.2)
2. **Configurar Pipeline CI/CD** (Tarea 3.1, 3.2, 3.3) ✅ **COMPLETADO**
3. **Convertir Flask a FastAPI** (Tarea 4.1, 4.3)
4. **Implementar monitoreo y resilencia** (Tareas 5, 6)
5. **Implementar validaciones de negocio** (Tarea 7)
6. **Crear páginas del frontend** (Tarea 10)
7. **Implementar scheduler automático** (Tarea 11)

## 🛠️ Desarrollo

### Requisitos
- Python 3.11+
- Node.js 18+
- Docker y Docker Compose
- AWS CLI configurado
- kubectl configurado

### Configuración Docker

#### Controlador (Backend)
El Dockerfile del controlador implementa las mejores prácticas de seguridad:

**Características de Seguridad:**
- **Multi-stage build**: Separación entre build y runtime para minimizar superficie de ataque
- **Usuario no-root**: Ejecuta como usuario `appuser` (UID 1001) con permisos mínimos
- **Imagen base slim**: Python 3.11-slim para reducir vulnerabilidades
- **Dependencias mínimas**: Solo instala dependencias de runtime necesarias
- **Tini init system**: Manejo apropiado de señales y procesos zombie

**Optimizaciones:**
- **Kubectl integrado**: Descarga y verifica kubectl v1.29.0 con checksums
- **Multi-arquitectura**: Soporte para AMD64 y ARM64
- **Cache de pip**: Optimización de builds con cache de dependencias
- **Health checks**: Endpoint `/health` en puerto 8080 con reintentos
- **Logs estructurados**: Variables de entorno para logging optimizado

**Configuración de Runtime:**
```dockerfile
# Puerto expuesto para API y métricas
EXPOSE 8080

# Health check cada 30s con timeout de 10s
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3

# Comando por defecto (FastAPI con uvicorn)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
```

#### Frontend
- **Pendiente**: Dockerfile optimizado con nginx y headers de seguridad (Tarea 2.2)

### Inicio Rápido
```bash
# Clonar y configurar
git clone <repository>
cd namespace-startup-scheduler
make setup

# Desarrollo local con Docker Compose
make dev-up

# Acceder a los servicios
# - API: http://localhost:8080
# - Frontend: http://localhost:3000  
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001 (admin/admin)

# Ejecutar tests
make test

# Linting y formato
make lint
make format

# Parar desarrollo local
make dev-down
```

### Comandos Disponibles
```bash
make help          # Ver todos los comandos disponibles
make setup          # Configurar entorno de desarrollo
make dev-up         # Iniciar entorno local
make test           # Ejecutar todos los tests
make build          # Construir imágenes Docker
make security-scan  # Escaneo de seguridad
make clean          # Limpiar archivos generados
```

## 📖 Documentación

Ver la documentación completa en `.kiro/specs/namespace-startup-scheduler/`:
- `requirements.md` - Requisitos funcionales detallados (12 requisitos)
- `design.md` - Arquitectura y diseño técnico con resilencia
- `tasks.md` - Plan de implementación paso a paso (14 tareas)

## 🏗️ Arquitectura Completa

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                           │
│  GitHub Actions → OIDC → ECR → Git → ArgoCD → EKS         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Application Layer                           │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)    │    API (FastAPI)    │   Scheduler    │
│  - Material-UI       │    - Pydantic       │   - Lambda     │
│  - TypeScript        │    - Structured     │   - EventBridge│
│  - Real-time updates │      Logging        │   - kubectl    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Resilience Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Circuit Breaker     │    Retry Logic      │   Cache Local  │
│  - DynamoDB          │    - Exponential    │   - Config     │
│  - EKS API           │      Backoff        │   - State      │
│  - S3 Config         │    - Jitter         │   - Operations │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
├─────────────────────────────────────────────────────────────┤
│  DynamoDB           │    S3 Config        │   EKS Cluster   │
│  - Programaciones   │    - Centros Costo  │   - Namespaces  │
│  - GSI Optimizado   │    - Versionado     │   - kubectl     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Monitoring Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Prometheus         │    Grafana          │   Logs          │
│  - Métricas Custom  │    - Dashboards     │   - Structured  │
│  - Health Checks    │    - Alertas        │   - Correlation │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Licencia

MIT License