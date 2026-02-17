#!/bin/bash
# Script para probar conectividad a DynamoDB desde kubectl-runner

set -e

NAMESPACE="task-scheduler"
DEPLOYMENT="task-scheduler"
AWS_REGION="us-east-1"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Probando conectividad a DynamoDB desde kubectl-runner...${NC}"

# Función para mostrar resultado
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# 1. Verificar que el deployment está corriendo
echo -e "${BLUE}🏗️  Verificando deployment...${NC}"
kubectl get deployment $DEPLOYMENT -n $NAMESPACE >/dev/null 2>&1
check_result $? "Deployment $DEPLOYMENT existe"

# Verificar que hay pods corriendo
READY_PODS=$(kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
if [ "$READY_PODS" -gt 0 ]; then
    echo -e "${GREEN}✅ Deployment tiene $READY_PODS pods listos${NC}"
else
    echo -e "${RED}❌ No hay pods listos en el deployment${NC}"
    echo -e "${YELLOW}📋 Estado del deployment:${NC}"
    kubectl describe deployment $DEPLOYMENT -n $NAMESPACE
    exit 1
fi

# 2. Obtener el nombre de un pod
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=task-scheduler -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$POD_NAME" ]; then
    echo -e "${RED}❌ No se encontró ningún pod del deployment${NC}"
    exit 1
fi

echo -e "${BLUE}🔧 Usando pod: $POD_NAME${NC}"

# 3. Verificar variables de entorno
echo -e "${BLUE}🔍 Verificando variables de entorno...${NC}"
kubectl exec $POD_NAME -n $NAMESPACE -- env | grep -E "(AWS_|DYNAMODB_|PERMISSIONS_)" || true

# 4. Verificar que boto3 puede acceder a AWS
echo -e "${BLUE}🔐 Verificando credenciales AWS...${NC}"
kubectl exec $POD_NAME -n $NAMESPACE -- python3 -c "
import boto3
import os
try:
    # Verificar que podemos crear un cliente DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    print('✅ Cliente DynamoDB creado exitosamente')
    
    # Verificar identidad
    sts = boto3.client('sts', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    identity = sts.get_caller_identity()
    print(f'✅ Identidad AWS: {identity.get(\"Arn\", \"Unknown\")}')
    
except Exception as e:
    print(f'❌ Error creando cliente DynamoDB: {e}')
    exit(1)
"
check_result $? "Credenciales AWS funcionando"

# 5. Probar acceso a las tablas DynamoDB
echo -e "${BLUE}🗄️  Probando acceso a tablas DynamoDB...${NC}"

# Probar tabla de logs
kubectl exec $POD_NAME -n $NAMESPACE -- python3 -c "
import boto3
import os
try:
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'task-scheduler-logs-production')
    table = dynamodb.Table(table_name)
    
    # Intentar describir la tabla
    table.load()
    print(f'✅ Tabla {table_name} accesible')
    print(f'   Estado: {table.table_status}')
    print(f'   Items: {table.item_count}')
    
except Exception as e:
    print(f'❌ Error accediendo a tabla {table_name}: {e}')
    exit(1)
"
check_result $? "Acceso a tabla task-scheduler-logs-production"

# Probar tabla de permisos
kubectl exec $POD_NAME -n $NAMESPACE -- python3 -c "
import boto3
import os
try:
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    table_name = os.getenv('PERMISSIONS_TABLE_NAME', 'cost-center-permissions-production')
    table = dynamodb.Table(table_name)
    
    # Intentar describir la tabla
    table.load()
    print(f'✅ Tabla {table_name} accesible')
    print(f'   Estado: {table.table_status}')
    print(f'   Items: {table.item_count}')
    
except Exception as e:
    print(f'❌ Error accediendo a tabla {table_name}: {e}')
    exit(1)
"
check_result $? "Acceso a tabla cost-center-permissions"

# 6. Probar operaciones básicas de DynamoDB
echo -e "${BLUE}🧪 Probando operaciones básicas...${NC}"

kubectl exec $POD_NAME -n $NAMESPACE -- python3 -c "
import boto3
import os
import time
import uuid

try:
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'task-scheduler-logs-production')
    table = dynamodb.Table(table_name)
    
    # Crear un item de prueba
    test_item = {
        'namespace_name': 'test-connectivity',
        'timestamp_start': int(time.time()),
        'operation_type': 'connectivity_test',
        'cost_center': 'test',
        'status': 'active',
        'id': str(uuid.uuid4())
    }
    
    # Insertar item
    table.put_item(Item=test_item)
    print('✅ Item de prueba insertado')
    
    # Leer item
    response = table.get_item(
        Key={
            'namespace_name': test_item['namespace_name'],
            'timestamp_start': test_item['timestamp_start']
        }
    )
    
    if 'Item' in response:
        print('✅ Item de prueba leído exitosamente')
        
        # Eliminar item de prueba
        table.delete_item(
            Key={
                'namespace_name': test_item['namespace_name'],
                'timestamp_start': test_item['timestamp_start']
            }
        )
        print('✅ Item de prueba eliminado')
    else:
        print('❌ No se pudo leer el item de prueba')
        exit(1)
    
except Exception as e:
    print(f'❌ Error en operaciones DynamoDB: {e}')
    exit(1)
"
check_result $? "Operaciones básicas de DynamoDB"

# 7. Verificar logs de la aplicación
echo -e "${BLUE}📋 Verificando logs de la aplicación...${NC}"
echo -e "${YELLOW}Últimas líneas de logs:${NC}"
kubectl logs $POD_NAME -n $NAMESPACE --tail=10

echo ""
echo -e "${GREEN}✅ Prueba de conectividad completada!${NC}"
echo ""
echo -e "${YELLOW}📋 Resumen:${NC}"
echo "   - Pod: $POD_NAME"
echo "   - Credenciales AWS: ✅ Funcionando"
echo "   - Tabla task-scheduler-logs-production: ✅ Accesible"
echo "   - Tabla cost-center-permissions: ✅ Accesible"
echo "   - Operaciones DynamoDB: ✅ Funcionando"
echo ""
echo -e "${BLUE}💡 Para monitorear en tiempo real:${NC}"
echo "   kubectl logs -f deployment/$DEPLOYMENT -n $NAMESPACE"