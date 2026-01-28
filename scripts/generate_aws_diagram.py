#!/usr/bin/env python3
"""
Script para generar diagramas de arquitectura AWS usando la librería diagrams
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SNS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.security import IAM
from diagrams.aws.storage import S3
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.container import Docker
from diagrams.k8s.compute import Pod, Deployment
from diagrams.k8s.network import Service
from diagrams.k8s.rbac import ServiceAccount
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.gitops import ArgoCD

def create_namespace_autoshutdown_diagram():
    """Crear diagrama de arquitectura del sistema de apagado automático"""
    
    with Diagram("Sistema de Apagado Automático de Namespaces", 
                 filename="docs/architecture_aws_diagram", 
                 show=False,
                 direction="TB"):
        
        # GitHub y CI/CD
        with Cluster("GitHub & CI/CD"):
            github = GithubActions("GitHub Actions")
            
        # AWS Services
        with Cluster("AWS Cloud"):
            with Cluster("Identity & Access"):
                iam = IAM("OIDC Provider\n& IAM Role")
                
            with Cluster("Container Registry"):
                ecr = ECR("Amazon ECR\nContainer Images")
                
            with Cluster("Database"):
                dynamodb = Dynamodb("DynamoDB\nNamespace Schedules")
                
            with Cluster("Monitoring & Notifications"):
                cloudwatch = Cloudwatch("CloudWatch\nLogs & Metrics")
                sns = SNS("SNS\nNotifications")
                email_service = S3("Email Service\n(SES/SMTP)")
        
        # Kubernetes Cluster
        with Cluster("Kubernetes Cluster"):
            with Cluster("Encendido EKS Namespace"):
                controller_sa = ServiceAccount("Service Account")
                controller_deploy = Deployment("Controller\nDeployment")
                controller_svc = Service("Controller\nService")
                
                frontend_deploy = Deployment("Frontend\nDeployment")
                frontend_svc = Service("Frontend\nService")
                
            with Cluster("Monitoring Stack"):
                prometheus = Prometheus("Prometheus\nMetrics")
                grafana = Grafana("Grafana\nDashboards")
                
            with Cluster("GitOps"):
                argocd = ArgoCD("ArgoCD\nDeployments")
                
            with Cluster("Target Workloads"):
                target_pods = [
                    Pod("Namespace 1\nPods"),
                    Pod("Namespace 2\nPods"),
                    Pod("Namespace N\nPods")
                ]
        
        # Conexiones principales
        github >> Edge(label="OIDC Auth") >> iam
        github >> Edge(label="Push Images") >> ecr
        
        ecr >> Edge(label="Pull Images") >> controller_deploy
        ecr >> Edge(label="Pull Images") >> frontend_deploy
        
        controller_deploy >> Edge(label="Read/Write\nSchedules") >> dynamodb
        controller_deploy >> Edge(label="Send Logs") >> cloudwatch
        controller_deploy >> Edge(label="Expose Metrics") >> prometheus
        
        # Scaling operations
        for pod in target_pods:
            controller_deploy >> Edge(label="Scale\nOperations") >> pod
            
        # Monitoring flow
        prometheus >> Edge(label="Query Data") >> grafana
        prometheus >> Edge(label="Trigger Alerts") >> sns
        sns >> Edge(label="Email Delivery") >> email_service
        
        # GitOps flow
        argocd >> Edge(label="Deploy") >> controller_deploy
        argocd >> Edge(label="Deploy") >> frontend_deploy
        
        # Service connections
        controller_deploy >> controller_svc
        frontend_deploy >> frontend_svc
        controller_sa >> controller_deploy

def create_cost_optimization_diagram():
    """Crear diagrama enfocado en optimización de costos"""
    
    with Diagram("Optimización de Costos con Karpenter", 
                 filename="docs/cost_optimization_diagram", 
                 show=False,
                 direction="LR"):
        
        # Timeline
        with Cluster("Horario Laboral (8AM-3PM)"):
            active_pods = [Pod("Active Pod 1"), Pod("Active Pod 2"), Pod("Active Pod 3")]
            
        with Cluster("Fuera de Horario (3PM-8AM)"):
            scaled_pods = [Pod("Scaled to 0"), Pod("Scaled to 0"), Pod("Scaled to 0")]
            
        # Karpenter
        with Cluster("Karpenter Node Management"):
            nodes_active = ECS("EC2 Nodes\n(Active)")
            nodes_scaled = ECS("EC2 Nodes\n(Scaled Down)")
            
        # Cost representation
        with Cluster("Ahorro de Costos"):
            cost_active = S3("Costo Alto\n$$$")
            cost_optimized = S3("Costo Optimizado\n$")
            
        # Connections
        for pod in active_pods:
            pod >> nodes_active
        nodes_active >> cost_active
        
        for pod in scaled_pods:
            pod >> nodes_scaled
        nodes_scaled >> cost_optimized

def create_monitoring_diagram():
    """Crear diagrama del stack de monitoreo"""
    
    with Diagram("Stack de Monitoreo y Observabilidad", 
                 filename="docs/monitoring_stack_diagram", 
                 show=False,
                 direction="TB"):
        
        # Applications
        with Cluster("Aplicaciones"):
            controller = Pod("Controller")
            frontend = Pod("Frontend")
            
        # Metrics & Logs
        with Cluster("Métricas y Logs"):
            prometheus = Prometheus("Prometheus\nMetrics Server")
            cloudwatch = Cloudwatch("CloudWatch\nLogs")
            
        # Dashboards & Alerts
        with Cluster("Visualización y Alertas"):
            grafana = Grafana("Grafana\nDashboards")
            sns = SNS("SNS\nAlert Delivery")
            
        # External notifications
        with Cluster("Notificaciones Externas"):
            email = S3("Email\nNotifications")
            slack = Docker("Slack\nIntegration")
            
        # Connections
        controller >> Edge(label="Metrics") >> prometheus
        frontend >> Edge(label="Metrics") >> prometheus
        controller >> Edge(label="Logs") >> cloudwatch
        frontend >> Edge(label="Logs") >> cloudwatch
        
        prometheus >> Edge(label="Query") >> grafana
        prometheus >> Edge(label="Alerts") >> sns
        
        sns >> Edge(label="Email") >> email
        sns >> Edge(label="Webhook") >> slack

if __name__ == "__main__":
    print("🎨 Generando diagramas de arquitectura AWS...")
    
    try:
        create_namespace_autoshutdown_diagram()
        print("✅ Diagrama principal generado: docs/architecture_aws_diagram.png")
        
        create_cost_optimization_diagram()
        print("✅ Diagrama de costos generado: docs/cost_optimization_diagram.png")
        
        create_monitoring_diagram()
        print("✅ Diagrama de monitoreo generado: docs/monitoring_stack_diagram.png")
        
        print("\n🎉 ¡Todos los diagramas generados exitosamente!")
        
    except ImportError as e:
        print(f"❌ Error: Falta instalar la librería diagrams")
        print(f"Ejecuta: pip install diagrams")
        print(f"Detalles: {e}")
    except Exception as e:
        print(f"❌ Error generando diagramas: {e}")