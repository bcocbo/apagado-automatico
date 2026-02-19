#!/bin/bash

# Script para sincronizar namespaces protegidos entre el archivo local y el ConfigMap
# Uso: ./sync-protected-namespaces.sh [--from-file|--from-configmap|--help]

set -e

NAMESPACE="task-scheduler"
CONFIGMAP_NAME="protected-namespaces-config"
LOCAL_FILE="kubectl-runner/src/config/protected-namespaces.json"

show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Sincroniza la lista de namespaces protegidos entre el archivo local y el ConfigMap de Kubernetes"
    echo ""
    echo "OPCIONES:"
    echo "  --from-file       Actualiza el ConfigMap usando el archivo local (por defecto)"
    echo "  --from-configmap  Actualiza el archivo local usando el ConfigMap"
    echo "  --help           Muestra esta ayuda"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0                      # Sincroniza desde archivo local al ConfigMap"
    echo "  $0 --from-file          # Sincroniza desde archivo local al ConfigMap"
    echo "  $0 --from-configmap     # Sincroniza desde ConfigMap al archivo local"
}

sync_from_file_to_configmap() {
    echo "🔄 Sincronizando namespaces protegidos desde archivo local al ConfigMap..."
    
    if [[ ! -f "$LOCAL_FILE" ]]; then
        echo "❌ Error: Archivo local no encontrado: $LOCAL_FILE"
        exit 1
    fi
    
    # Validar que el archivo JSON sea válido
    if ! jq empty "$LOCAL_FILE" 2>/dev/null; then
        echo "❌ Error: El archivo $LOCAL_FILE no contiene JSON válido"
        exit 1
    fi
    
    # Extraer la lista de namespaces del JSON
    NAMESPACES_LIST=$(jq -r '.protected_namespaces[]' "$LOCAL_FILE")
    
    # Crear el contenido del ConfigMap
    echo "📝 Creando ConfigMap con los siguientes namespaces protegidos:"
    echo "$NAMESPACES_LIST" | sed 's/^/  - /'
    
    # Actualizar el ConfigMap
    kubectl create configmap "$CONFIGMAP_NAME" \
        --from-file=protected-namespaces.json="$LOCAL_FILE" \
        --from-literal=protected-namespaces-list.txt="$NAMESPACES_LIST" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo "✅ ConfigMap actualizado exitosamente"
}

sync_from_configmap_to_file() {
    echo "🔄 Sincronizando namespaces protegidos desde ConfigMap al archivo local..."
    
    # Verificar que el ConfigMap existe
    if ! kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "❌ Error: ConfigMap $CONFIGMAP_NAME no encontrado en namespace $NAMESPACE"
        exit 1
    fi
    
    # Extraer el JSON del ConfigMap
    kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.data.protected-namespaces\.json}' > "$LOCAL_FILE"
    
    # Validar que el archivo resultante sea JSON válido
    if ! jq empty "$LOCAL_FILE" 2>/dev/null; then
        echo "❌ Error: Los datos del ConfigMap no contienen JSON válido"
        exit 1
    fi
    
    echo "📝 Archivo local actualizado con los siguientes namespaces protegidos:"
    jq -r '.protected_namespaces[]' "$LOCAL_FILE" | sed 's/^/  - /'
    
    echo "✅ Archivo local actualizado exitosamente: $LOCAL_FILE"
}

# Procesar argumentos
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --from-configmap)
        sync_from_configmap_to_file
        ;;
    --from-file|"")
        sync_from_file_to_configmap
        ;;
    *)
        echo "❌ Error: Opción desconocida: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

echo ""
echo "🎉 Sincronización completada!"
echo ""
echo "💡 Consejos:"
echo "  - Para agregar un namespace protegido: edita $LOCAL_FILE y ejecuta este script"
echo "  - Para quitar un namespace protegido: edita $LOCAL_FILE y ejecuta este script"
echo "  - Los cambios se aplicarán automáticamente a las políticas de Kyverno"
echo "  - Reinicia el pod del task-scheduler para que cargue la nueva configuración"