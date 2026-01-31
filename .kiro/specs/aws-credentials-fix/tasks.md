# Plan de Implementación: Configuración de Credenciales AWS para Controlador de Kubernetes

## Resumen

Este plan implementa IAM Roles for Service Accounts (IRSA) para resolver el problema de credenciales de AWS en el controlador de namespaces. Las tareas están organizadas para construir incrementalmente la solución completa.

## Tareas

- [ ] 1. Configurar infraestructura AWS con Terraform
  - [ ] 1.1 Crear configuración Terraform para IAM Role y Policy
    - Crear archivo `terraform/irsa.tf` con definición del rol IAM
    - Definir policy de DynamoDB con permisos mínimos necesarios
    - Configurar trust relationship para OIDC provider del cluster EKS
    - Incluir variables para reutilización entre ambientes
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.3, 2.5, 7.1, 7.2, 7.5_

  - [ ] 1.2 Escribir test de propiedad para permisos DynamoDB
    - **Property 1: Permisos DynamoDB completos**
    - **Validates: Requirements 1.2, 5.1, 5.2, 5.3, 5.4**

  - [ ] 1.3 Crear script de aplicación de infraestructura
    - Crear script `scripts/apply-infrastructure.sh` para aplicar Terraform
    - Incluir validaciones pre-aplicación y post-aplicación
    - Agregar logging y manejo de errores
    - _Requirements: 7.4_

  - [ ]* 1.4 Escribir test de propiedad para configuración completa
    - **Property 10: Configuración completa mediante infraestructura como código**
    - **Validates: Requirements 7.4**

- [ ] 2. Configurar ServiceAccount y manifiestos de Kubernetes
  - [ ] 2.1 Actualizar ServiceAccount con anotación IRSA
    - Modificar archivo `k8s/serviceaccount.yaml` con anotación `eks.amazonaws.com/role-arn`
    - Asegurar que mantiene anotaciones y labels existentes
    - Validar que está en el namespace correcto `encendido-eks`
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 7.3_

  - [ ]* 2.2 Escribir test de propiedad para preservación de metadatos
    - **Property 4: Preservación de metadatos existentes**
    - **Validates: Requirements 3.5**

  - [ ] 2.3 Actualizar Deployment del controlador
    - Modificar `k8s/deployment.yaml` para usar el ServiceAccount correcto
    - Agregar variables de ambiente necesarias para IRSA
    - Configurar health checks y probes apropiados
    - _Requirements: 3.3, 4.1_

  - [ ]* 2.4 Escribir test de propiedad para descubrimiento automático
    - **Property 3: Descubrimiento automático de credenciales**
    - **Validates: Requirements 3.3, 4.1, 4.2**

- [ ] 3. Checkpoint - Validar configuración de infraestructura
  - Asegurar que todos los tests pasan, preguntar al usuario si surgen dudas.

- [ ] 4. Mejorar el código del controlador para IRSA
  - [ ] 4.1 Agregar logging mejorado para credenciales
    - Modificar `controller/scaler.py` para incluir logging detallado de IRSA
    - Implementar clases de error específicas para problemas de credenciales
    - Agregar validación de anotaciones del ServiceAccount al inicio
    - Asegurar que no se loguee información sensible
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 4.2 Escribir test de propiedad para logging de errores
    - **Property 7: Logging comprehensivo de errores**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [ ]* 4.3 Escribir test de propiedad para logging de éxito
    - **Property 8: Logging de éxito para debugging**
    - **Validates: Requirements 6.4**

  - [ ]* 4.4 Escribir test de propiedad para protección de información sensible
    - **Property 9: Protección de información sensible**
    - **Validates: Requirements 6.5**

  - [ ] 4.5 Implementar validación de credenciales en health check
    - Modificar función `health_check()` para verificar acceso a DynamoDB
    - Agregar retry logic específico para errores de credenciales
    - Implementar circuit breaker para fallos de autenticación
    - _Requirements: 1.3, 5.5, 6.1_

  - [ ]* 4.6 Escribir test de propiedad para validación OIDC
    - **Property 2: Validación automática de tokens OIDC**
    - **Validates: Requirements 2.4**

- [ ] 5. Implementar scripts de automatización y diagnóstico
  - [ ] 5.1 Crear script de diagnóstico IRSA
    - Crear `scripts/diagnose-irsa.sh` para troubleshooting
    - Verificar configuración del cluster OIDC
    - Validar anotaciones del ServiceAccount
    - Probar asunción del rol IAM
    - Verificar permisos DynamoDB
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 5.2 Crear script de despliegue completo
    - Crear `scripts/deploy-complete.sh` que ejecute todo el proceso
    - Incluir aplicación de Terraform
    - Aplicar manifiestos de Kubernetes
    - Validar funcionamiento end-to-end
    - _Requirements: 7.4_

  - [ ]* 5.3 Escribir test de propiedad para uso exclusivo de credenciales IRSA
    - **Property 6: Uso exclusivo de credenciales IRSA**
    - **Validates: Requirements 4.4**

- [ ] 6. Implementar tests de integración y validación
  - [ ] 6.1 Crear tests de integración para operaciones DynamoDB
    - Crear `tests/integration/test_dynamodb_operations.py`
    - Probar todas las operaciones CRUD con credenciales IRSA
    - Validar que no hay errores de autenticación
    - Incluir tests para DescribeTable
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 6.2 Escribir test de propiedad para renovación de credenciales
    - **Property 5: Renovación automática de credenciales**
    - **Validates: Requirements 4.3**

  - [ ] 6.3 Crear tests de validación de configuración
    - Crear `tests/validation/test_irsa_config.py`
    - Validar que el rol IAM existe con configuración correcta
    - Verificar trust relationship y permisos
    - Comprobar anotaciones del ServiceAccount
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.5, 3.1, 3.2, 3.4_

  - [ ]* 6.4 Escribir tests unitarios para casos edge
    - Probar comportamiento con anotaciones faltantes
    - Validar manejo de errores de permisos
    - Probar escenarios de fallo de red
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 7. Crear documentación y guías de troubleshooting
  - [ ] 7.1 Crear guía de troubleshooting
    - Crear `docs/troubleshooting-irsa.md`
    - Documentar errores comunes y soluciones
    - Incluir comandos de diagnóstico
    - Agregar ejemplos de logs de error y éxito
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 7.2 Crear documentación de despliegue
    - Crear `docs/deployment-guide.md`
    - Documentar proceso completo paso a paso
    - Incluir prerequisitos y validaciones
    - Agregar ejemplos de configuración para diferentes ambientes
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 8. Checkpoint final - Validación end-to-end
  - Asegurar que todos los tests pasan, preguntar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requirements específicos para trazabilidad
- Los checkpoints aseguran validación incremental
- Los property tests validan propiedades universales de corrección
- Los unit tests validan ejemplos específicos y casos edge
- La implementación sigue el principio de menor privilegio para seguridad
- Todos los componentes están definidos como infraestructura como código para reproducibilidad