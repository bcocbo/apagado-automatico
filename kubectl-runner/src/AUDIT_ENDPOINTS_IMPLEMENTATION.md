# Audit Endpoints Implementation

## Overview

This document describes the implementation of audit endpoints for querying activities by user and cluster. These endpoints provide comprehensive audit capabilities for the namespace scheduler system.

## New Endpoints

### 1. User Audit Endpoint

**Endpoint**: `GET /api/audit/user/<requested_by>`

**Description**: Query all activities requested by a specific user.

**Parameters**:
- `start_date` (optional): ISO format date (YYYY-MM-DDTHH:MM:SS)
- `end_date` (optional): ISO format date (YYYY-MM-DDTHH:MM:SS)
- `limit` (optional): Number of results (1-1000, default 100)

**Response Structure**:
```json
{
  "summary": {
    "total_activities": 25,
    "user": "john.doe@company.com",
    "date_range": {
      "start": "2024-01-01T00:00:00",
      "end": "2024-01-31T23:59:59"
    },
    "limit_applied": 100,
    "operation_counts": {
      "manual_activation": 15,
      "manual_deactivation": 8,
      "task_created": 2
    }
  },
  "activities": [
    {
      "namespace_name": "my-app-dev",
      "timestamp_start": 1640995200,
      "operation_type": "manual_activation",
      "cost_center": "CC-001",
      "cluster_name": "production-cluster",
      "requested_by": "john.doe@company.com",
      "status": "completed"
    }
  ]
}
```

### 2. Cluster Audit Endpoint

**Endpoint**: `GET /api/audit/cluster/<cluster_name>`

**Description**: Query all activities on a specific cluster.

**Parameters**:
- `start_date` (optional): ISO format date (YYYY-MM-DDTHH:MM:SS)
- `end_date` (optional): ISO format date (YYYY-MM-DDTHH:MM:SS)
- `limit` (optional): Number of results (1-1000, default 100)

**Response Structure**:
```json
{
  "summary": {
    "total_activities": 150,
    "cluster": "production-cluster",
    "date_range": {
      "start": "2024-01-01T00:00:00",
      "end": "2024-01-31T23:59:59"
    },
    "limit_applied": 100,
    "operation_counts": {
      "manual_activation": 75,
      "manual_deactivation": 60,
      "task_created": 15
    },
    "user_counts": {
      "john.doe@company.com": 45,
      "jane.smith@company.com": 30,
      "admin@company.com": 75
    },
    "cost_center_counts": {
      "CC-001": 80,
      "CC-002": 45,
      "CC-003": 25
    }
  },
  "activities": [...]
}
```

### 3. Audit Summary Endpoint

**Endpoint**: `GET /api/audit/summary`

**Description**: Get general audit information and guidance.

**Parameters**:
- `start_date` (optional): ISO format date
- `end_date` (optional): ISO format date

**Response Structure**:
```json
{
  "date_range": {
    "start": "2024-01-01T00:00:00",
    "end": "2024-01-31T23:59:59"
  },
  "message": "Use specific endpoints (/api/audit/user/<user> or /api/audit/cluster/<cluster>) for detailed audit queries"
}
```

## Usage Examples

### Query User Activities
```bash
# Get all activities for a user
curl "http://localhost:8080/api/audit/user/john.doe@company.com"

# Get activities for a user in date range
curl "http://localhost:8080/api/audit/user/john.doe@company.com?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59"

# Get limited number of activities
curl "http://localhost:8080/api/audit/user/john.doe@company.com?limit=50"
```

### Query Cluster Activities
```bash
# Get all activities for a cluster
curl "http://localhost:8080/api/audit/cluster/production-cluster"

# Get activities for a cluster in date range
curl "http://localhost:8080/api/audit/cluster/production-cluster?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59"

# Get limited number of activities
curl "http://localhost:8080/api/audit/cluster/production-cluster?limit=200"
```

## Implementation Details

### DynamoDB Methods

#### `get_activities_by_user(requested_by, start_date=None, end_date=None, limit=100)`
- Uses `requested-by-timestamp-index` GSI
- Sorts by timestamp descending (newest first)
- Supports date range filtering
- Configurable result limit

#### `get_activities_by_cluster(cluster_name, start_date=None, end_date=None, limit=100)`
- Uses `cluster-timestamp-index` GSI
- Sorts by timestamp descending (newest first)
- Supports date range filtering
- Configurable result limit

### DynamoDB Indexes

#### requested-by-timestamp-index
- **Hash Key**: `requested_by` (String)
- **Range Key**: `timestamp_start` (Number)
- **Projection**: ALL
- **Purpose**: Enable efficient queries by user

#### cluster-timestamp-index
- **Hash Key**: `cluster_name` (String)
- **Range Key**: `timestamp_start` (Number)
- **Projection**: ALL
- **Purpose**: Enable efficient queries by cluster

### Parameter Validation

#### Date Validation
- Accepts ISO format: `YYYY-MM-DDTHH:MM:SS`
- Returns 400 error for invalid formats
- Validates that start_date <= end_date

#### Limit Validation
- Minimum: 1
- Maximum: 1000
- Default: 100
- Automatically adjusts out-of-range values

### Error Handling

#### 400 Bad Request
- Invalid date format
- Invalid date range (start > end)

#### 500 Internal Server Error
- DynamoDB query failures
- Unexpected exceptions

### Response Features

#### Summary Statistics
- Total activity count
- Date range applied
- Limit applied
- Operation type breakdown
- User activity breakdown (cluster endpoint)
- Cost center breakdown (cluster endpoint)

#### Activity Sorting
- Results sorted by timestamp descending
- Most recent activities first
- Consistent ordering across queries

## Security Considerations

### Input Validation
- All parameters validated before processing
- SQL injection prevention through parameterized queries
- Date format validation prevents malformed inputs

### Rate Limiting
- Consider implementing rate limiting for audit endpoints
- Large queries can impact DynamoDB performance
- Monitor query costs and adjust limits as needed

### Access Control
- Consider adding authentication/authorization
- Audit endpoints expose sensitive operational data
- Implement role-based access if needed

## Performance Considerations

### DynamoDB Optimization
- Uses GSI for efficient queries
- Avoids expensive scan operations
- Limits result sets to prevent large responses

### Query Patterns
- Queries sorted by timestamp for optimal performance
- Date range filtering reduces data transfer
- Configurable limits prevent resource exhaustion

### Monitoring
- Monitor DynamoDB consumed capacity
- Track query latency and error rates
- Set up alerts for unusual activity patterns

## Testing

### Test Coverage
- Parameter validation testing
- Date range testing
- Limit validation testing
- Error handling testing
- Response structure validation

### Test Files
- `test_audit_endpoints.py`: Comprehensive endpoint testing
- `verify_audit_endpoints.py`: Implementation verification

## Future Enhancements

### Potential Improvements
- Add pagination for large result sets
- Implement caching for frequently accessed data
- Add export functionality (CSV, JSON)
- Implement real-time audit streaming
- Add advanced filtering options

### Additional Endpoints
- `/api/audit/cost-center/<cost_center>`: Query by cost center
- `/api/audit/operation/<operation_type>`: Query by operation type
- `/api/audit/namespace/<namespace>`: Query by namespace
- `/api/audit/export`: Export audit data

## Compliance

### Audit Trail
- All queries logged for audit purposes
- User identification tracked
- Query parameters recorded
- Response metadata captured

### Data Retention
- Consider implementing TTL for old audit records
- Balance compliance requirements with storage costs
- Implement archival strategy for historical data