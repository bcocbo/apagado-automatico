# Audit Logging Implementation

## Overview

This document describes the audit logging implementation for validation events in the namespace scheduler system. All validation operations are now logged to DynamoDB for compliance, security, and troubleshooting purposes.

**Implementation Status**: ✅ Complete - All cost center validation operations now include comprehensive audit logging with full context capture (user ID, operation type, namespace, cluster name, validation source, and error details).

## Features

### 1. Validation Audit Logging

All cost center permission validations are now logged to DynamoDB with the following information:

- **Validation Type**: Type of validation performed (e.g., `cost_center_permission`)
- **Cost Center**: The cost center being validated
- **Validation Result**: `success` or `failure`
- **Validation Source**: Where the validation data came from (`cache`, `dynamodb`, or `error`)
- **User ID**: Who requested the operation (if available)
- **Operation Type**: What operation triggered the validation (e.g., `namespace_activation`, `task_creation`)
- **Namespace**: The namespace involved (if applicable)
- **Cluster Name**: The EKS cluster where the operation is being performed
- **Error Message**: Details if validation failed (e.g., "Cost center not found")
- **Timestamp**: When the validation occurred

### 2. Logged Operations

Audit logs are created for the following validation scenarios:

1. **Direct Cost Center Validation** (`/api/cost-centers/<cost_center>/validate`)
   - User can pass `user_id`, `operation_type`, and `namespace` as query parameters
   - Logs validation result with all context
   - Default `user_id`: `api_request`, default `operation_type`: `permission_check`

2. **Namespace Activation Validation**
   - Automatically logs validation when activating a namespace
   - Includes user ID and namespace information from request body
   - Operation type: `namespace_activation`
   - Captures validation source (cache or DynamoDB)

3. **Namespace Deactivation Validation**
   - Automatically logs validation when deactivating a namespace
   - Includes user ID and namespace information from request body
   - Operation type: `namespace_deactivation`
   - Captures validation source (cache or DynamoDB)

4. **Task Creation Validation**
   - Automatically logs validation when creating a scheduled task
   - Includes user ID, namespace, and task details from request body
   - Operation type: `task_creation`
   - Captures validation source (cache or DynamoDB)

All operations now pass complete audit context to the validation function, ensuring comprehensive audit trails.

## DynamoDB Schema

Audit log entries are stored in the main activity logs table with the following structure:

```json
{
  "namespace_name": "string (hash key)",
  "timestamp_start": "number (range key)",
  "operation_type": "validation_cost_center_permission",
  "cost_center": "string",
  "validation_result": "success|failure",
  "validation_source": "cache|dynamodb|error",
  "user_id": "string (optional)",
  "requested_operation": "string (optional)",
  "cluster_name": "string",
  "error_message": "string (optional)",
  "status": "completed",
  "created_at": "ISO datetime",
  "id": "UUID"
}
```

## API Changes

### Updated Endpoint: `/api/cost-centers/<cost_center>/validate`

**Query Parameters** (all optional):
- `user_id`: Identifier of the user making the request (default: `api_request`)
- `operation_type`: Type of operation being validated (default: `permission_check`)
- `namespace`: Namespace involved in the operation

**Example Request:**
```bash
GET /api/cost-centers/development/validate?user_id=john.doe&operation_type=namespace_activation&namespace=my-app
```

**Response:**
```json
{
  "cost_center": "development",
  "is_authorized": true,
  "details": {
    "cost_center": "development",
    "is_authorized": true,
    "max_concurrent_namespaces": 5,
    "authorized_namespaces": [],
    "created_at": 1234567890,
    "updated_at": 1234567890
  }
}
```

## Implementation Details

### Method: `_log_validation_audit()`

New private method in `DynamoDBManager` class that handles audit logging:

```python
def _log_validation_audit(self, validation_type, cost_center, validation_result, 
                          validation_source, user_id=None, operation_type=None, 
                          namespace=None, error_message=None, **kwargs):
    """Log validation audit events to DynamoDB"""
```

**Parameters:**
- `validation_type`: Type of validation (e.g., `cost_center_permission`)
- `cost_center`: Cost center being validated
- `validation_result`: Boolean indicating success/failure
- `validation_source`: Source of validation data (`cache`, `dynamodb`, `error`)
- `user_id`: Optional user identifier
- `operation_type`: Optional operation type
- `namespace`: Optional namespace
- `error_message`: Optional error details
- `**kwargs`: Additional fields to include in the audit log

**Behavior:**
- Logs are written synchronously to DynamoDB
- Failures in audit logging do not block the validation operation
- Errors in audit logging are logged to application logs but do not propagate to the caller
- Each validation attempt generates exactly one audit log entry
- Audit logs capture the complete validation context including source (cache/dynamodb/error)

### Updated Method: `validate_cost_center_permissions()`

Enhanced to accept audit parameters and log all validation attempts:

```python
def validate_cost_center_permissions(self, cost_center, user_id=None, 
                                    operation_type=None, namespace=None):
    """Validate if cost center has permissions (with caching and audit logging)"""
```

**Changes:**
- Accepts additional parameters for audit context (`user_id`, `operation_type`, `namespace`)
- Logs validation result from cache hits with `validation_source: cache`
- Logs validation result from DynamoDB queries with `validation_source: dynamodb`
- Logs validation failures with error messages and `validation_source: error`
- Logs "not found" scenarios with appropriate error messages
- All validation paths (success, failure, error) now generate audit logs
- Audit logging is non-blocking - validation continues even if logging fails

## Querying Audit Logs

### Query by Namespace

```python
response = table.query(
    KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
    ExpressionAttributeValues={
        ':ns': 'my-namespace',
        ':ts': start_timestamp
    }
)

# Filter for validation logs
validation_logs = [
    log for log in response['Items'] 
    if log.get('operation_type', '').startswith('validation_')
]
```

### Query by Cost Center

Use the `cost-center-index` GSI:

```python
response = table.query(
    IndexName='cost-center-index',
    KeyConditionExpression='cost_center = :cc AND timestamp_start >= :ts',
    ExpressionAttributeValues={
        ':cc': 'development',
        ':ts': start_timestamp
    }
)
```

## Testing

A comprehensive test suite is provided in `test_audit_logging.py`:

```bash
python3 kubectl-runner/src/test_audit_logging.py
```

**Test Coverage:**
1. Authorized cost center validation with audit log verification
2. Unauthorized cost center validation with audit log verification
3. Namespace activation validation with audit log verification
4. Task creation validation with audit log verification

## Performance Considerations

### Cache Integration

Audit logging is fully integrated with the permissions cache:
- **Cache hits** are logged with `validation_source: cache` before returning the cached result
- **Cache misses** trigger DynamoDB lookup and are logged with `validation_source: dynamodb`
- **Errors** during validation are logged with `validation_source: error`
- **Not found** cost centers are logged with appropriate error messages
- Audit logging does not impact cache performance or validation logic
- Cache behavior remains unchanged - audit logging is transparent to the caching layer

### Error Handling

- Audit logging failures are caught and logged but do not affect validation
- Validation operations continue even if audit logging fails
- This ensures system availability is not impacted by audit logging issues

### DynamoDB Write Capacity

- Each validation generates one write to DynamoDB
- Consider provisioned capacity or on-demand billing based on validation frequency
- Audit logs use the same table as activity logs for cost efficiency

## Security and Compliance

### Data Retention

Audit logs are stored indefinitely in DynamoDB. Consider implementing:
- TTL (Time To Live) for automatic cleanup of old logs
- Archival to S3 for long-term storage
- Compliance with data retention policies

### Sensitive Information

Audit logs may contain:
- User identifiers
- Cost center names
- Namespace names
- Operation types

Ensure proper access controls are in place for the DynamoDB table.

## Future Enhancements

Potential improvements to the audit logging system:

1. **Structured Query API**: Add endpoints to query audit logs by various criteria
2. **Real-time Alerts**: Trigger alerts on suspicious validation patterns
3. **Audit Log Export**: Provide API to export audit logs for external analysis
4. **Validation Metrics**: Aggregate validation statistics for monitoring
5. **User Activity Reports**: Generate reports of user activity based on audit logs

## Troubleshooting

### Audit Logs Not Appearing

1. Check DynamoDB table permissions
2. Verify IAM role has write access to the table
3. Check application logs for audit logging errors
4. Ensure table name is correctly configured in environment variables

### High DynamoDB Costs

1. Review validation frequency
2. Consider increasing cache TTL to reduce DynamoDB queries
3. Implement TTL on audit log items
4. Use on-demand billing if validation patterns are unpredictable

### Missing Audit Context

1. Ensure API clients pass `user_id` in requests
2. Update frontend to include user context in API calls
3. Consider implementing middleware to automatically capture user context
