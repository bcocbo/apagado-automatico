#!/bin/bash

# Script de despliegue para la infraestructura AWS del Sistema MVP de Auto-Encendido de Namespaces
# Trabaja con la infraestructura existente del proyecto

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-prod}

echo "🚀 Desplegando infraestructura AWS para namespace-startup-scheduler..."
echo "   Región: ${AWS_REGION}"
echo "   Entorno: ${ENVIRONMENT}"
echo "   Directorio: ${SCRIPT_DIR}"

# Verificar que estamos conectados al cluster correcto
echo "🔍 Verificando conexión a Kubernetes..."
if ! kubectl get ns encendido-eks >/dev/null 2>&1; then
    echo "❌ Error: No se puede acceder al namespace 'encendido-eks'"
    echo "   Verificar conexión al cluster EKS"
    exit 1
fi

echo "✅ Conectado al cluster EKS"

# Verificar que AWS CLI esté configurado
echo "🔍 Verificando configuración de AWS CLI..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ Error: AWS CLI no está configurado correctamente"
    echo "   Ejecutar: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS CLI configurado - Cuenta: ${ACCOUNT_ID}"

# 1. Aplicar ConfigMap y Secret
echo "📝 Aplicando configuración de Kubernetes..."
kubectl apply -f "${SCRIPT_DIR}/configmap.yaml"

# Actualizar el ConfigMap con el nombre real del bucket
BUCKET_NAME="namespace-scheduler-config-${ENVIRONMENT}-${ACCOUNT_ID}"
kubectl patch configmap namespace-scheduler-config -n encendido-eks \
    --patch "{\"data\":{\"s3_bucket_name\":\"${BUCKET_NAME}\"}}"

echo "✅ ConfigMap y Secret aplicados"

# 2. Crear infraestructura AWS
echo "🏗️  Creando infraestructura AWS..."
kubectl apply -f "${SCRIPT_DIR}/dynamodb-table.yaml"

# Esperar a que el Job complete
echo "⏳ Esperando que el Job de infraestructura complete..."
kubectl wait --for=condition=complete job/aws-infrastructure-setup -n encendido-eks --timeout=300s

# Verificar si el Job fue exitoso
JOB_STATUS=$(kubectl get job aws-infrastructure-setup -n encendido-eks -o jsonpath='{.status.conditions[0].type}')
if [ "$JOB_STATUS" != "Complete" ]; then
    echo "❌ Error: El Job de infraestructura falló"
    echo "📋 Logs del Job:"
    kubectl logs job/aws-infrastructure-setup -n encendido-eks
    exit 1
fi

echo "✅ Infraestructura AWS creada exitosamente"

# 3. Actualizar deployment existente
echo "🔄 Actualizando deployment existente..."

# Verificar que el deployment existe
if ! kubectl get deployment namespace-scaler -n encendido-eks >/dev/null 2>&1; then
    echo "❌ Error: Deployment 'namespace-scaler' no encontrado"
    echo "   Verificar que ArgoCD haya desplegado el controller"
    exit 1
fi

# Aplicar el patch al deployment
kubectl patch deployment namespace-scaler -n encendido-eks --patch-file "${SCRIPT_DIR}/update-deployment.yaml"

echo "✅ Deployment actualizado"

# 4. Esperar que el deployment esté listo
echo "⏳ Esperando que el deployment esté listo..."
kubectl rollout status deployment/namespace-scaler -n encendido-eks --timeout=300s

# 5. Verificar que el pod esté funcionando
echo "🔍 Verificando estado del pod..."
POD_NAME=$(kubectl get pods -n encendido-eks -l app=namespace-scaler -o jsonpath='{.items[0].metadata.name}')

if [ -n "$POD_NAME" ]; then
    echo "📋 Pod activo: $POD_NAME"
    
    # Verificar health check
    echo "🏥 Verificando health check..."
    if kubectl exec -n encendido-eks "$POD_NAME" -- curl -f http://localhost:8081/health >/dev/null 2>&1; then
        echo "✅ Health check exitoso"
    else
        echo "⚠️  Health check falló - revisar logs"
        kubectl logs -n encendido-eks "$POD_NAME" --tail=20
    fi
else
    echo "⚠️  No se encontró pod activo"
fi

# 6. Limpiar Job temporal
echo "🧹 Limpiando recursos temporales..."
kubectl delete job aws-infrastructure-setup -n encendido-eks --ignore-not-found=true

# 7. Mostrar resumen final
echo ""
echo "🎉 Despliegue completado exitosamente!"
echo ""
echo "📋 Resumen de infraestructura:"
echo "   ✅ Tabla DynamoDB: NamespaceSchedules"
echo "   ✅ GSI: estado-fecha_encendido-index"
echo "   ✅ Bucket S3: ${BUCKET_NAME}"
echo "   ✅ ConfigMap: namespace-scheduler-config"
echo "   ✅ Deployment: namespace-scaler (actualizado)"
echo ""
echo "🔗 Endpoints disponibles:"
echo "   Health Check: kubectl port-forward -n encendido-eks svc/namespace-scaler-service 8081:8081"
echo "   Metrics: kubectl port-forward -n encendido-eks svc/namespace-scaler-service 8080:8080"
echo "   Frontend: kubectl port-forward -n encendido-eks svc/namespace-scaler-service 8081:8081 (http://localhost:8081/frontend)"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Verificar que el archivo config.json en S3 tenga los centros de costo correctos"
echo "   2. Configurar notificaciones (Slack/Email) si es necesario"
echo "   3. Probar la creación de programaciones desde el frontend"
echo "   4. Continuar con la implementación de la API según las tareas del spec"

# 8. Mostrar información de configuración
echo ""
echo "🔧 Información de configuración:"
echo "   AWS Region: ${AWS_REGION}"
echo "   S3 Bucket: ${BUCKET_NAME}"
echo "   DynamoDB Table: NamespaceSchedules"
echo "   Namespace: encendido-eks"

# 9. Verificar archivo de configuración en S3
echo ""
echo "📄 Verificando archivo de configuración en S3..."
if aws s3 ls "s3://${BUCKET_NAME}/config.json" >/dev/null 2>&1; then
    echo "✅ Archivo config.json encontrado en S3"
    echo "📋 Contenido actual:"
    aws s3 cp "s3://${BUCKET_NAME}/config.json" - | jq '.' 2>/dev/null || echo "   (archivo no es JSON válido o jq no disponible)"
else
    echo "⚠️  Archivo config.json no encontrado en S3"
fi

echo ""
echo "✨ ¡Infraestructura lista para continuar con las tareas del spec!"