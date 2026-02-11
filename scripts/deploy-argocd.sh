#!/bin/bash
# Script para desplegar la aplicación con ArgoCD

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Desplegando Task Scheduler con ArgoCD...${NC}"
echo ""

# Verificar que ArgoCD esté instalado
if ! kubectl get namespace argocd &> /dev/null; then
    echo -e "${YELLOW}⚠️  ArgoCD no está instalado. Instalando...${NC}"
    kubectl create namespace argocd
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    echo -e "${GREEN}✓ ArgoCD instalado${NC}"
    echo ""
    echo -e "${YELLOW}Esperando a que ArgoCD esté listo...${NC}"
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
fi

echo -e "${BLUE}📝 Aplicando configuración de ArgoCD...${NC}"
kubectl apply -f argocd/backstage-app.yaml

echo ""
echo -e "${GREEN}✅ Aplicación Task Scheduler creada en ArgoCD${NC}"
echo ""
echo -e "${YELLOW}📊 Verificando estado de la aplicación...${NC}"
sleep 5
kubectl get application task-scheduler -n argocd

echo ""
echo -e "${YELLOW}🔍 Para ver el estado detallado:${NC}"
echo "   kubectl get application task-scheduler -n argocd -o yaml"
echo ""
echo -e "${YELLOW}🌐 Para acceder a ArgoCD UI:${NC}"
echo "   kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "   Usuario: admin"
echo "   Password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
echo ""
echo -e "${YELLOW}📦 Para ver los pods desplegados:${NC}"
echo "   kubectl get pods -n task-scheduler"
