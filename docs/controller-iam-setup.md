# Configuración IAM para el Controlador de Namespaces

## 🎯 Objetivo

Configurar un IAM Role específico para que el controlador de namespaces pueda acceder a DynamoDB usando IRSA (IAM Roles for Service Accounts) en lugar de credenciales estáticas.

## 📋 Prerrequisitos

- Cluster EKS con OIDC Identity Provider habilitado
- AWS CLI configurado con permisos administrativos
- kubectl configurado para acceder al cluster
- Controlador desplegado en el namespace `encendido-eks`

## 🔧 Configuración Automática

### Usando el Script

```bash
# Hacer el script ejecutable
chmod +x scripts/setup-controller-iam-role.sh

# Ejecutar el script
./scripts/setup-controller-iam-role.sh
```

El script te pedirá:
- **Nombre del cluster EKS**: El nombre de tu cluster
- **Región AWS**: La región donde está tu cluster (default: us-east-1)

## 🔐 Configuración Manual

### Paso 1: Obtener información del cluster EKS

```bash
# Obtener el OIDC Issuer URL
CLUSTER_NAME="tu-cluster-name"
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

OIDC_ISSUER=$(aws eks describe-cluster \
    --name $CLUSTER_NAME \
    --region $AWS_REGION \
    --query "cluster.identity.oidc.issuer" \
    --output text)

echo "OIDC Issuer: $OIDC_ISSUER"
```

### Paso 2: Verificar OIDC Identity Provider

```bash
# Verificar si existe
OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER#https://}"
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN"

# Si no existe, crearlo
if [ $? -ne 0 ]; then
    THUMBPRINT=$(echo | openssl s_client -servername ${OIDC_ISSUER#https://} \
        -connect ${OIDC_ISSUER#https://}:443 2>/dev/null | \
        openssl x509 -fingerprint -noout -sha1 | \
        sed 's/://g' | awk -F= '{print tolower($2)}')
    
    aws iam create-open-id-connect-provider \
        --url $OIDC_ISSUER \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list $THUMBPRINT
fi
```

### Paso 3: Crear Policy para DynamoDB

```bash
# Crear archivo de policy
cat > dynamodb-policy.json << EOF
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
                "dynamodb:DescribeTable",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/NamespaceSchedules",
                "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/NamespaceSchedules/index/*"
            ]
        }
    ]
}
EOF

# Crear la policy
aws iam create-policy \
    --policy-name NamespaceControllerDynamoDBPolicy \
    --policy-document file://dynamodb-policy.json \
    --description "Policy para que el controlador de namespaces acceda a DynamoDB"
```

### Paso 4: Crear Trust Policy para IRSA

```bash
# Crear archivo de trust policy
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER#https://}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_ISSUER#https://}:sub": "system:serviceaccount:encendido-eks:scaler-sa",
                    "${OIDC_ISSUER#https://}:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
EOF
```

### Paso 5: Crear IAM Role

```bash
# Crear el role
aws iam create-role \
    --role-name NamespaceControllerRole \
    --assume-role-policy-document file://trust-policy.json \
    --description "Role para el controlador de namespaces con acceso a DynamoDB"

# Attachar la policy al role
aws iam attach-role-policy \
    --role-name NamespaceControllerRole \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/NamespaceControllerDynamoDBPolicy
```

### Paso 6: Crear tabla DynamoDB (si no existe)

```bash
# Verificar si la tabla existe
aws dynamodb describe-table --table-name NamespaceSchedules --region $AWS_REGION

# Si no existe, crearla
if [ $? -ne 0 ]; then
    aws dynamodb create-table \
        --table-name NamespaceSchedules \
        --attribute-definitions \
            AttributeName=namespace,AttributeType=S \
        --key-schema \
            AttributeName=namespace,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION
    
    # Esperar a que esté activa
    aws dynamodb wait table-exists --table-name NamespaceSchedules --region $AWS_REGION
fi
```

## 🔗 Configuración del ServiceAccount

### Anotar el ServiceAccount

```bash
# Obtener el ARN del role
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/NamespaceControllerRole"

# Anotar el ServiceAccount
kubectl annotate serviceaccount scaler-sa -n encendido-eks \
    eks.amazonaws.com/role-arn=$ROLE_ARN
```

### Verificar la anotación

```bash
kubectl describe serviceaccount scaler-sa -n encendido-eks
```

Deberías ver algo como:
```
Annotations:  eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/NamespaceControllerRole
```

## 🚀 Aplicar los cambios

### Reiniciar el deployment

```bash
# Reiniciar el deployment para que tome la nueva configuración
kubectl rollout restart deployment namespace-scaler -n encendido-eks

# Verificar el estado del rollout
kubectl rollout status deployment namespace-scaler -n encendido-eks
```

### Verificar los logs

```bash
# Ver los logs del controlador
kubectl logs -f deployment/namespace-scaler -n encendido-eks

# Buscar mensajes de éxito en la conexión a DynamoDB
kubectl logs deployment/namespace-scaler -n encendido-eks | grep -i dynamodb
```

## ✅ Verificación

### Verificar que el pod tiene las credenciales correctas

```bash
# Ejecutar un comando dentro del pod para verificar las credenciales
kubectl exec -it deployment/namespace-scaler -n encendido-eks -- env | grep AWS

# Deberías ver variables como:
# AWS_ROLE_ARN=arn:aws:iam::123456789012:role/NamespaceControllerRole
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

### Probar acceso a DynamoDB

```bash
# Ejecutar un comando de prueba dentro del pod
kubectl exec -it deployment/namespace-scaler -n encendido-eks -- python3 -c "
import boto3
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('NamespaceSchedules')
print('Conexión a DynamoDB exitosa:', table.table_status)
"
```

### Verificar health check

```bash
# Verificar que el health check pase
kubectl get pods -n encendido-eks -l app=namespace-scaler

# El pod debería estar en estado Running y Ready
```

## 🔍 Troubleshooting

### Error: "Unable to locate credentials"

**Causa**: El ServiceAccount no tiene la anotación correcta o el IAM Role no existe.

**Solución**:
```bash
# Verificar la anotación
kubectl describe sa scaler-sa -n encendido-eks

# Verificar que el role existe
aws iam get-role --role-name NamespaceControllerRole
```

### Error: "Access Denied" en DynamoDB

**Causa**: El IAM Role no tiene los permisos correctos para DynamoDB.

**Solución**:
```bash
# Verificar las policies attachadas al role
aws iam list-attached-role-policies --role-name NamespaceControllerRole

# Verificar el contenido de la policy
aws iam get-policy-version \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/NamespaceControllerDynamoDBPolicy \
    --version-id v1
```

### Error: "AssumeRoleWithWebIdentity failed"

**Causa**: La trust policy del IAM Role no está configurada correctamente.

**Solución**:
```bash
# Verificar la trust policy
aws iam get-role --role-name NamespaceControllerRole --query 'Role.AssumeRolePolicyDocument'

# Verificar que el OIDC Issuer sea correcto
aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.identity.oidc.issuer"
```

### Pod no puede asumir el role

**Causa**: El OIDC Identity Provider no está configurado o el thumbprint es incorrecto.

**Solución**:
```bash
# Listar OIDC providers
aws iam list-open-id-connect-providers

# Verificar el thumbprint
OIDC_ISSUER=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text)
echo | openssl s_client -servername ${OIDC_ISSUER#https://} -connect ${OIDC_ISSUER#https://}:443 2>/dev/null | openssl x509 -fingerprint -noout -sha1
```

## 📊 Recursos Creados

Después de ejecutar la configuración, tendrás:

### IAM Resources
- **Policy**: `NamespaceControllerDynamoDBPolicy`
- **Role**: `NamespaceControllerRole`
- **OIDC Provider**: Para tu cluster EKS (si no existía)

### DynamoDB Resources
- **Table**: `NamespaceSchedules` (con billing mode PAY_PER_REQUEST)

### Kubernetes Resources
- **ServiceAccount**: `scaler-sa` (anotado con el IAM Role ARN)

## 🔒 Seguridad

### Principios aplicados

1. **Principio de menor privilegio**: El role solo tiene permisos específicos para DynamoDB
2. **Restricción por ServiceAccount**: Solo el SA `scaler-sa` en el namespace `encendido-eks` puede asumir el role
3. **Sin credenciales estáticas**: Usa tokens temporales de OIDC
4. **Auditoría**: Todas las operaciones quedan registradas en CloudTrail

### Permisos otorgados

El IAM Role tiene permisos para:
- Leer, escribir, actualizar y eliminar items en la tabla `NamespaceSchedules`
- Realizar operaciones de batch en la tabla
- Describir la tabla y sus índices
- **NO** tiene permisos para crear o eliminar tablas
- **NO** tiene permisos para otras tablas de DynamoDB

## 💰 Costos

- **IAM Role y Policy**: $0.00
- **OIDC Provider**: $0.00
- **DynamoDB**: Pay-per-request (muy bajo costo para este uso)
- **Tokens OIDC**: $0.00 (incluidos en EKS)

## 🎉 ¡Listo!

Una vez completada la configuración, tu controlador debería poder acceder a DynamoDB sin errores de credenciales. El health check debería pasar y los logs no deberían mostrar errores relacionados con AWS credentials.