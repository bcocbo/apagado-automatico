#!/usr/bin/env python3
"""
Script para crear las tablas DynamoDB para namespace-scheduler
- task-scheduler-logs: Para logs de actividades
- cost-center-permissions: Para validación de centros de costo

Uso: 
  python create_dynamodb_table.py [--environment production] [--table all]
  python create_dynamodb_table.py --table logs
  python create_dynamodb_table.py --table permissions
"""

import boto3
import argparse
import sys
import time
from botocore.exceptions import ClientError

def create_cost_center_permissions_table(environment='production'):
    """
    Crea la tabla cost-center-permissions para validación de centros de costo
    """
    dynamodb = boto3.client('dynamodb')
    table_name = f'cost-center-permissions-{environment}'
    
    table_definition = {
        'TableName': table_name,
        'KeySchema': [
            {
                'AttributeName': 'cost_center',
                'KeyType': 'HASH'
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'cost_center',
                'AttributeType': 'S'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'namespace-scheduler'
            },
            {
                'Key': 'Environment',
                'Value': environment
            }
        ]
    }
    
    try:
        print(f"🚀 Creando tabla: {table_name}")
        response = dynamodb.create_table(**table_definition)
        
        print("⏳ Esperando que la tabla esté activa...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("✅ Tabla creada exitosamente")
        
        # Mostrar información de la tabla
        table_info = dynamodb.describe_table(TableName=table_name)['Table']
        print(f"\n📊 Información de la tabla:")
        print(f"   Nombre: {table_info['TableName']}")
        print(f"   Estado: {table_info['TableStatus']}")
        print(f"   ARN: {table_info['TableArn']}")
        print(f"   Modo de facturación: {table_info.get('BillingModeSummary', {}).get('BillingMode', 'N/A')}")
        
        print(f"\n🔍 Estructura:")
        print(f"   - Índice principal: cost_center (HASH)")
        print(f"   - Atributos: is_authorized, max_concurrent_namespaces, authorized_namespaces")
        
        return table_name
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"⚠️  La tabla {table_name} ya existe")
            return table_name
        else:
            print(f"❌ Error creando la tabla: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

def create_task_scheduler_logs_table(environment='production'):
    """
    Crea la tabla task-scheduler-logs con los índices apropiados
    """
    dynamodb = boto3.client('dynamodb')
    table_name = f'task-scheduler-logs-{environment}'
    
    table_definition = {
        'TableName': table_name,
        'KeySchema': [
            {
                'AttributeName': 'namespace_name',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'timestamp_start',
                'KeyType': 'RANGE'
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'namespace_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'timestamp_start',
                'AttributeType': 'N'
            },
            {
                'AttributeName': 'cost_center',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'operation_type',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'cluster_name',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'requested_by',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'cost-center-timestamp-index',
                'KeySchema': [
                    {
                        'AttributeName': 'cost_center',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp_start',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            },
            {
                'IndexName': 'operation-type-timestamp-index',
                'KeySchema': [
                    {
                        'AttributeName': 'operation_type',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp_start',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            },
            {
                'IndexName': 'cluster-timestamp-index',
                'KeySchema': [
                    {
                        'AttributeName': 'cluster_name',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp_start',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            },
            {
                'IndexName': 'requested-by-timestamp-index',
                'KeySchema': [
                    {
                        'AttributeName': 'requested_by',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp_start',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'StreamSpecification': {
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        'PointInTimeRecoverySpecification': {
            'PointInTimeRecoveryEnabled': True
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'namespace-scheduler'
            },
            {
                'Key': 'Environment',
                'Value': environment
            }
        ]
    }
    
    try:
        print(f"🚀 Creando tabla: {table_name}")
        response = dynamodb.create_table(**table_definition)
        
        print("⏳ Esperando que la tabla esté activa...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        # Esperar a que los GSI estén activos
        print("⏳ Esperando que los índices estén activos...")
        while True:
            table_description = dynamodb.describe_table(TableName=table_name)
            table_status = table_description['Table']['TableStatus']
            
            if table_status == 'ACTIVE':
                gsi_statuses = []
                if 'GlobalSecondaryIndexes' in table_description['Table']:
                    gsi_statuses = [gsi['IndexStatus'] for gsi in table_description['Table']['GlobalSecondaryIndexes']]
                
                if all(status == 'ACTIVE' for status in gsi_statuses):
                    break
            
            print("   Esperando...")
            time.sleep(10)
        
        print("✅ Tabla creada exitosamente")
        
        # Mostrar información de la tabla
        table_info = dynamodb.describe_table(TableName=table_name)['Table']
        print(f"\n📊 Información de la tabla:")
        print(f"   Nombre: {table_info['TableName']}")
        print(f"   Estado: {table_info['TableStatus']}")
        print(f"   ARN: {table_info['TableArn']}")
        print(f"   Modo de facturación: {table_info.get('BillingModeSummary', {}).get('BillingMode', 'N/A')}")
        
        print(f"\n🔍 Índices creados:")
        print(f"   - Índice principal: namespace_name (HASH) + timestamp_start (RANGE)")
        
        if 'GlobalSecondaryIndexes' in table_info:
            for gsi in table_info['GlobalSecondaryIndexes']:
                key_schema = ' + '.join([f"{key['AttributeName']} ({key['KeyType']})" for key in gsi['KeySchema']])
                print(f"   - GSI: {gsi['IndexName']} -> {key_schema}")
        
        print(f"\n🔧 Variables de entorno para la aplicación:")
        print(f"   DYNAMODB_TABLE_NAME={table_name}")
        print(f"   AWS_REGION={boto3.Session().region_name}")
        
        return table_name
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"⚠️  La tabla {table_name} ya existe")
            return table_name
        else:
            print(f"❌ Error creando la tabla: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Crear tablas DynamoDB para namespace-scheduler')
    parser.add_argument('--environment', '-e', default='production', 
                       help='Entorno (default: production)')
    parser.add_argument('--table', '-t', choices=['logs', 'permissions', 'all'], default='all',
                       help='Tabla a crear: logs, permissions, o all (default: all)')
    
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
    
    created_tables = []
    
    if args.table in ['logs', 'all']:
        logs_table = create_task_scheduler_logs_table(args.environment)
        created_tables.append(logs_table)
    
    if args.table in ['permissions', 'all']:
        permissions_table = create_cost_center_permissions_table(args.environment)
        created_tables.append(permissions_table)
    
    print(f"\n✨ Proceso completado. Tablas creadas:")
    for table in created_tables:
        print(f"   - {table}")
    
    print(f"\n🔧 Variables de entorno para la aplicación:")
    if args.table in ['logs', 'all']:
        print(f"   DYNAMODB_TABLE_NAME={logs_table}")
    if args.table in ['permissions', 'all']:
        print(f"   PERMISSIONS_TABLE_NAME={permissions_table}")
    print(f"   AWS_REGION={boto3.Session().region_name}")

if __name__ == '__main__':
    main()