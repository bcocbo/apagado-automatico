# 🚀 Namespace Controller - Test Simple DynamoDB

Sistema básico para probar la conectividad y operaciones CRUD con DynamoDB.

## 🎯 Objetivo

Este frontend y backend simplificados están diseñados para:
- ✅ Probar la conexión con DynamoDB
- ✅ Realizar operaciones de lectura (READ)
- ✅ Realizar operaciones de escritura (WRITE)
- ✅ Validar las credenciales de AWS
- ✅ Crear/eliminar schedules de namespaces

## 🛠️ Requisitos

- Python 3.7+
- AWS CLI configurado con credenciales válidas
- Acceso a DynamoDB (permisos de lectura/escritura)

## 🚀 Inicio Rápido

### 1. Configurar AWS (si no está configurado)

```bash
# Instalar AWS CLI si no está instalado
pip install awscli

# Configurar credenciales
aws configure
```

### 2. Ejecutar el sistema

```bash
# Hacer ejecutable el script
chmod +x run_simple_test.sh

# Ejecutar el test
./run_simple_test.sh
```

### 3. Abrir el navegador

Ir a: http://localhost:8080

## 🎮 Funcionalidades del Frontend

### 📊 Estado del Sistema
- Verifica la conexión con DynamoDB
- Muestra el estado de los componentes
- Crea automáticamente la tabla si no existe

### ➕ Crear Schedule
- Formulario simple para crear schedules
- Validación de campos requeridos
- Almacenamiento directo en DynamoDB

### 📋 Ver Schedules
- Lista todos los schedules existentes
- Información detallada de cada schedule
- Opción para eliminar schedules

### 📝 Log de Operaciones
- Registro en tiempo real de todas las operaciones
- Mensajes de éxito y error
- Timestamps de cada operación

## 🔧 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Estado del sistema |
| GET | `/api/schedules` | Listar todos los schedules |
| POST | `/api/schedules` | Crear nuevo schedule |
| GET | `/api/schedules/{id}` | Obtener schedule específico |
| DELETE | `/api/schedules/{id}` | Eliminar schedule |
| GET | `/api/test-write` | Test de escritura rápido |

## 📋 Ejemplo de Schedule

```json
{
  "namespace": "production-app",
  "startup_time": "08:00",
  "shutdown_time": "18:00",
  "timezone": "America/Bogota",
  "days_of_week": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "enabled": true,
  "metadata": {
    "business_unit": "Engineering",
    "cost_savings_target": 1500
  }
}
```

## 🔍 Troubleshooting

### Error: "No se encontraron credenciales de AWS"
```bash
# Verificar credenciales
aws sts get-caller-identity

# Si no están configuradas
aws configure
```

### Error: "Tabla no existe"
- El sistema creará automáticamente la tabla `namespace-schedules-test`
- Asegúrate de tener permisos de DynamoDB

### Error: "Access Denied"
- Verificar que las credenciales tienen permisos de DynamoDB
- Política mínima requerida:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/namespace-schedules-test"
        }
    ]
}
```

## 🎯 Próximos Pasos

Una vez que este sistema básico funcione correctamente:

1. ✅ Confirmar conectividad con DynamoDB
2. ✅ Validar operaciones CRUD
3. 🔄 Migrar al frontend completo de React
4. 🔄 Implementar funcionalidades avanzadas
5. 🔄 Agregar autenticación y autorización

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs en la consola
2. Verifica las credenciales de AWS
3. Confirma los permisos de DynamoDB
4. Revisa el log de operaciones en el frontend