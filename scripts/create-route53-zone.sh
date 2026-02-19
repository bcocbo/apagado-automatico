#!/bin/bash

# Script para crear zona Route53 y configurar DNS para task-scheduler
set -e

DOMAIN_NAME="pocarqnube.com"
SUBDOMAIN="task-scheduler.pocarqnube.com"
AWS_REGION="us-east-1"

echo "🚀 Creando zona Route53 para $DOMAIN_NAME..."

# Crear la zona Route53 si no existe
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
    --dns-name "$DOMAIN_NAME" \
    --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" \
    --output text \
    --region $AWS_REGION | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
    echo "📝 Creando nueva zona Route53 para $DOMAIN_NAME..."
    
    # Crear zona Route53
    ZONE_RESULT=$(aws route53 create-hosted-zone \
        --name "$DOMAIN_NAME" \
        --caller-reference "task-scheduler-$(date +%s)" \
        --hosted-zone-config Comment="Zona para Task Scheduler EKS" \
        --region $AWS_REGION)
    
    HOSTED_ZONE_ID=$(echo $ZONE_RESULT | jq -r '.HostedZone.Id' | cut -d'/' -f3)
    
    echo "✅ Zona Route53 creada con ID: $HOSTED_ZONE_ID"
    
    # Mostrar los name servers
    echo "📋 Name Servers para configurar en tu registrador de dominio:"
    aws route53 get-hosted-zone --id $HOSTED_ZONE_ID \
        --query 'DelegationSet.NameServers' \
        --output table \
        --region $AWS_REGION
else
    echo "✅ Zona Route53 ya existe con ID: $HOSTED_ZONE_ID"
fi

# Obtener la dirección del Load Balancer
echo "🔍 Obteniendo dirección del Load Balancer..."
LB_DNS=$(kubectl get ingress -n task-scheduler task-scheduler-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

if [ -z "$LB_DNS" ]; then
    echo "❌ Error: No se pudo obtener la dirección del Load Balancer"
    echo "Verifica que el ingress esté configurado correctamente:"
    kubectl get ingress -n task-scheduler
    exit 1
fi

echo "📍 Load Balancer DNS: $LB_DNS"

# Crear registro CNAME para el subdominio
echo "📝 Creando registro DNS para $SUBDOMAIN..."

# Crear archivo JSON para el cambio de Route53
cat > /tmp/route53-change.json << EOF
{
    "Changes": [
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "$SUBDOMAIN",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [
                    {
                        "Value": "$LB_DNS"
                    }
                ]
            }
        }
    ]
}
EOF

# Aplicar el cambio
CHANGE_ID=$(aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch file:///tmp/route53-change.json \
    --query 'ChangeInfo.Id' \
    --output text \
    --region $AWS_REGION)

echo "✅ Registro DNS creado. Change ID: $CHANGE_ID"

# Esperar a que el cambio se propague
echo "⏳ Esperando propagación DNS..."
aws route53 wait resource-record-sets-changed --id $CHANGE_ID --region $AWS_REGION

echo "🎉 ¡DNS configurado exitosamente!"
echo ""
echo "📋 Resumen de configuración:"
echo "   Dominio: $SUBDOMAIN"
echo "   Load Balancer: $LB_DNS"
echo "   Zona Route53 ID: $HOSTED_ZONE_ID"
echo ""
echo "🌐 URLs de acceso:"
echo "   HTTP:  http://$SUBDOMAIN"
echo "   HTTPS: https://$SUBDOMAIN"
echo "   API:   https://$SUBDOMAIN/api/namespaces"
echo ""
echo "⚠️  Nota: La propagación DNS puede tardar hasta 48 horas en completarse globalmente"

# Limpiar archivo temporal
rm -f /tmp/route53-change.json

echo "✅ Script completado exitosamente"