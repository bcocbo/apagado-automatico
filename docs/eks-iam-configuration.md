# Configuración de IAM para EKS - Namespace Scheduler

## Descripción

Este documento describe la configuración de roles IAM necesarios para que el servicio `kubectl-runner` en EKS pueda acceder a las tablas DynamoDB del proyecto Namespace Scheduler.

## Arquitectura de Seguridad

### Componentes

1. **EKS Cluster**: `production-cluster`
2. **Service Account**: `kubectl-runner` en namespace `task-scheduler`
3. **IAM Role**: `kubectl-runner-role`
4. **IAM Policy**: `kubectl-runner-dynamodb-policy`
5. **OIDC Provider**: Para autenticación entre EKS y IAM

### Flujo de Autenticación

El sistema soporta dos métodos de autenticación dependiendo del entorno de ejecución:

#### Método 1: Service Account Token (En Pod de Kubernetes)
```
Pod (kubectl-runner) 
  ↓ (detecta /var/run/secrets/kubernetes.io/serviceaccount/token)
Service Account Token (autenticación automática)
  ↓ (usa Service Account)
Service Account (con anotación eks.amazonaws.com/role-arn)
  ↓ (asume rol via OIDC)
IAM Role (kubectl-runner-role)
  ↓ (tiene permisos via Policy)
DynamoDB Tables (task-scheduler-logs, cost-center-permissions)
```

#### Método 2: AWS EKS kubeconfig (Desarrollo Local)
```
Aplicación Local
  ↓ (no encuentra service account token)
AWS EKS update-kubeconfig
  ↓ (configura ~/.kube/config)
kubectl con AWS credentials
  ↓ (acceso directo al cluster)
EKS Cluster + DynamoDB (via AWS credentials locales)
```

## Detección Automática de Entorno

El sistema detecta automáticamente el entorno de ejecución y selecciona el método de autenticación apropiado:

### Detección de Pod de Kubernetes
```python
# Verifica si existe el token del service account
in_k8s_pod = os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token')
```

### Comportamiento por Entorno

| Entorno | Detección | Método de Auth | Configuración |
|---------|-----------|----------------|---------------|
| **Pod en EKS** | Token existe | Service Account | Automático via IRSA |
| **Desarrollo Local** | Token no existe | AWS kubeconfig | Requiere AWS credentials |
| **CI/CD** | Token no existe | AWS kubeconfig | Requiere AWS credentials |

### Ventajas de la Detección Automática

1. **Sin Configuración Manual**: No requiere variables de entorno para seleccionar el método
2. **Compatibilidad**: Funciona tanto en producción (EKS) como en desarrollo local
3. **Seguridad**: Usa el método más seguro disponible en cada entorno
4. **Simplicidad**: Un solo código base para todos los entornos

## Configuración Paso a Paso

### 1. Ejecutar Script de Configuración

```bash
# Configurar IAM roles para EKS
./scripts/setup-eks-iam-roles.sh
```

Este script:
- Obtiene el OIDC issuer URL del cluster EKS
- Crea/verifica el OIDC provider para EKS
- Crea la política IAM con permisos DynamoDB
- Crea el rol IAM con trust policy para el service account
- Adjunta la política al rol

### 2. Validar Configuración

```bash
# Validar que todo esté configurado correctamente
./scripts/validate-eks-iam-setup.sh
```

### 3. Probar Conectividad

```bash
# Probar conectividad desde el pod
./scripts/test-dynamodb-connectivity.sh
```

## Recursos Creados

### IAM Role: `kubectl-runner-role`

**ARN**: `arn:aws:iam::226633502530:role/kubectl-runner-role`

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::226633502530:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/[OIDC_ID]"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/[OIDC_ID]:sub": "system:serviceaccount:task-scheduler:kubectl-runner",
          "oidc.eks.us-east-1.amazonaws.com/id/[OIDC_ID]:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

### IAM Policy: `kubectl-runner-dynamodb-policy`

**Permisos**:
- **DynamoDB**: Acceso completo a tablas `task-scheduler-logs*` y `cost-center-permissions*`
- **DynamoDB**: Permisos de listado y descripción de tablas
- **EKS**: Permiso para describir el cluster

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:226633502530:table/task-scheduler-logs*",
        "arn:aws:dynamodb:us-east-1:226633502530:table/cost-center-permissions*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:ListTables",
        "dynamodb:DescribeTable"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster"
      ],
      "Resource": "arn:aws:eks:us-east-1:226633502530:cluster/production-cluster"
    }
  ]
}
```

### Service Account

El service account `kubectl-runner` debe tener la anotación:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubectl-runner
  namespace: task-scheduler
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::226633502530:role/kubectl-runner-role
```

**Nota**: Para información detallada sobre la configuración RBAC de Kubernetes (ClusterRole, ClusterRoleBinding), consultar [kubernetes-rbac-configuration.md](kubernetes-rbac-configuration.md).

## Variables de Entorno

El deployment debe tener estas variables de entorno configuradas:

```yaml
env:
- name: EKS_CLUSTER_NAME
  value: "eks-cloud"
- name: AWS_REGION
  value: "us-east-1"
- name: DYNAMODB_TABLE_NAME
  value: "task-scheduler-logs-production"
- name: PERMISSIONS_TABLE_NAME
  value: "cost-center-permissions-production"
```

## Troubleshooting

### Error: "Unable to locate credentials"

**Causa**: El service account no tiene la anotación correcta o el rol no existe.

**Solución**:
1. Verificar anotación: `kubectl get sa kubectl-runner -n task-scheduler -o yaml`
2. Verificar rol: `aws iam get-role --role-name kubectl-runner-role`
3. Reiniciar deployment: `kubectl rollout restart deployment/task-scheduler -n task-scheduler`

### Error: "AccessDeniedException"

**Causa**: El rol no tiene permisos suficientes para DynamoDB.

**Solución**:
1. Verificar política adjunta: `aws iam list-attached-role-policies --role-name kubectl-runner-role`
2. Verificar permisos: `./scripts/validate-eks-iam-setup.sh`

### Error: "An error occurred (InvalidUserID.NotFound)"

**Causa**: El OIDC provider no está configurado correctamente.

**Solución**:
1. Verificar OIDC provider: `aws iam list-open-id-connect-providers`
2. Reconfigurar: `./scripts/setup-eks-iam-roles.sh`

### Error: "Table does not exist"

**Causa**: Las tablas DynamoDB no existen o tienen nombres diferentes.

**Solución**:
1. Verificar tablas: `aws dynamodb list-tables`
2. Crear tablas: `./scripts/create-dynamodb-tables.sh`
3. Verificar variables de entorno en el deployment

## Comandos Útiles

### Verificar Configuración

```bash
# Ver service account
kubectl get sa kubectl-runner -n task-scheduler -o yaml

# Ver deployment
kubectl get deployment task-scheduler -n task-scheduler -o yaml

# Ver logs
kubectl logs deployment/task-scheduler -n task-scheduler

# Ver eventos
kubectl get events -n task-scheduler --sort-by='.lastTimestamp'
```

### Verificar IAM

```bash
# Ver rol
aws iam get-role --role-name kubectl-runner-role

# Ver políticas adjuntas
aws iam list-attached-role-policies --role-name kubectl-runner-role

# Ver trust policy
aws iam get-role --role-name kubectl-runner-role --query 'Role.AssumeRolePolicyDocument'

# Ver OIDC providers
aws iam list-open-id-connect-providers
```

### Verificar DynamoDB

```bash
# Listar tablas
aws dynamodb list-tables

# Describir tabla
aws dynamodb describe-table --table-name task-scheduler-logs

# Ver items (limitado)
aws dynamodb scan --table-name task-scheduler-logs --max-items 5
```

## Seguridad

### Principio de Menor Privilegio

- El rol solo tiene acceso a las tablas específicas del proyecto
- Los permisos están limitados a las operaciones necesarias
- El trust policy está restringido al service account específico

### Rotación de Credenciales

- Las credenciales se rotan automáticamente por AWS
- No hay credenciales estáticas almacenadas en el cluster
- El acceso se basa en tokens temporales de OIDC

### Auditoría

- Todas las operaciones DynamoDB se registran en CloudTrail
- Los logs de la aplicación incluyen información de auditoría
- El acceso está limitado por namespace y service account

## Referencias

- [AWS IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [DynamoDB IAM Permissions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/using-identity-based-policies.html)
- [EKS OIDC Provider](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html)