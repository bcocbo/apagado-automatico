#!/bin/bash
# Script para eliminar nodos NotReady del cluster

set -e

echo "🔍 Buscando nodos NotReady..."
NOTREADY_NODES=$(kubectl get nodes --no-headers | grep NotReady | awk '{print $1}')
COUNT=$(echo "$NOTREADY_NODES" | wc -l)

if [ -z "$NOTREADY_NODES" ]; then
    echo "✅ No hay nodos NotReady para eliminar"
    exit 0
fi

echo "📊 Encontrados $COUNT nodos NotReady"
echo ""
echo "🗑️  Eliminando nodos NotReady..."

# Eliminar nodos en lotes de 5 para no sobrecargar
echo "$NOTREADY_NODES" | xargs -n 5 -P 5 -I {} kubectl delete node {} --grace-period=0 --force 2>/dev/null || true

echo ""
echo "✅ Limpieza completada"
echo ""
echo "📊 Estado actual del cluster:"
kubectl get nodes
