# User Tracking Implementation

## Overview

This document describes the implementation of comprehensive user tracking across all operations in the namespace scheduler system. Every operation now captures the user who requested it, providing complete accountability and traceability.

## Features

### 1. Consistent User Capture

All operations now capture user information through two fields:

- **`requested_by`**: Primary field for user tracking (who initiated the request)
- **`user_id`**: Secondary field for backward compatibility

The system prioritizes `requested_by` over `user_id` when both are provided, ensuring consistent tracking.

### 2. Default Behavior

When no user information is provided:
- API endpoints default to `'anonymous'`
- System operations default to `'system'`
- Validation operations default to `'api_request'`

This ensures every operation has a traceable user identifier.

## Implementation Details

### DynamoDB Schema Updates

All activity logs now include:

```json
{
  "namespace_name": "string (hash key)",
  "timestamp_start": "number (range key)",
  "operation_type": "string",
  "cost_center": "string",
  "requested_by": "string (primary user field)",
  "user_id": "string (backward compatibility)",
  "status": "string",
  "created_at": "ISO datetime",
  "id": "UUID"
}
```

### Task Schema Updates

Tasks now track who created them:

```json
{
  "id": "string",
  "title": "string",
  "created_by": "string (user who created the task)",
  "created_at": "ISO datetime",
  ...
}
```

## API Changes

### 1. Namespace Activation

**Endpoint**: `POST /api/namespaces/<namespace>/activate`

**Request Body**:
```json
{
  "cost_center": "development",
  "user_id": "john.doe",
  "requested_by": "jane.smith"  // Optional, defaults to user_id
}
```

**Behavior**:
- If `requested_by` is provided, it's used as the primary user identifier
- If only `user_id` is provided, it's used for both fields
- If neither is provided, defaults to `'anonymous'`

### 2. Namespace Deactivation

**Endpoint**: `POST /api/namespaces/<namespace>/deactivate`

**Request Body**:
```json
{
  "cost_center": "development",
  "user_id": "john.doe",
  "requested_by": "jane.smith"  // Optional, defaults to user_id
}
```

**Behavior**: Same as activation

### 3. Task Creation

**Endpoint**: `POST /api/tasks`

**Request Body**:
```json
{
  "title": "My Task",
  "operation_type": "activate",
  "namespace": "my-app",
  "cost_center": "development",
  "user_id": "john.doe",
  "requested_by": "jane.smith",  // Optional, defaults to user_id
  "schedule": "0 9 * * 1-5"
}
```

**Response**:
```json
{
  "id": "task-uuid",
  "title": "My Task",
  "created_by": "jane.smith",  // Captured from requested_by
  ...
}
```

### 4. Cost Center Validation

**Endpoint**: `GET /api/cost-centers/<cost_center>/validate`

**Query Parameters**:
- `user_id`: User identifier (optional, default: `'api_request'`)
- `requested_by`: Primary user identifier (optional, defaults to `user_id`)
- `operation_type`: Type of operation (optional)
- `namespace`: Namespace involved (optional)

**Example**:
```bash
GET /api/cost-centers/development/validate?user_id=john.doe&requested_by=jane.smith&operation_type=namespace_activation&namespace=my-app
```

## Code Changes

### 1. Enhanced `log_namespace_activity()`

```python
def log_namespace_activity(self, namespace_name, operation_type, cost_center, 
                          user_id=None, requested_by=None, **kwargs):
    """Log namespace activity to DynamoDB with user tracking"""
    
    # Capture user information
    if requested_by:
        item['requested_by'] = requested_by
        item['user_id'] = requested_by
    elif user_id:
        item['user_id'] = user_id
        item['requested_by'] = user_id
    else:
        item['requested_by'] = 'system'
        item['user_id'] = 'system'
```

### 2. Enhanced `_log_validation_audit()`

```python
def _log_validation_audit(self, validation_type, cost_center, validation_result, 
                         validation_source, user_id=None, requested_by=None, 
                         operation_type=None, namespace=None, error_message=None, **kwargs):
    """Log validation audit events to DynamoDB with user tracking"""
    
    # Capture user information
    if requested_by:
        audit_item['requested_by'] = requested_by
        audit_item['user_id'] = requested_by
    elif user_id:
        audit_item['user_id'] = user_id
        audit_item['requested_by'] = user_id
    else:
        audit_item['requested_by'] = 'system'
        audit_item['user_id'] = 'system'
```

### 3. Updated Method Signatures

All methods now accept `requested_by` parameter:

- `validate_cost_center_permissions(cost_center, user_id=None, requested_by=None, ...)`
- `validate_namespace_activation(cost_center, namespace, user_id=None, requested_by=None)`
- `activate_namespace(namespace, cost_center, user_id=None, requested_by=None)`
- `deactivate_namespace(namespace, cost_center, user_id=None, requested_by=None)`
- `add_task(task_data)` - extracts `requested_by` from task_data

## Usage Examples

### Example 1: Namespace Activation with User Tracking

```bash
curl -X POST http://localhost:8080/api/namespaces/my-app/activate \
  -H "Content-Type: application/json" \
  -d '{
    "cost_center": "development",
    "user_id": "john.doe",
    "requested_by": "jane.smith"
  }'
```

**DynamoDB Log**:
```json
{
  "namespace_name": "my-app",
  "operation_type": "manual_activation",
  "cost_center": "development",
  "requested_by": "jane.smith",
  "user_id": "jane.smith",
  "timestamp_start": 1234567890
}
```

### Example 2: Task Creation with User Tracking

```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Daily Activation",
    "operation_type": "activate",
    "namespace": "my-app",
    "cost_center": "development",
    "requested_by": "admin@company.com",
    "schedule": "0 9 * * 1-5"
  }'
```

**Task Object**:
```json
{
  "id": "task-uuid",
  "title": "Daily Activation",
  "created_by": "admin@company.com",
  "created_at": "2024-01-15T10:30:00"
}
```

### Example 3: Query Operations by User

```python
# Query all operations by a specific user
response = table.scan(
    FilterExpression='requested_by = :user',
    ExpressionAttributeValues={
        ':user': 'jane.smith'
    }
)

operations = response['Items']
```

## Testing

A comprehensive test suite is provided in `test_user_tracking.py`:

```bash
python3 kubectl-runner/src/test_user_tracking.py
```

**Test Coverage**:
1. Namespace activation with `requested_by`
2. Namespace deactivation with `requested_by`
3. Task creation with `requested_by`
4. Validation with `requested_by`
5. Default behavior when no user provided

## Benefits

### 1. Complete Accountability
Every operation is traceable to a specific user, providing full accountability for all actions in the system.

### 2. Audit Trail
Complete audit trail of who performed what operations, when, and on which resources.

### 3. Security and Compliance
Meets security and compliance requirements for user tracking and activity logging.

### 4. Troubleshooting
Easier to identify who performed problematic operations and investigate issues.

### 5. Analytics
Analyze user behavior patterns, identify power users, and understand system usage.

## Query Patterns

### Query 1: All Operations by User

```python
# Scan for all operations by a user
response = table.scan(
    FilterExpression='requested_by = :user',
    ExpressionAttributeValues={
        ':user': 'john.doe'
    }
)
```

### Query 2: User Operations on Specific Namespace

```python
# Query operations by user on a namespace
response = table.query(
    KeyConditionExpression='namespace_name = :ns',
    FilterExpression='requested_by = :user',
    ExpressionAttributeValues={
        ':ns': 'my-app',
        ':user': 'john.doe'
    }
)
```

### Query 3: Recent Operations by User

```python
# Query recent operations by user
from datetime import datetime, timedelta

one_week_ago = int((datetime.now() - timedelta(days=7)).timestamp())

response = table.scan(
    FilterExpression='requested_by = :user AND timestamp_start >= :ts',
    ExpressionAttributeValues={
        ':user': 'john.doe',
        ':ts': one_week_ago
    }
)
```

## Migration Notes

### Backward Compatibility

The implementation maintains backward compatibility:

- Existing code using only `user_id` continues to work
- `user_id` is automatically copied to `requested_by` when not provided
- Old logs without `requested_by` can be queried using `user_id`

### Recommended Migration Path

1. **Phase 1**: Deploy the updated code (backward compatible)
2. **Phase 2**: Update API clients to send `requested_by`
3. **Phase 3**: Update frontend to capture and send user information
4. **Phase 4**: Add GSI on `requested_by` for efficient queries (optional)

## Future Enhancements

### 1. User Activity Dashboard
Create a dashboard showing:
- Operations per user
- Most active users
- User activity timeline

### 2. User-Based Access Control
Implement role-based access control based on user identity:
- Restrict operations to authorized users
- Implement approval workflows

### 3. DynamoDB GSI for User Queries
Add a Global Secondary Index on `requested_by` for efficient user-based queries:

```python
GlobalSecondaryIndexes=[
    {
        'IndexName': 'requested-by-timestamp-index',
        'KeySchema': [
            {'AttributeName': 'requested_by', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp_start', 'KeyType': 'RANGE'}
        ],
        'Projection': {'ProjectionType': 'ALL'},
        'BillingMode': 'PAY_PER_REQUEST'
    }
]
```

### 4. User Activity Reports
Generate periodic reports:
- Weekly user activity summary
- Monthly operations by user
- Anomaly detection for unusual user behavior

## Security Considerations

### 1. User Identity Verification
The system currently trusts the `requested_by` field from API requests. Consider:
- Implementing authentication middleware
- Validating user identity with SSO/OAuth
- Using JWT tokens to verify user claims

### 2. PII Protection
User identifiers may be considered PII. Ensure:
- Proper access controls on DynamoDB table
- Encryption at rest and in transit
- Compliance with data protection regulations

### 3. Audit Log Integrity
Protect audit logs from tampering:
- Restrict write access to application service account only
- Consider write-once storage for critical audit logs
- Implement log verification mechanisms

## Troubleshooting

### Issue: Missing `requested_by` in Logs

**Cause**: API client not sending `requested_by` or `user_id`

**Solution**: 
- Check API request payload
- Verify frontend is capturing user information
- Review default values in endpoints

### Issue: Incorrect User in Logs

**Cause**: Wrong user identifier being passed

**Solution**:
- Verify authentication middleware is setting correct user
- Check that frontend is passing correct user identifier
- Review user mapping logic

### Issue: Cannot Query by User

**Cause**: No GSI on `requested_by` field

**Solution**:
- Use `scan` operation with filter (less efficient)
- Create GSI on `requested_by` for efficient queries
- Consider using DynamoDB Streams for user activity aggregation
