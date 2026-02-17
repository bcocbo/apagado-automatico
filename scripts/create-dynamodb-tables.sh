#!/bin/bash

# Script para crear las tablas de DynamoDB para Namespace Scheduler
# Uso: ./create-dynamodb-tables.sh [environment]

set -e

ENVIRONMENT=${1:-production}
AWS_REGION="us-east-1"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Creando tablas de DynamoDB para el entorno: ${ENVIRONMENT}${NC}"

# Verificar que AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: AWS CLI no está configurado correctamente${NC}"
    echo "   Ejecuta: aws configure"
    exit 1
fi

# Función para mostrar resultado
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
    else
        echo -e "${RED}❌ $1${NC}"
        return 1
    fi
}

# 1. Crear tabla task-scheduler-logs
LOGS_TABLE_NAME="task-scheduler-logs-${ENVIRONMENT}"
echo -e "${BLUE}📋 Creando tabla: ${LOGS_TABLE_NAME}${NC}"

if aws dynamodb describe-table --table-name $LOGS_TABLE_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Tabla ${LOGS_TABLE_NAME} ya existe${NC}"
else
    # Crear tabla básica primero
    aws dynamodb create-table \
        --table-name $LOGS_TABLE_NAME \
        --attribute-definitions \
            AttributeName=namespace_name,AttributeType=S \
            AttributeName=timestamp_start,AttributeType=N \
        --key-schema \
            AttributeName=namespace_name,KeyType=HASH \
            AttributeName=timestamp_start,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
    
    check_result "Tabla ${LOGS_TABLE_NAME} creada"
    
    # Esperar a que la tabla esté activa
    echo -e "${BLUE}⏳ Esperando a que la tabla esté activa...${NC}"
    aws dynamodb wait table-exists --table-name $LOGS_TABLE_NAME --region $AWS_REGION
    check_result "Tabla ${LOGS_TABLE_NAME} activa"
    
    # Agregar GSI para cost-center
    echo -e "${BLUE}📋 Agregando índice cost-center-timestamp-index...${NC}"
    aws dynamodb update-table \
        --table-name $LOGS_TABLE_NAME \
        --attribute-definitions \
            AttributeName=cost_center,AttributeType=S \
            AttributeName=timestamp_start,AttributeType=N \
        --global-secondary-index-updates \
            'Create={IndexName=cost-center-timestamp-index,KeySchema=[{AttributeName=cost_center,KeyType=HASH},{AttributeName=timestamp_start,KeyType=RANGE}],Projection={ProjectionType=ALL}}' \
        --region $AWS_REGION
    
    check_result "Índice cost-center-timestamp-index agregado"
fi

# 2. Crear tabla cost-center-permissions
PERMISSIONS_TABLE_NAME="cost-center-permissions-${ENVIRONMENT}"
echo -e "${BLUE}📋 Creando tabla: ${PERMISSIONS_TABLE_NAME}${NC}"

if aws dynamodb describe-table --table-name $PERMISSIONS_TABLE_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Tabla ${PERMISSIONS_TABLE_NAME} ya existe${NC}"
else
    aws dynamodb create-table \
        --table-name $PERMISSIONS_TABLE_NAME \
        --attribute-definitions \
            AttributeName=cost_center,AttributeType=S \
        --key-schema \
            AttributeName=cost_center,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
    
    check_result "Tabla ${PERMISSIONS_TABLE_NAME} creada"
    
    # Esperar a que la tabla esté activa
    echo -e "${BLUE}⏳ Esperando a que la tabla esté activa...${NC}"
    aws dynamodb wait table-exists --table-name $PERMISSIONS_TABLE_NAME --region $AWS_REGION
    check_result "Tabla ${PERMISSIONS_TABLE_NAME} activa"
fi

echo ""
echo -e "${GREEN}✅ Tablas creadas exitosamente!${NC}"
echo ""
echo -e "${YELLOW}📋 Tablas creadas:${NC}"
echo "   - ${LOGS_TABLE_NAME}"
echo "   - ${PERMISSIONS_TABLE_NAME}"

# Mostrar detalles de las tablas
echo ""
echo -e "${BLUE}🔍 Detalles de la tabla de logs:${NC}"
aws dynamodb describe-table --table-name $LOGS_TABLE_NAME --region $AWS_REGION --query 'Table.{
    TableName: TableName,
    TableStatus: TableStatus,
    ItemCount: ItemCount,
    BillingMode: BillingModeSummary.BillingMode,
    GlobalSecondaryIndexes: GlobalSecondaryIndexes[].{IndexName: IndexName, IndexStatus: IndexStatus}
}' --output table

echo ""
echo -e "${BLUE}🔍 Detalles de la tabla de permisos:${NC}"
aws dynamodb describe-table --table-name $PERMISSIONS_TABLE_NAME --region $AWS_REGION --query 'Table.{
    TableName: TableName,
    TableStatus: TableStatus,
    ItemCount: ItemCount,
    BillingMode: BillingModeSummary.BillingMode
}' --output table

echo ""
echo -e "${YELLOW}🔧 Variables de entorno para la aplicación:${NC}"
echo "   DYNAMODB_TABLE_NAME=${LOGS_TABLE_NAME}"
echo "   PERMISSIONS_TABLE_NAME=${PERMISSIONS_TABLE_NAME}"
echo "   AWS_REGION=${AWS_REGION}"
echo ""
echo -e "${BLUE}💡 Para verificar las tablas:${NC}"
echo "   aws dynamodb list-tables --region ${AWS_REGION}"