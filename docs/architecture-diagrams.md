# Diagramas de Arquitectura - Sistema de Apagado Automático

## 1. Flujo General del Sistema

```mermaid
graph TB
    subgraph "Trigger Events"
        Timer[⏰ Timer - Cada 5 min]
        Manual[👤 Manual Override]
        Schedule[📅 Schedule Change]
    end
    
    subgraph "Controller Logic"
        Controller[🎛️ Python Controller]
        Decision{🤔 ¿Dentro de horario?}
        ScaleUp[⬆️ Scale UP<br/>Replicas > 0]
        ScaleDown[⬇️ Scale DOWN<br/>Replicas = 0]
    end
    
    subgraph "Data Sources"
        DynamoDB[(🗄️ DynamoDB<br/>Schedules)]
        K8sAPI[☸️ Kubernetes API<br/>Deployments]
    end
    
    subgraph "Target Resources"
        NS1[📦 Namespace 1]
        NS2[📦 Namespace 2]
        NSN[📦 Namespace N]
    end
    
    subgraph "Monitoring"
        Metrics[📊 Prometheus<br/>Metrics]
        Logs[📝 CloudWatch<br/>Logs]
        Alerts[🚨 AlertManager<br/>Notifications]
    end
    
    Timer --> Controller
    Manual --> Controller
    Schedule --> Controller
    
    Controller --> DynamoDB
    Controller --> K8sAPI
    Controller --> Decision
    
    Decision -->|Sí| ScaleUp
    Decision -->|No| ScaleDown
    
    ScaleUp --> NS1
    ScaleUp --> NS2
    ScaleUp --> NSN
    
    ScaleDown --> NS1
    ScaleDown --> NS2
    ScaleDown --> NSN
    
    Controller --> Metrics
    Controller --> Logs
    Metrics --> Alerts
    
    style Controller fill:#e1f5fe
    style Decision fill:#fff3e0
    style ScaleUp fill:#e8f5e8
    style ScaleDown fill:#ffebee
```

## 2. Flujo de CI/CD Pipeline

```mermaid
graph LR
    subgraph "Source Control"
        Dev[👨‍💻 Developer]
        Repo[📁 GitHub Repo]
    end
    
    subgraph "CI Pipeline"
        Trigger[🔄 Push/PR Trigger]
        Lint[✅ YAML Lint]
        Security[🔒 Security Scan]
        Build[🏗️ Docker Build]
        Test[🧪 Tests]
    end
    
    subgraph "Authentication"
        OIDC[🔐 OIDC Provider]
        IAM[👤 AWS IAM Role]
    end
    
    subgraph "Container Registry"
        ECR[📦 AWS ECR]
    end
    
    subgraph "Deployment"
        ArgoCD[🚀 ArgoCD]
        K8s[☸️ Kubernetes]
    end
    
    Dev --> Repo
    Repo --> Trigger
    Trigger --> Lint
    Lint --> Security
    Security --> Build
    Build --> Test
    
    Build --> OIDC
    OIDC --> IAM
    IAM --> ECR
    
    ECR --> ArgoCD
    ArgoCD --> K8s
    
    style OIDC fill:#e8f5e8
    style Security fill:#fff3e0
    style ECR fill:#e1f5fe
```

## 3. Flujo de Decisión de Escalado

```mermaid
graph TD
    Start([🚀 Inicio del Ciclo])
    GetNS[📋 Obtener Namespaces]
    LoopNS{🔄 Para cada Namespace}
    
    CheckSchedule[📅 Verificar Schedule<br/>en DynamoDB]
    HasCustom{❓ ¿Tiene horario<br/>personalizado?}
    
    CheckCustomTime[⏰ Verificar horario<br/>personalizado]
    CheckDefaultTime[⏰ Verificar horario<br/>por defecto<br/>(Lun-Vie 8AM-3PM)]
    
    InWorkHours{🕐 ¿Dentro del<br/>horario laboral?}
    
    GetCurrentState[📊 Obtener estado<br/>actual deployments]
    
    NeedScaleUp{⬆️ ¿Necesita<br/>escalar UP?}
    NeedScaleDown{⬇️ ¿Necesita<br/>escalar DOWN?}
    
    SaveOriginal[💾 Guardar replicas<br/>originales]
    ScaleToZero[⬇️ Escalar a 0<br/>replicas]
    RestoreOriginal[⬆️ Restaurar replicas<br/>originales]
    
    LogEvent[📝 Log evento]
    SendMetrics[📊 Enviar métricas]
    
    NextNS[➡️ Siguiente Namespace]
    Wait[⏳ Esperar 5 minutos]
    
    Start --> GetNS
    GetNS --> LoopNS
    LoopNS -->|Sí| CheckSchedule
    LoopNS -->|No| Wait
    
    CheckSchedule --> HasCustom
    HasCustom -->|Sí| CheckCustomTime
    HasCustom -->|No| CheckDefaultTime
    
    CheckCustomTime --> InWorkHours
    CheckDefaultTime --> InWorkHours
    
    InWorkHours --> GetCurrentState
    GetCurrentState --> NeedScaleUp
    GetCurrentState --> NeedScaleDown
    
    NeedScaleUp -->|Sí| RestoreOriginal
    NeedScaleDown -->|Sí| SaveOriginal
    SaveOriginal --> ScaleToZero
    
    RestoreOriginal --> LogEvent
    ScaleToZero --> LogEvent
    NeedScaleUp -->|No| NextNS
    NeedScaleDown -->|No| NextNS
    
    LogEvent --> SendMetrics
    SendMetrics --> NextNS
    NextNS --> LoopNS
    
    Wait --> Start
    
    style InWorkHours fill:#fff3e0
    style ScaleToZero fill:#ffebee
    style RestoreOriginal fill:#e8f5e8
    style SaveOriginal fill:#e1f5fe
```

## 4. Arquitectura de Monitoreo

```mermaid
graph TB
    subgraph "Aplicaciones"
        Controller[🎛️ Controller]
        Frontend[🌐 Frontend]
    end
    
    subgraph "Métricas y Logs"
        PromMetrics[📊 Prometheus<br/>Metrics Endpoint]
        CloudWatch[☁️ CloudWatch<br/>Logs]
        StructLogs[📝 Structured<br/>Logging]
    end
    
    subgraph "Monitoreo Stack"
        Prometheus[📈 Prometheus<br/>Server]
        Grafana[📊 Grafana<br/>Dashboards]
        AlertManager[🚨 AlertManager]
    end
    
    subgraph "Notificaciones"
        Slack[💬 Slack]
        Email[📧 Email]
        SNS[📱 AWS SNS]
    end
    
    subgraph "Dashboards"
        SystemHealth[🏥 System Health]
        Operations[⚙️ Operations]
        CostSavings[💰 Cost Savings]
        Performance[⚡ Performance]
    end
    
    Controller --> PromMetrics
    Controller --> StructLogs
    Frontend --> PromMetrics
    
    StructLogs --> CloudWatch
    PromMetrics --> Prometheus
    
    Prometheus --> Grafana
    Prometheus --> AlertManager
    
    Grafana --> SystemHealth
    Grafana --> Operations
    Grafana --> CostSavings
    Grafana --> Performance
    
    AlertManager --> Slack
    AlertManager --> Email
    AlertManager --> SNS
    
    style Prometheus fill:#e8f5e8
    style AlertManager fill:#fff3e0
    style Grafana fill:#e1f5fe
```

## 5. Flujo de Manejo de Errores y Rollback

```mermaid
graph TD
    Operation[🔄 Operación de Escalado]
    Success{✅ ¿Exitosa?}
    
    UpdateMetrics[📊 Actualizar Métricas<br/>Exitosas]
    
    ErrorDetected[❌ Error Detectado]
    ErrorCount{🔢 ¿Errores > Umbral?}
    
    LogError[📝 Log Error]
    IncrementCounter[➕ Incrementar<br/>Contador Errores]
    
    TriggerRollback[🔄 Trigger Rollback]
    GetPreviousState[📋 Obtener Estado<br/>Anterior]
    
    RestoreState[⚡ Restaurar Estado<br/>Anterior]
    RollbackSuccess{✅ ¿Rollback<br/>Exitoso?}
    
    NotifyOps[📢 Notificar Equipo<br/>Operaciones]
    BlockOperations[🚫 Bloquear Nuevas<br/>Operaciones]
    
    ManualIntervention[👨‍🔧 Intervención<br/>Manual Requerida]
    
    ResetCounter[🔄 Reset Contador<br/>Errores]
    Continue[➡️ Continuar<br/>Operaciones]
    
    Operation --> Success
    Success -->|Sí| UpdateMetrics
    Success -->|No| ErrorDetected
    
    UpdateMetrics --> Continue
    
    ErrorDetected --> LogError
    LogError --> IncrementCounter
    IncrementCounter --> ErrorCount
    
    ErrorCount -->|No| Continue
    ErrorCount -->|Sí| TriggerRollback
    
    TriggerRollback --> GetPreviousState
    GetPreviousState --> RestoreState
    RestoreState --> RollbackSuccess
    
    RollbackSuccess -->|Sí| NotifyOps
    RollbackSuccess -->|No| ManualIntervention
    
    NotifyOps --> BlockOperations
    BlockOperations --> ResetCounter
    ResetCounter --> Continue
    
    ManualIntervention --> Continue
    
    style ErrorDetected fill:#ffebee
    style TriggerRollback fill:#fff3e0
    style RestoreState fill:#e8f5e8
    style ManualIntervention fill:#fce4ec
```

## 6. Flujo de Configuración de Horarios (Frontend)

```mermaid
graph LR
    subgraph "Usuario"
        User[👤 Usuario]
        Browser[🌐 Navegador]
    end
    
    subgraph "Frontend React"
        UI[🎨 React UI]
        ScheduleForm[📝 Schedule Form]
        Dashboard[📊 Dashboard]
    end
    
    subgraph "Backend API"
        API[🔌 Controller API]
        Validation[✅ Validación]
    end
    
    subgraph "Storage"
        DynamoDB[(🗄️ DynamoDB)]
    end
    
    subgraph "Real-time Updates"
        WebSocket[🔄 WebSocket]
        Notifications[🔔 Notificaciones]
    end
    
    User --> Browser
    Browser --> UI
    UI --> ScheduleForm
    UI --> Dashboard
    
    ScheduleForm --> API
    API --> Validation
    Validation --> DynamoDB
    
    DynamoDB --> WebSocket
    WebSocket --> Notifications
    Notifications --> Dashboard
    
    style ScheduleForm fill:#e1f5fe
    style Validation fill:#e8f5e8
    style WebSocket fill:#fff3e0
```

## Métricas Clave del Sistema

### Métricas de Operación
- `namespace_scaling_operations_total{namespace, operation, status}`
- `namespace_scaling_duration_seconds{namespace, operation}`
- `namespace_active_count`
- `controller_errors_total{error_type}`

### Métricas de Infraestructura
- `dynamodb_operations_total{operation, status}`
- `kubernetes_api_calls_total{operation, status}`
- `frontend_requests_total{method, endpoint, status}`

### Métricas de Negocio
- `cost_savings_estimated_dollars`
- `namespaces_managed_total`
- `uptime_percentage`

## Alertas Configuradas

### Críticas
- Controller Down (5 min)
- High Error Rate (>10% por 2 min)
- DynamoDB Throttling
- Kubernetes API Unreachable

### Advertencias
- Scaling Operation Failures
- High Response Times
- Resource Utilization High

### Informativas
- Daily Cost Savings Report
- Weekly Operations Summary