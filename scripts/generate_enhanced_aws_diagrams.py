#!/usr/bin/env python3
"""
Script mejorado para generar diagramas de arquitectura AWS con información detallada
Usa información específica de servicios AWS para crear diagramas más precisos
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, ECR, Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SNS, SQS
from diagrams.aws.management import Cloudwatch, CloudwatchLogs
from diagrams.aws.security import IAM, IAMRole
from diagrams.aws.storage import S3
from diagrams.aws.network import VPC, PrivateSubnet, PublicSubnet, InternetGateway
from diagrams.aws.cost import CostExplorer
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.container import Docker
from diagrams.k8s.compute import Pod, Deployment, Job
from diagrams.k8s.network import Service, Ingress
from diagrams.k8s.rbac import ServiceAccount, ClusterRole
from diagrams.k8s.storage import PV, PVC
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.gitops import ArgoCD

def create_detailed_architecture_diagram():
    """Crear diagrama detallado con información específica de AWS"""
    
    with Diagram("Arquitectura Detallada - Sistema de Apagado Automático", 
                 filename="docs/detailed_architecture_diagram", 
                 show=False,
                 direction="TB",
                 graph_attr={"fontsize": "12", "bgcolor": "white"}):
        
        # GitHub CI/CD Pipeline
        with Cluster("🔄 CI/CD Pipeline"):
            github_repo = GithubActions("GitHub Repository\nbcocbo/apagado-automatico")
            
        # AWS Cloud Infrastructure
        with Cluster("☁️ AWS Cloud Infrastructure"):
            
            # Identity and Access Management
            with Cluster("🔐 Identity & Access Management"):
                oidc_provider = IAM("OIDC Identity Provider\ntoken.actions.githubusercontent.com")
                github_role = IAMRole("GitHubActionsECRRole\nECR Push Permissions")
                controller_role = IAMRole("NamespaceControllerRole\nDynamoDB + CloudWatch")
                
            # Container Services
            with Cluster("📦 Container Registry & Compute"):
                ecr_controller = ECR("namespace-scaler\nController Images\nLifecycle: 7 days")
                ecr_frontend = ECR("namespace-frontend\nFrontend Images\nLifecycle: 7 days")
                
            # Database Layer
            with Cluster("🗄️ Database Services"):
                dynamodb_table = Dynamodb("NamespaceSchedules\nPay-per-request\nPoint-in-time Recovery")
                
            # Monitoring & Logging
            with Cluster("📊 Monitoring & Logging"):
                cloudwatch_logs = CloudwatchLogs("Log Groups\n/aws/kubernetes/namespace-controller\nRetention: 30 days")
                cloudwatch_metrics = Cloudwatch("Custom Metrics\nScaling Operations\nError Rates")
                
            # Notification Services
            with Cluster("🔔 Notification Services"):
                sns_alerts = SNS("namespace-controller-alerts\nEmail + Webhook")
                cost_explorer = CostExplorer("Cost Optimization\nSavings Tracking")
                
        # Kubernetes Cluster
        with Cluster("☸️ Kubernetes Cluster (EKS/Self-managed)"):
            
            # Encendido EKS Namespace
            with Cluster("🎛️ encendido-eks Namespace"):
                # RBAC
                service_account = ServiceAccount("scaler-sa")
                cluster_role = ClusterRole("namespace-scaler-role\nnamespaces: get,list\ndeployments: get,list,patch,update\nevents: create")
                
                # Controller Components
                controller_deployment = Deployment("namespace-scaler\nReplicas: 1\nResources: 128Mi/100m")
                controller_service = Service("namespace-scaler-service\nPorts: 8080 (metrics), 8081 (health)")
                
                # Frontend Components
                frontend_deployment = Deployment("namespace-frontend\nReplicas: 2\nNginx + React")
                frontend_service = Service("frontend-service\nPort: 8080")
                frontend_ingress = Ingress("frontend-ingress\nTLS + Security Headers")
                
            # Monitoring Stack
            with Cluster("📈 Monitoring Stack"):
                prometheus_server = Prometheus("Prometheus Server\nMetrics Collection\nRetention: 15 days")
                grafana_dashboard = Grafana("Grafana Dashboards\n• System Overview\n• Operations\n• Cost Savings")
                alertmanager = Grafana("AlertManager\nSlack + Email + SNS")
                
            # GitOps
            with Cluster("🚀 GitOps Deployment"):
                argocd_server = ArgoCD("ArgoCD Applications\n• apagado-controller\n• apagado-frontend\n• apagado-policies")
                
            # Target Workloads
            with Cluster("🎯 Target Namespaces"):
                target_workloads = [
                    Deployment("production-app\nAuto-scaled"),
                    Deployment("staging-env\nAuto-scaled"),
                    Deployment("development\nAuto-scaled")
                ]
                
        # External Integrations
        with Cluster("🌐 External Integrations"):
            slack_webhook = Docker("Slack Notifications\nAlert Channel")
            email_smtp = Docker("Email SMTP\nOperations Team")
            
        # Main Flow Connections
        github_repo >> Edge(label="1. OIDC Auth", style="bold", color="green") >> oidc_provider
        oidc_provider >> Edge(label="2. Assume Role") >> github_role
        github_repo >> Edge(label="3. Push Images", style="bold", color="blue") >> [ecr_controller, ecr_frontend]
        
        # Container Deployment
        ecr_controller >> Edge(label="4. Pull Image") >> controller_deployment
        ecr_frontend >> Edge(label="4. Pull Image") >> frontend_deployment
        
        # RBAC Connections
        service_account >> Edge(label="RBAC") >> cluster_role
        service_account >> controller_deployment
        controller_role >> Edge(label="AWS Permissions") >> controller_deployment
        
        # Data Flow
        controller_deployment >> Edge(label="5. Read/Write Schedules", color="orange") >> dynamodb_table
        controller_deployment >> Edge(label="6. Send Logs", color="purple") >> cloudwatch_logs
        controller_deployment >> Edge(label="7. Custom Metrics", color="red") >> cloudwatch_metrics
        
        # Scaling Operations
        for workload in target_workloads:
            controller_deployment >> Edge(label="Scale 0↔N", color="red", style="dashed") >> workload
            
        # Monitoring Flow
        controller_deployment >> Edge(label="8. Expose Metrics") >> prometheus_server
        frontend_deployment >> Edge(label="8. Expose Metrics") >> prometheus_server
        prometheus_server >> Edge(label="9. Query Data") >> grafana_dashboard
        prometheus_server >> Edge(label="10. Trigger Alerts") >> alertmanager
        
        # Alert Delivery
        alertmanager >> Edge(label="11. Notifications") >> sns_alerts
        sns_alerts >> Edge(label="12. Deliver") >> [slack_webhook, email_smtp]
        
        # GitOps Flow
        argocd_server >> Edge(label="Deploy", color="green") >> [controller_deployment, frontend_deployment]
        
        # Service Connections
        controller_deployment >> controller_service
        frontend_deployment >> frontend_service
        frontend_service >> frontend_ingress
        
        # Cost Tracking
        target_workloads[0] >> Edge(label="Cost Savings", style="dotted", color="green") >> cost_explorer

def create_security_architecture_diagram():
    """Crear diagrama enfocado en seguridad y compliance"""
    
    with Diagram("Arquitectura de Seguridad y Compliance", 
                 filename="docs/security_architecture_diagram", 
                 show=False,
                 direction="LR"):
        
        # Security Layers
        with Cluster("🔒 Security Layers"):
            
            # Network Security
            with Cluster("🌐 Network Security"):
                vpc = VPC("VPC\nPrivate Networking")
                private_subnet = PrivateSubnet("Private Subnets\nK8s Nodes")
                public_subnet = PublicSubnet("Public Subnets\nLoad Balancers")
                igw = InternetGateway("Internet Gateway\nControlled Access")
                
            # Identity Security
            with Cluster("👤 Identity & Access"):
                oidc_security = IAM("OIDC Provider\nNo Long-term Keys")
                role_security = IAMRole("Least Privilege Roles\nTime-limited Tokens")
                
            # Container Security
            with Cluster("📦 Container Security"):
                ecr_security = ECR("ECR Repositories\nVulnerability Scanning\nImage Signing")
                
            # Runtime Security
            with Cluster("🏃 Runtime Security"):
                pod_security = Pod("Non-root Containers\nSecurity Contexts\nResource Limits")
                rbac_security = ClusterRole("RBAC Policies\nMinimal Permissions")
                
        # Security Controls
        with Cluster("🛡️ Security Controls"):
            scanning = Docker("Trivy Scanner\nCVE Detection\nPolicy Enforcement")
            monitoring = Cloudwatch("Security Monitoring\nAudit Logs\nAnomaly Detection")
            
        # Compliance
        with Cluster("📋 Compliance"):
            audit_logs = CloudwatchLogs("Audit Trails\nAPI Calls\nAccess Logs")
            compliance_check = Lambda("Compliance Checks\nPolicy Validation\nReporting")
            
        # Security Flow
        oidc_security >> role_security >> ecr_security
        ecr_security >> scanning >> pod_security
        pod_security >> rbac_security >> monitoring
        monitoring >> audit_logs >> compliance_check

def create_cost_optimization_detailed_diagram():
    """Crear diagrama detallado de optimización de costos"""
    
    with Diagram("Optimización de Costos - Análisis Detallado", 
                 filename="docs/cost_optimization_detailed_diagram", 
                 show=False,
                 direction="TB"):
        
        # Time-based Cost Analysis
        with Cluster("⏰ Análisis de Costos por Tiempo"):
            
            with Cluster("🌅 Horario Laboral (8AM-3PM) - 35h/semana"):
                active_workloads = [
                    Deployment("Prod Apps\n3 replicas\n$120/mes"),
                    Deployment("Staging\n2 replicas\n$80/mes"),
                    Deployment("Dev\n1 replica\n$40/mes")
                ]
                active_nodes = ECS("EC2 Nodes Activos\n3 x m5.large\n$180/mes")
                
            with Cluster("🌙 Fuera de Horario (3PM-8AM) - 133h/semana"):
                scaled_workloads = [
                    Pod("Prod Apps\n0 replicas\n$0/mes"),
                    Pod("Staging\n0 replicas\n$0/mes"),
                    Pod("Dev\n0 replicas\n$0/mes")
                ]
                scaled_nodes = ECS("EC2 Nodes Mínimos\n1 x t3.small\n$15/mes")
                
        # Cost Components
        with Cluster("💰 Componentes de Costo"):
            
            # Infrastructure Costs
            with Cluster("🏗️ Infraestructura"):
                compute_cost = CostExplorer("Compute\nAntes: $240/mes\nDespués: $75/mes\nAhorro: 69%")
                storage_cost = S3("Storage\nEBS: $30/mes\nECR: $5/mes")
                network_cost = VPC("Network\nData Transfer: $10/mes")
                
            # Service Costs
            with Cluster("🔧 Servicios AWS"):
                dynamodb_cost = Dynamodb("DynamoDB\nPay-per-request\n~$2/mes")
                cloudwatch_cost = Cloudwatch("CloudWatch\nLogs + Metrics\n~$8/mes")
                
        # Savings Calculation
        with Cluster("📊 Cálculo de Ahorros"):
            total_before = CostExplorer("Costo Total Antes\n$295/mes")
            total_after = CostExplorer("Costo Total Después\n$100/mes")
            monthly_savings = CostExplorer("Ahorro Mensual\n$195/mes (66%)")
            annual_savings = CostExplorer("Ahorro Anual\n$2,340/año")
            
        # Cost Flow
        for workload in active_workloads:
            workload >> active_nodes
        active_nodes >> compute_cost
        
        for workload in scaled_workloads:
            workload >> scaled_nodes
        scaled_nodes >> compute_cost
        
        # Total calculations
        [compute_cost, storage_cost, network_cost, dynamodb_cost, cloudwatch_cost] >> total_before
        total_before >> Edge(label="Optimización", color="green") >> total_after
        total_after >> monthly_savings >> annual_savings

def create_operational_workflow_diagram():
    """Crear diagrama del flujo operacional completo"""
    
    with Diagram("Flujo Operacional Completo", 
                 filename="docs/operational_workflow_diagram", 
                 show=False,
                 direction="LR"):
        
        # Development Workflow
        with Cluster("👨‍💻 Desarrollo"):
            dev_commit = GithubActions("Git Commit\nCode Changes")
            pr_review = GithubActions("Pull Request\nCode Review")
            
        # CI/CD Pipeline
        with Cluster("🔄 CI/CD Pipeline"):
            lint_test = GithubActions("Lint & Test\nYAML + Security")
            build_push = GithubActions("Build & Push\nDocker Images")
            deploy = GithubActions("Deploy\nArgoCD Sync")
            
        # Runtime Operations
        with Cluster("🏃 Runtime Operations"):
            schedule_check = Job("Schedule Check\nEvery 5 minutes")
            scaling_operation = Lambda("Scaling Logic\nScale Up/Down")
            health_check = Service("Health Monitoring\nLiveness/Readiness")
            
        # Monitoring & Alerting
        with Cluster("📊 Monitoring"):
            metrics_collection = Prometheus("Metrics Collection\nReal-time Data")
            alert_evaluation = Grafana("Alert Rules\nThreshold Monitoring")
            notification = SNS("Notifications\nSlack + Email")
            
        # Incident Response
        with Cluster("🚨 Incident Response"):
            alert_received = Docker("Alert Received\nOps Team")
            investigation = Docker("Investigation\nLogs + Metrics")
            resolution = Docker("Resolution\nManual/Automatic")
            
        # Workflow connections
        dev_commit >> pr_review >> lint_test >> build_push >> deploy
        deploy >> schedule_check >> scaling_operation >> health_check
        health_check >> metrics_collection >> alert_evaluation >> notification
        notification >> alert_received >> investigation >> resolution

if __name__ == "__main__":
    print("🎨 Generando diagramas mejorados con información detallada de AWS...")
    
    try:
        create_detailed_architecture_diagram()
        print("✅ Diagrama detallado generado: docs/detailed_architecture_diagram.png")
        
        create_security_architecture_diagram()
        print("✅ Diagrama de seguridad generado: docs/security_architecture_diagram.png")
        
        create_cost_optimization_detailed_diagram()
        print("✅ Diagrama de costos detallado generado: docs/cost_optimization_detailed_diagram.png")
        
        create_operational_workflow_diagram()
        print("✅ Diagrama de flujo operacional generado: docs/operational_workflow_diagram.png")
        
        print("\n🎉 ¡Todos los diagramas mejorados generados exitosamente!")
        print("\n📊 Diagramas disponibles:")
        print("• detailed_architecture_diagram.png - Arquitectura completa con detalles")
        print("• security_architecture_diagram.png - Enfoque en seguridad y compliance")
        print("• cost_optimization_detailed_diagram.png - Análisis detallado de costos")
        print("• operational_workflow_diagram.png - Flujo operacional completo")
        
    except ImportError as e:
        print(f"❌ Error: Falta instalar la librería diagrams")
        print(f"Ejecuta: pip install diagrams")
        print(f"Detalles: {e}")
    except Exception as e:
        print(f"❌ Error generando diagramas: {e}")
        import traceback
        traceback.print_exc()