# GitHub Actions Workflow Improvements

## Resumen de Cambios

El workflow de GitHub Actions (`build.yaml`) ha sido significativamente mejorado con las siguientes actualizaciones:

## 1. Mejoras de Nomenclatura y Consistencia

### Variables de Entorno
- **Antes**: `ECR_REPOSITORY_KUBECTL`
- **Después**: `ECR_REPOSITORY_BACKEND`
- **Beneficio**: Nomenclatura más clara y consistente

### Jobs Renombrados
- **Antes**: `build-kubectl-runner`
- **Después**: `build-backend`
- **Beneficio**: Refleja mejor la función del componente

## 2. Mejoras de Seguridad

### Parametrización de Secrets
- **Antes**: ARN del rol hardcodeado en el workflow
- **Después**: `${{ secrets.AWS_ROLE_TO_ASSUME }}` y `${{ secrets.AWS_REGION }}`
- **Beneficio**: Mayor flexibilidad y seguridad

### Uso de OIDC
- **Implementación**: `aws-actions/configure-aws-credentials@v4`
- **Beneficio**: No requiere credenciales de larga duración

## 3. Simplificación de Gestión de Manifiestos

### Estrategia Anterior
- Actualizaba repositorio externo `bcocbo/backstage-k8s-manifests-auth`
- Requería token personal `MANIFESTS_REPO_TOKEN`
- Complejidad adicional de gestión multi-repositorio

### Estrategia Actual
- Actualiza el mismo repositorio
- Usa `GITHUB_TOKEN` automático
- Modifica `manifests/overlays/production/kustomization.yaml` directamente
- Commit automático con `[skip ci]` para evitar loops

## 4. Mejoras Técnicas

### Actualización de Tags
```bash
# Método actual - más directo y confiable
sed -i "s|newTag: .*|newTag: $IMAGE_TAG|g" manifests/overlays/production/kustomization.yaml
```

### Permisos Optimizados
```yaml
permissions:
  id-token: write    # Para OIDC
  contents: write    # Para commits automáticos
```

## 5. Beneficios de los Cambios

### Simplicidad
- Un solo repositorio para código e infraestructura
- Menos tokens y secrets requeridos
- Proceso más directo

### Seguridad
- OIDC en lugar de credenciales estáticas
- Secrets parametrizados
- Permisos mínimos necesarios

### Mantenibilidad
- Nomenclatura consistente
- Código más limpio y legible
- Menos dependencias externas

### Trazabilidad
- Cada commit tiene su imagen correspondiente
- Historial completo en un solo repositorio
- GitOps nativo con ArgoCD

## 6. Configuración Requerida

Para que estos cambios funcionen correctamente, se requieren los siguientes secrets en GitHub:

| Secret | Valor | Descripción |
|--------|-------|-------------|
| `AWS_REGION` | `us-east-1` | Región de AWS |
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::226633502530:role/GitHubActions-TaskScheduler-Role` | ARN del rol IAM |

El `GITHUB_TOKEN` se proporciona automáticamente.

## 7. Próximos Pasos

1. **Verificar secrets**: Asegurar que los secrets requeridos están configurados
2. **Probar workflow**: Hacer un push para validar el funcionamiento
3. **Configurar ArgoCD**: Para detectar cambios en kustomization.yaml
4. **Eliminar dependencias obsoletas**: Remover tokens y configuraciones no utilizadas

## 8. Archivos Actualizados

- `.github/workflows/build.yaml` - Workflow principal
- `docs/github-actions-setup.md` - Documentación de configuración
- `docs/deployment-configuration.md` - Estrategia de despliegue
- `docs/github-secrets-configuration.md` - Configuración de secrets