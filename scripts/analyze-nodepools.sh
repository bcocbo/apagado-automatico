#!/bin/bash
# Script para analizar el uso de NodePools de Karpenter

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Análisis de NodePools de Karpenter ===${NC}"
echo ""

# Reconectar al cluster
echo -e "${YELLOW}Conectando al cluster...${NC}"
aws eks update-kubeconfig --region us-east-1 --name eks-cloud > /dev/null 2>&1

echo -e "${GREEN}✓ Conectado${NC}"
echo ""

# 1. Resumen de NodePools
echo -e "${BLUE}1. Estado de NodePools:${NC}"
kubectl get nodepools
echo ""

# 2. Nodos por NodePool
echo -e "${BLUE}2. Conteo de nodos por NodePool:${NC}"
kubectl get nodes -o json | jq -r '.items[] | .metadata.labels."karpenter.sh/nodepool" // "sin-nodepool"' | sort | uniq -c
echo ""

# 3. Uso de recursos en nodos SPOT
echo -e "${BLUE}3. Uso de CPU/Memoria en nodos SPOT:${NC}"
kubectl top nodes --selector=karpenter.sh/nodepool=spot 2>/dev/null || echo "Metrics server no disponible"
echo ""

# 4. Pods por nodo SPOT
echo -e "${BLUE}4. Cantidad de pods por nodo SPOT:${NC}"
for node in $(kubectl get nodes -l karpenter.sh/nodepool=spot -o jsonpath='{.items[*].metadata.name}'); do
    pod_count=$(kubectl get pods --all-namespaces --field-selector spec.nodeName=$node --no-headers 2>/dev/null | wc -l)
    instance=$(kubectl get node $node -o jsonpath='{.metadata.labels.node\.kubernetes\.io/instance-type}')
    echo "  $node ($instance): $pod_count pods"
done
echo ""

# 5. Namespaces usando nodos SPOT
echo -e "${BLUE}5. Top Namespaces en nodos SPOT:${NC}"
temp_file=$(mktemp)
for node in $(kubectl get nodes -l karpenter.sh/nodepool=spot -o jsonpath='{.items[*].metadata.name}'); do
    kubectl get pods --all-namespaces --field-selector spec.nodeName=$node -o custom-columns=NS:.metadata.namespace --no-headers 2>/dev/null >> $temp_file
done
cat $temp_file | sort | uniq -c | sort -rn | head -10
rm -f $temp_file
echo ""

# 6. Resumen general
echo -e "${BLUE}6. Resumen general de todos los nodos:${NC}"
kubectl get pods --all-namespaces -o wide 2>/dev/null | grep -E "ip-192-168" | awk '{print $1}' | sort | uniq -c | sort -rn | head -15
echo ""

echo -e "${GREEN}✓ Análisis completado${NC}"
