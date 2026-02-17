#!/usr/bin/env python3
"""
Script para poblar la tabla cost-center-permissions con centros de costo iniciales
Uso: python populate-cost-center-permissions.py [--environment production]
"""

import boto3
import argparse
import sys
import json
from botocore.exceptions import ClientError

def populate_cost_center_permissions(environment='production'):
    """
    Poblar la tabla cost-center-permissions con centros de costo iniciales
    """
    dynamodb = boto3.resource('dynamodb')
    table_name = f'cost-center-permissions-{environment}'
    
    try:
        table = dynamodb.Table(table_name)
        
        # Verificar que la tabla existe
        table.load()
        print(f"📋 Poblando tabla: {table_name}")
        
        # Centros de costo iniciales con configuración por defecto
        initial_cost_centers = [
            {
                'cost_center': 'IT-DEVELOPMENT',
                'codigo-cost-center': 'C102000001',
                'is_authorized': True,
                'max_concurrent_namespaces': 10,
                'authorized_namespaces': ['dev-*', 'test-*', 'staging-*'],
                'description': 'Centro de costo para desarrollo de TI'
            },
            {
                'cost_center': 'IT-PRODUCTION',
                'codigo-cost-center': 'C102000002',
                'is_authorized': True,
                'max_concurrent_namespaces': 5,
                'authorized_namespaces': ['prod-*', 'production-*'],
                'description': 'Centro de costo para producción de TI'
            },
            {
                'cost_center': 'QA-TESTING',
                'codigo-cost-center': 'C102000003',
                'is_authorized': True,
                'max_concurrent_namespaces': 8,
                'authorized_namespaces': ['qa-*', 'test-*', 'e2e-*'],
                'description': 'Centro de costo para testing y QA'
            },
            {
                'cost_center': 'DEVOPS-INFRA',
                'codigo-cost-center': 'C102000004',
                'is_authorized': True,
                'max_concurrent_namespaces': 15,
                'authorized_namespaces': ['*'],  # Acceso completo
                'description': 'Centro de costo para infraestructura DevOps'
            },
            {
                'cost_center': 'DEMO-SANDBOX',
                'codigo-cost-center': 'C102000005',
                'is_authorized': True,
                'max_concurrent_namespaces': 3,
                'authorized_namespaces': ['demo-*', 'sandbox-*'],
                'description': 'Centro de costo para demos y sandbox'
            },
            {
                'cost_center': 'EXTERNAL-CONTRACTOR',
                'codigo-cost-center': 'C102000006',
                'is_authorized': False,
                'max_concurrent_namespaces': 2,
                'authorized_namespaces': ['contractor-*'],
                'description': 'Centro de costo para contratistas externos (deshabilitado por defecto)'
            }
        ]
        
        # Insertar cada centro de costo
        for cost_center_data in initial_cost_centers:
            # Agregar timestamps
            import time
            cost_center_data['created_at'] = int(time.time())
            cost_center_data['updated_at'] = int(time.time())
            
            try:
                # Usar put_item con condition para no sobrescribir si ya existe
                table.put_item(
                    Item=cost_center_data,
                    ConditionExpression='attribute_not_exists(cost_center)'
                )
                status = "✅ Creado"
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    status = "⚠️  Ya existe"
                else:
                    raise e
            
            print(f"   {status}: {cost_center_data['cost_center']} - {cost_center_data['description']}")
        
        print(f"\n📊 Resumen de centros de costo:")
        
        # Mostrar todos los centros de costo en la tabla
        response = table.scan()
        items = response['Items']
        
        print(f"   Total de centros de costo: {len(items)}")
        print(f"   Autorizados: {len([item for item in items if item.get('is_authorized', False)])}")
        print(f"   No autorizados: {len([item for item in items if not item.get('is_authorized', False)])}")
        
        print(f"\n🔍 Detalle de centros de costo:")
        for item in sorted(items, key=lambda x: x['cost_center']):
            auth_status = "✅ Autorizado" if item.get('is_authorized', False) else "❌ No autorizado"
            max_ns = item.get('max_concurrent_namespaces', 0)
            namespaces = ', '.join(item.get('authorized_namespaces', []))
            print(f"   {item['cost_center']}: {auth_status}, Max NS: {max_ns}, Patrones: [{namespaces}]")
        
        return len(items)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"❌ Error: La tabla {table_name} no existe")
            print(f"   Ejecuta primero: python create_dynamodb_table.py --table permissions")
            sys.exit(1)
        else:
            print(f"❌ Error accediendo a la tabla: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Poblar tabla cost-center-permissions con datos iniciales')
    parser.add_argument('--environment', '-e', default='production', 
                       help='Entorno (default: production)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Mostrar qué se haría sin ejecutar cambios')
    
    args = parser.parse_args()
    
    # Verificar credenciales de AWS
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"🔐 Usando credenciales AWS para: {identity.get('Arn', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: No se pudieron obtener las credenciales de AWS")
        print(f"   Ejecuta: aws configure")
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 Modo dry-run: mostrando qué se haría...")
        # TODO: Implementar dry-run si es necesario
        print("   (Funcionalidad dry-run no implementada)")
        return
    
    count = populate_cost_center_permissions(args.environment)
    print(f"\n✨ Proceso completado. {count} centros de costo configurados.")
    print(f"\n💡 Consejos:")
    print(f"   - Usa el endpoint POST /api/cost-centers/<id>/permissions para modificar permisos")
    print(f"   - Los patrones de namespaces soportan wildcards (*)")
    print(f"   - Los centros de costo no autorizados no pueden activar namespaces")

if __name__ == '__main__':
    main()