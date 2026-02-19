#!/usr/bin/env python3
"""
Script para crear tareas por defecto del sistema
Crea tareas de encendido (8 AM) y apagado (6 PM) para namespaces críticos
"""

import json
import uuid
from datetime import datetime
import sys
import os

# Agregar el directorio actual al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def generate_task_id():
    """Genera un ID único para la tarea"""
    return str(uuid.uuid4())

def create_default_tasks():
    """
    Crea las tareas por defecto para namespaces del sistema
    """
    
    # Namespaces críticos que deben estar siempre encendidos en horario laboral
    critical_namespaces = [
        # Namespaces de sistema
        'kube-system',
        'monitoring', 
        'argocd',
        'istio-system',
        'karpenter',
        
        # Namespaces específicos mencionados
        'keda',
        'task-scheduler'
    ]
    
    # Namespaces de ingress (pueden tener nombres variables)
    ingress_namespaces = [
        'istio-system',  # Ya incluido arriba, pero es el ingress principal
        'ingress-nginx'  # Por si existe un namespace específico de nginx
    ]
    
    # Combinar todos los namespaces únicos
    all_namespaces = list(set(critical_namespaces + ingress_namespaces))
    
    tasks = []
    
    for namespace in all_namespaces:
        # Tarea de ENCENDIDO - 8:00 AM días laborales
        activate_task = {
            "id": generate_task_id(),
            "title": f"Activar {namespace} - Horario Laboral",
            "description": f"Activación automática del namespace {namespace} al inicio del horario laboral",
            "operation_type": "activate",
            "namespace": namespace,
            "schedule": "0 8 * * 1-5",  # 8:00 AM, Lunes a Viernes
            "cost_center": "system",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "start": datetime.now().isoformat(),
            "allDay": False,
            "user_id": "system",
            "requested_by": "system-auto",
            "cluster_name": "eks-cloud",
            "auto_created": True,
            "system_task": True
        }
        
        # Tarea de APAGADO - 6:00 PM días laborales
        deactivate_task = {
            "id": generate_task_id(),
            "title": f"Desactivar {namespace} - Fin Horario Laboral", 
            "description": f"Desactivación automática del namespace {namespace} al final del horario laboral",
            "operation_type": "deactivate",
            "namespace": namespace,
            "schedule": "0 18 * * 1-5",  # 6:00 PM, Lunes a Viernes
            "cost_center": "system",
            "status": "pending", 
            "created_at": datetime.now().isoformat(),
            "start": datetime.now().isoformat(),
            "allDay": False,
            "user_id": "system",
            "requested_by": "system-auto",
            "cluster_name": "eks-cloud",
            "auto_created": True,
            "system_task": True
        }
        
        tasks.append(activate_task)
        tasks.append(deactivate_task)
    
    return tasks

def save_tasks_to_file(tasks, filename="default_tasks.json"):
    """
    Guarda las tareas en un archivo JSON
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {len(tasks)} tareas guardadas en {filename}")

def print_tasks_summary(tasks):
    """
    Muestra un resumen de las tareas creadas
    """
    print("\n📋 RESUMEN DE TAREAS CREADAS:")
    print("=" * 60)
    
    activate_tasks = [t for t in tasks if t['operation_type'] == 'activate']
    deactivate_tasks = [t for t in tasks if t['operation_type'] == 'deactivate']
    
    print(f"🟢 Tareas de ACTIVACIÓN (8:00 AM): {len(activate_tasks)}")
    for task in activate_tasks:
        print(f"   • {task['namespace']}")
    
    print(f"\n🔴 Tareas de DESACTIVACIÓN (6:00 PM): {len(deactivate_tasks)}")
    for task in deactivate_tasks:
        print(f"   • {task['namespace']}")
    
    print(f"\n📊 TOTAL: {len(tasks)} tareas")
    print("⏰ Horario: Lunes a Viernes, 8:00 AM - 6:00 PM")
    print("🏢 Centro de Costo: system")
    print("🤖 Usuario: system-auto")

def create_api_payload(tasks):
    """
    Crea el payload para enviar las tareas via API
    """
    return {
        "tasks": tasks,
        "batch_create": True,
        "source": "system-default",
        "created_by": "system-auto"
    }

if __name__ == "__main__":
    print("🚀 Generando tareas por defecto del sistema...")
    print("=" * 60)
    
    # Crear las tareas
    tasks = create_default_tasks()
    
    # Mostrar resumen
    print_tasks_summary(tasks)
    
    # Guardar en archivo
    save_tasks_to_file(tasks, "default_system_tasks.json")
    
    # Crear payload para API
    api_payload = create_api_payload(tasks)
    save_tasks_to_file([api_payload], "default_tasks_api_payload.json")
    
    print(f"\n✅ Archivos generados:")
    print(f"   • default_system_tasks.json - Tareas individuales")
    print(f"   • default_tasks_api_payload.json - Payload para API")
    
    print(f"\n📝 Para cargar las tareas, ejecuta:")
    print(f"   curl -X POST http://localhost:8080/api/tasks/batch \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d @default_tasks_api_payload.json")