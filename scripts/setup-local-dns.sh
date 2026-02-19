#!/bin/bash

# Script para configurar DNS local temporal
set -e

LB_DNS="k8s-tasksche-tasksche-eda317fc9f-1665879767.us-east-1.elb.amazonaws.com"
DOMAIN="task-scheduler.pocarqnube.com"

echo "🔍 Resolviendo IP del Load Balancer..."
LB_IP=$(nslookup $LB_DNS | grep -A1 "Name:" | tail -1 | awk '{print $2}')

if [ -z "$LB_IP" ]; then
    echo "❌ No se pudo resolver la IP del Load Balancer"
    exit 1
fi

echo "📍 IP del Load Balancer: $LB_IP"

# Crear entrada para /etc/hosts
HOSTS_ENTRY="$LB_IP $DOMAIN"

echo "📝 Agregando entrada al archivo hosts:"
echo "   $HOSTS_ENTRY"

# Verificar si ya existe la entrada
if grep -q "$DOMAIN" /etc/hosts; then
    echo "⚠️  La entrada ya existe en /etc/hosts"
    echo "Para actualizarla, ejecuta:"
    echo "sudo sed -i '/$DOMAIN/d' /etc/hosts"
    echo "echo '$HOSTS_ENTRY' | sudo tee -a /etc/hosts"
else
    echo "Para agregar la entrada, ejecuta:"
    echo "echo '$HOSTS_ENTRY' | sudo tee -a /etc/hosts"
fi

echo ""
echo "🌐 Después de agregar la entrada, podrás acceder a:"
echo "   http://$DOMAIN"
echo "   http://$DOMAIN/api/namespaces"
echo ""
echo "⚠️  Recuerda remover la entrada cuando configures Route53:"
echo "sudo sed -i '/$DOMAIN/d' /etc/hosts"