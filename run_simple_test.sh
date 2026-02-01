#!/bin/bash

echo "🚀 Iniciando test simple del Namespace Controller"
echo "=================================================="

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r controller/simple_requirements.txt

# Configurar variables de entorno
export DYNAMODB_TABLE_NAME="namespace-schedules-test"
export AWS_REGION="us-east-1"
export PORT="8080"

echo ""
echo "🌟 Configuración:"
echo "   - Tabla DynamoDB: $DYNAMODB_TABLE_NAME"
echo "   - Región AWS: $AWS_REGION"
echo "   - Puerto: $PORT"
echo ""

# Verificar credenciales de AWS
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ Credenciales de AWS configuradas correctamente"
    aws sts get-caller-identity --query 'Account' --output text | xargs echo "   Cuenta AWS:"
else
    echo "⚠️  Credenciales de AWS no configuradas o no válidas"
    echo "   El sistema funcionará en modo de prueba limitado"
fi

echo ""
echo "🚀 Iniciando controlador..."
echo "   Frontend disponible en: http://localhost:8080"
echo "   API disponible en: http://localhost:8080/api"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

# Ejecutar el controlador
cd controller
python3 simple_controller.py