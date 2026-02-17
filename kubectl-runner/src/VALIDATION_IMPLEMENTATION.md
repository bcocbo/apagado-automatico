# Cost Center Validation Implementation

## Overview
This document describes the cost center validation implementation for namespace activation and deactivation operations.

## Implementation Details

### Validation in Activation
The `activate_namespace` method validates:
1. Cost center authorization via `validate_namespace_activation`
2. Business hours constraints (max 5 namespaces during non-business hours)
3. Returns error if validation fails

### Validation in Deactivation
The `deactivate_namespace` method now validates:
1. Cost center authorization via `validate_cost_center_permissions`
2. Passes audit context (cost_center, user_id, operation_type, namespace) for logging
3. Returns error if cost center is not authorized

## Code Changes

### Modified Method: `deactivate_namespace`
Added cost center validation with audit logging before allowing deactivation:
```python
# Validate cost center permissions before deactivation
if not self.dynamodb_manager.validate_cost_center_permissions(
    cost_center,
    user_id=user_id,
    operation_type='namespace_deactivation',
    namespace=namespace
):
    return {'success': False, 'error': 'Cost center not authorized'}
```

### Modified Method: `validate_namespace_activation`
Enhanced with robust error handling and detailed validation:
```python
def validate_namespace_activation(self, cost_center, namespace, user_id=None, requested_by=None):
    """Validate if namespace can be activated with robust error handling
    
    Returns:
        tuple: (is_valid: bool, message: str, details: dict)
    """
    # Input validation
    # Namespace existence check
    # Cost center permissions validation
    # Business hours check
    # Namespace limit enforcement during non-business hours
    # Comprehensive error handling with detailed error types
```

**Key improvements:**
- Returns 3-tuple with validation status, message, and details dictionary
- Validates input parameters (namespace and cost_center)
- Checks namespace existence before validation
- Wraps all checks in try-except blocks for robust error handling
- Provides detailed error types in response: `validation_error`, `namespace_not_found`, `authorization_error`, `permission_check_error`, `count_error`, `limit_exceeded`, `unexpected_error`
- Defaults to business hours if check fails (safer behavior)
- Includes current active count and limits in success responses

### Modified Method: `create_task`
Enhanced to pass audit context during task creation validation:
```python
if not self.dynamodb_manager.validate_cost_center_permissions(
    cost_center,
    user_id=user_id,
    operation_type='task_creation',
    namespace=namespace
):
    return {'success': False, 'error': 'Cost center not authorized'}
```

## Testing

### Test File: `test_namespace_validation.py`
Comprehensive test suite that validates:
1. Activation with authorized cost center (should succeed)
2. Activation with unauthorized cost center (should fail)
3. Deactivation with authorized cost center (should succeed)
4. Deactivation with unauthorized cost center (should fail)
5. Activation with non-existent cost center (should fail)
6. Deactivation with non-existent cost center (should fail)

### Running Tests
```bash
# Ensure the backend is running
python3 kubectl-runner/src/test_namespace_validation.py
```

## API Behavior

### Activation Endpoint: POST /api/namespaces/{namespace}/activate
**Request Body:**
```json
{
  "cost_center": "string",
  "user_id": "string"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Namespace {namespace} activated successfully"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Cost center not authorized"
}
```

### Deactivation Endpoint: POST /api/namespaces/{namespace}/deactivate
**Request Body:**
```json
{
  "cost_center": "string",
  "user_id": "string"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Namespace {namespace} deactivated successfully"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Cost center not authorized"
}
```

## Error Handling

### Error Types Returned
The validation now returns detailed error types in the response dictionary:

- `validation_error`: Invalid input parameters (namespace or cost_center)
- `namespace_not_found`: Namespace doesn't exist in the cluster
- `kubectl_error`: Failed to execute kubectl commands
- `authorization_error`: Cost center is not authorized
- `permission_check_error`: Failed to validate permissions (DynamoDB error)
- `count_error`: Failed to check active namespace count
- `limit_exceeded`: Maximum namespace limit reached during non-business hours
- `unexpected_error`: Unexpected exception occurred

### Response Format
```python
# Success
(True, "Validation passed (current active: 2)", {
    'current_active_count': 2,
    'max_allowed': 5,
    'limit_applies': True
})

# Failure
(False, "Cost center 'invalid' is not authorized", {
    'error_type': 'authorization_error'
})
```

## Requirements Satisfied

This implementation satisfies the following acceptance criteria:

### From Requirements 1.5:
- ✓ Validates permissions of cost center before activating

### From Requirements 4.2:
- ✓ Validates permissions of cost center for all operations

### From Requirements 4.3:
- ✓ Registers all activities with their cost center associated

### From Requirements 2.2 (Error Handling):
- ✓ Robust error handling with try-except blocks
- ✓ Detailed error types for debugging and monitoring
- ✓ Graceful degradation on failures
- ✓ Input validation before operations

## Security Considerations

1. All operations require a valid, authorized cost center
2. Non-existent cost centers are treated as unauthorized (fail-safe default)
3. Validation occurs before any Kubernetes operations are performed
4. All operations are logged to DynamoDB for audit trail with complete context
5. Audit logs capture user identity, operation type, and validation source for compliance
6. Validation failures include detailed error messages in audit logs
7. Input validation prevents injection attacks and invalid operations
8. Namespace existence is verified before attempting operations
9. Defaults to business hours on check failure (safer, more permissive behavior)
