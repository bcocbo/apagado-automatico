#!/bin/bash
# Script para verificar que los secrets de GitHub estén configurados

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verificando configuración de GitHub Secrets...${NC}"
echo ""

REPO="bcocbo/apagado-automatico"
SECRETS_URL="https://github.com/$REPO/settings/secrets/actions"

echo -e "${YELLOW}📋 Secrets requeridos para el workflow:${NC}"
echo ""
echo -e "${BLUE}1. AWS_REGION${NC}"
echo "   Valor: us-east-1"
echo "   Descripción: Región de AWS donde están los recursos"
echo ""
echo -e "${BLUE}2. AWS_ROLE_TO_ASSUME${NC}"
echo "   Valor: arn:aws:iam::2266