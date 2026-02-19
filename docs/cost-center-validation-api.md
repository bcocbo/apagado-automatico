# Cost Center Validation API

## Overview

The cost center validation endpoint allows you to check if a cost center has the necessary permissions to perform operations on namespaces.

## Endpoint

### Validate Cost Center

**GET** `/api/cost-centers/{cost_center}/validate`

Validates if a cost center has permissions and returns detailed information about its configuration.

#### Parameters

- `cost_center` (path parameter): The name of the cost center to validate

#### Response

```json
{
  "cost_center": "string",
  "is_authorized": boolean,
  "details": {
    "cost_center": "string",
    "is_authorized": boolean,
    "max_concurrent_namespaces": number,
    "authorized_namespaces": ["string"],
    "created_at": number,
    "updated_at": number
  }
}
```

#### Response Fields

- `cost_center`: The name of the cost center being validated
- `is_authorized`: Boolean indicating if the cost center has permissions
- `details`: Additional details (only present if authorized):
  - `max_concurrent_namespaces`: Maximum number of concurrent namespaces allowed
  - `authorized_namespaces`: List of specific namespaces this cost center can access
  - `created_at`: Unix timestamp when permissions were created
  - `updated_at`: Unix timestamp when permissions were last updated

#### Examples

**Request:**
```bash
curl http://localhost:8080/api/cost-centers/development/validate
```

**Response (Authorized):**
```json
{
  "cost_center": "development",
  "is_authorized": true,
  "details": {
    "cost_center": "development",
    "is_authorized": true,
    "max_concurrent_namespaces": 5,
    "authorized_namespaces": ["dev-ns-1", "dev-ns-2"],
    "created_at": 1707840000,
    "updated_at": 1707840000
  }
}
```

**Response (Unauthorized):**
```json
{
  "cost_center": "unknown-center",
  "is_authorized": false,
  "details": null
}
```

**Response (Error):**
```json
{
  "error": "Error message describing what went wrong"
}
```

## Usage in Operations

The system automatically validates cost centers before performing operations. The validation checks:

1. If the cost center exists in the permissions table
2. If the cost center is authorized (`is_authorized = true`)
3. During namespace activation in non-business hours, if the namespace limit would be exceeded

### Namespace Activation Flow
When activating a namespace, the system:
- Validates input parameters (namespace name and cost center)
- Checks if the namespace exists in the cluster
- Validates cost center permissions
- Checks if it's non-business hours using configurable timezone and business hours
- Enforces the 5 namespace limit during non-business hours (weekends, outside business hours, or holidays)
- Returns detailed error information including error type for debugging
- Scales up namespace resources if validation passes

**Validation Response Format:**
The validation now returns a 3-tuple: `(is_valid: bool, message: str, details: dict)`
- Success: `(True, "Validation passed (current active: 2)", {'current_active_count': 2, 'max_allowed': 5})`
- Failure: `(False, "Cost center 'invalid' is not authorized", {'error_type': 'authorization_error'})`

**Error Types:**
- `validation_error`: Invalid input parameters
- `namespace_not_found`: Namespace doesn't exist
- `authorization_error`: Cost center not authorized
- `permission_check_error`: Failed to validate permissions
- `count_error`: Failed to check namespace limits
- `limit_exceeded`: Maximum namespace limit reached
- `unexpected_error`: Unexpected exception

**Business Hours Configuration**: The system uses configurable business hours detection. See `docs/business-hours-configuration.md` for detailed configuration options including timezone, business hours, and holiday settings.

### Namespace Deactivation Flow
When deactivating a namespace, the system:
- Validates cost center permissions before allowing deactivation
- Returns an error if the cost center is not authorized
- Scales down namespace resources to 0 replicas if validation passes
- Logs the deactivation activity to DynamoDB

### Task Creation Flow
When creating a scheduled task, the system:
- Validates that the `cost_center` field is provided (returns 400 if missing)
- Validates cost center permissions before creating the task
- Returns 403 error if the cost center is not authorized
- Creates and schedules the task if validation passes
- Logs the task creation to DynamoDB
- Supports optional calendar fields (`start` and `allDay`) for frontend calendar integration

## Related Endpoints

- **POST** `/api/cost-centers/{cost_center}/permissions` - Set or update permissions for a cost center
- **GET** `/api/cost-centers` - List all configured cost centers
- **GET** `/api/business-hours` - Get current business hours configuration and status
- **POST** `/api/namespaces/{namespace}/activate` - Activate a namespace (requires valid cost center)
- **POST** `/api/namespaces/{namespace}/deactivate` - Deactivate a namespace (requires valid cost center)
- **POST** `/api/tasks` - Create a scheduled task (requires valid cost center)

### Task Creation API

**POST** `/api/tasks`

Creates a new scheduled task with cost center validation.

#### Request Body

```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "command": "string (optional, required for 'command' operation_type)",
  "schedule": "string (required, cron expression)",
  "namespace": "string (required)",
  "cost_center": "string (required)",
  "operation_type": "string (optional, default: 'command')",
  "start": "string (optional, ISO datetime for calendar display)",
  "allDay": "boolean (optional, default: false, for calendar display)",
  "requested_by": "string (optional, for audit tracking)"
}
```

#### Response

```json
{
  "id": "string (UUID)",
  "title": "string",
  "command": "string",
  "schedule": "string",
  "namespace": "string",
  "cost_center": "string",
  "operation_type": "string",
  "status": "pending",
  "created_at": "string (ISO datetime)",
  "start": "string (ISO datetime)",
  "allDay": "boolean",
  "created_by": "string",
  "last_run": null,
  "next_run": "string (ISO datetime)",
  "run_count": 0,
  "success_count": 0,
  "error_count": 0
}
```

#### Field Descriptions

- `title`: Descriptive name for the task
- `description`: Optional detailed description
- `command`: kubectl command to execute (required for 'command' operation_type)
- `schedule`: Cron expression defining when the task runs
- `namespace`: Target Kubernetes namespace
- `cost_center`: Cost center for permission validation
- `operation_type`: Type of operation ('command', 'activate', 'deactivate')
- `start`: Optional start date/time for calendar visualization (defaults to creation time)
- `allDay`: Optional flag for all-day calendar events (defaults to false)
- `requested_by`: Optional user identifier for audit tracking

## Frontend Integration

The frontend API client (`frontend/src/api.js`) includes a method to validate cost centers:

```javascript
// Validate cost center permissions
const result = await apiClient.validateCostCenter('development', 'web-user');

if (result.success && result.data.is_authorized) {
    console.log('Cost center is authorized');
    console.log('Max namespaces:', result.data.details.max_concurrent_namespaces);
} else {
    console.error('Cost center validation failed');
}
```

**Method Signature:**
```javascript
async validateCostCenter(costCenter, userId = 'web-user')
```

**Parameters:**
- `costCenter` (string): The cost center name to validate
- `userId` (string, optional): User ID for audit tracking (defaults to 'web-user')

**Returns:**
- `success` (boolean): Whether the API call succeeded
- `data` (object): The validation response (see Response section above)
- `error` (string): Error message if the call failed

## Testing

A test script is available at `kubectl-runner/src/test_cost_center_validation.py` to verify the endpoint functionality:

```bash
python3 kubectl-runner/src/test_cost_center_validation.py
```

The test script validates:
1. Authorized cost center validation
2. Non-existent cost center validation
3. Setting permissions and validating the changes
