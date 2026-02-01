#!/usr/bin/env python3
"""
Simple Namespace Controller for DynamoDB Testing
Controlador básico para probar lectura y escritura en DynamoDB
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de la aplicación Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Configuración de DynamoDB
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME', 'namespace-schedules')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

class SimpleDynamoDBClient:
    """Cliente simple para operaciones con DynamoDB"""
    
    def __init__(self):
        try:
            # Intentar crear cliente de DynamoDB
            self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
            self.table = self.dynamodb.Table(DYNAMODB_TABLE_NAME)
            self.connected = True
            logger.info(f"✅ Conectado a DynamoDB tabla: {DYNAMODB_TABLE_NAME}")
        except NoCredentialsError:
            logger.error("❌ No se encontraron credenciales de AWS")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Error conectando a DynamoDB: {e}")
            self.connected = False
    
    def test_connection(self) -> bool:
        """Probar la conexión con DynamoDB"""
        if not self.connected:
            return False
        
        try:
            # Intentar describir la tabla
            response = self.table.meta.client.describe_table(TableName=DYNAMODB_TABLE_NAME)
            logger.info(f"✅ Tabla {DYNAMODB_TABLE_NAME} existe y es accesible")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning(f"⚠️ Tabla {DYNAMODB_TABLE_NAME} no existe")
                return self.create_table()
            else:
                logger.error(f"❌ Error accediendo a la tabla: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
    
    def create_table(self) -> bool:
        """Crear la tabla de DynamoDB si no existe"""
        try:
            logger.info(f"🔨 Creando tabla {DYNAMODB_TABLE_NAME}...")
            
            table = self.dynamodb.create_table(
                TableName=DYNAMODB_TABLE_NAME,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'  # On-demand billing
            )
            
            # Esperar a que la tabla esté disponible
            table.wait_until_exists()
            logger.info(f"✅ Tabla {DYNAMODB_TABLE_NAME} creada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando tabla: {e}")
            return False
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crear un nuevo schedule en DynamoDB"""
        if not self.connected:
            raise Exception("No hay conexión con DynamoDB")
        
        try:
            # Generar ID único
            schedule_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Preparar item para DynamoDB
            item = {
                'id': schedule_id,
                'namespace': schedule_data['namespace'],
                'startup_time': schedule_data['startup_time'],
                'shutdown_time': schedule_data['shutdown_time'],
                'timezone': schedule_data['timezone'],
                'days_of_week': schedule_data.get('days_of_week', []),
                'enabled': schedule_data.get('enabled', True),
                'metadata': schedule_data.get('metadata', {}),
                'created_at': timestamp,
                'updated_at': timestamp
            }
            
            # Insertar en DynamoDB
            self.table.put_item(Item=item)
            logger.info(f"✅ Schedule creado: {schedule_id} para namespace {schedule_data['namespace']}")
            
            return item
            
        except Exception as e:
            logger.error(f"❌ Error creando schedule: {e}")
            raise
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Obtener todos los schedules de DynamoDB"""
        if not self.connected:
            raise Exception("No hay conexión con DynamoDB")
        
        try:
            response = self.table.scan()
            schedules = response.get('Items', [])
            
            logger.info(f"✅ Obtenidos {len(schedules)} schedules de DynamoDB")
            return schedules
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo schedules: {e}")
            raise
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un schedule específico por ID"""
        if not self.connected:
            raise Exception("No hay conexión con DynamoDB")
        
        try:
            response = self.table.get_item(Key={'id': schedule_id})
            item = response.get('Item')
            
            if item:
                logger.info(f"✅ Schedule encontrado: {schedule_id}")
            else:
                logger.warning(f"⚠️ Schedule no encontrado: {schedule_id}")
            
            return item
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo schedule {schedule_id}: {e}")
            raise
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Eliminar un schedule de DynamoDB"""
        if not self.connected:
            raise Exception("No hay conexión con DynamoDB")
        
        try:
            self.table.delete_item(Key={'id': schedule_id})
            logger.info(f"✅ Schedule eliminado: {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error eliminando schedule {schedule_id}: {e}")
            raise

# Inicializar cliente de DynamoDB
db_client = SimpleDynamoDBClient()

# Rutas de la API

@app.route('/')
def index():
    """Servir la página principal"""
    return send_from_directory('public', 'simple.html')

@app.route('/api/health')
def health_check():
    """Endpoint de health check"""
    try:
        db_connected = db_client.test_connection()
        
        health_data = {
            'status': 'healthy' if db_connected else 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'dynamodb': db_connected,
                'controller': True,
                'circuit_breaker': True
            },
            'table_name': DYNAMODB_TABLE_NAME,
            'aws_region': AWS_REGION
        }
        
        status_code = 200 if db_connected else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Obtener todos los schedules"""
    try:
        schedules = db_client.get_all_schedules()
        return jsonify(schedules), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo schedules: {e}")
        return jsonify({
            'error': 'Error obteniendo schedules',
            'message': str(e)
        }), 500

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Crear un nuevo schedule"""
    try:
        data = request.get_json()
        
        # Validación básica
        required_fields = ['namespace', 'startup_time', 'shutdown_time', 'timezone']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        # Crear schedule
        schedule = db_client.create_schedule(data)
        return jsonify(schedule), 201
        
    except Exception as e:
        logger.error(f"❌ Error creando schedule: {e}")
        return jsonify({
            'error': 'Error creando schedule',
            'message': str(e)
        }), 500

@app.route('/api/schedules/<schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Obtener un schedule específico"""
    try:
        schedule = db_client.get_schedule(schedule_id)
        
        if schedule:
            return jsonify(schedule), 200
        else:
            return jsonify({
                'error': 'Schedule no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo schedule {schedule_id}: {e}")
        return jsonify({
            'error': 'Error obteniendo schedule',
            'message': str(e)
        }), 500

@app.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Eliminar un schedule"""
    try:
        # Verificar que existe
        schedule = db_client.get_schedule(schedule_id)
        if not schedule:
            return jsonify({
                'error': 'Schedule no encontrado'
            }), 404
        
        # Eliminar
        db_client.delete_schedule(schedule_id)
        return jsonify({
            'message': 'Schedule eliminado exitosamente'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error eliminando schedule {schedule_id}: {e}")
        return jsonify({
            'error': 'Error eliminando schedule',
            'message': str(e)
        }), 500

@app.route('/api/test-write')
def test_write():
    """Endpoint para probar escritura en DynamoDB"""
    try:
        test_data = {
            'namespace': f'test-namespace-{int(datetime.now().timestamp())}',
            'startup_time': '08:00',
            'shutdown_time': '18:00',
            'timezone': 'America/Bogota',
            'days_of_week': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            'enabled': True,
            'metadata': {
                'business_unit': 'Testing',
                'cost_savings_target': 500,
                'description': 'Schedule de prueba para testing'
            }
        }
        
        schedule = db_client.create_schedule(test_data)
        return jsonify({
            'message': 'Test de escritura exitoso',
            'schedule': schedule
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error en test de escritura: {e}")
        return jsonify({
            'error': 'Error en test de escritura',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Iniciando Simple Namespace Controller...")
    logger.info(f"📊 Tabla DynamoDB: {DYNAMODB_TABLE_NAME}")
    logger.info(f"🌍 Región AWS: {AWS_REGION}")
    
    # Probar conexión inicial
    if db_client.test_connection():
        logger.info("✅ Conexión con DynamoDB establecida")
    else:
        logger.warning("⚠️ No se pudo conectar con DynamoDB - algunas funciones pueden no estar disponibles")
    
    # Ejecutar aplicación
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)