# Structured Logging Configuration

## Overview

The Namespace Scheduler backend implements structured logging with support for both JSON and text formats. This provides enhanced observability, request tracing, and integration with log aggregation systems.

## Features

### Structured JSON Logging
- Machine-readable JSON format for easy parsing by log aggregation tools
- Consistent log structure across all application components
- Automatic inclusion of contextual metadata

### Request Tracing
- Unique request ID for each API call
- Request/response logging with duration tracking
- Correlation of logs across the request lifecycle

### Log Rotation
- Automatic log file rotation to prevent disk space issues
- Configurable file size limits (default: 10 MB per file)
- Retention of up to 5 backup files

### Contextual Logging
- Automatic capture of request metadata (user, namespace, cost center, cluster)
- Operation-specific context fields
- Exception tracking with full stack traces

## Configuration

### Environment Variables

The logging system is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | `json` | Log format: `json` or `text` |
| `LOG_FILE` | `/app/logs/app.log` | Path to log file |

### Log Levels

- **DEBUG**: Detailed diagnostic information (cache hits/misses, detailed flow)
- **INFO**: General informational messages (requests, operations, completions)
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for failures that don't stop the application
- **CRITICAL**: Critical errors that may cause application failure

### Log Formats

#### JSON Format (Default)
Structured JSON output suitable for log aggregation systems like CloudWatch, ELK, or Splunk:

```json
{
  "timestamp": "2026-02-16T10:30:45.123456Z",
  "level": "INFO",
  "logger": "__main__",
  "message": "Request completed: POST /api/namespaces/activate - 200",
  "module": "app",
  "function": "after_request",
  "line": 145,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "operation": "POST /api/namespaces/activate",
  "status_code": 200,
  "duration_ms": 234,
  "namespace": "dev-team-1",
  "cost_center": "CC-12345",
  "user_id": "john.doe@example.com"
}
```

#### Text Format
Human-readable format for local development:

```
2026-02-16 10:30:45,123 - __main__ - INFO - Request completed: POST /api/namespaces/activate - 200
```

## Log Fields

### Standard Fields
Present in all log entries:

- `timestamp`: ISO 8601 timestamp in UTC
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger`: Logger name (typically `__main__`)
- `message`: Human-readable log message
- `module`: Python module name
- `function`: Function name where log was generated
- `line`: Line number in source code

### Contextual Fields
Added automatically when available:

- `request_id`: Unique identifier for the request (also returned in `X-Request-ID` response header)
- `operation`: HTTP method and path (e.g., "POST /api/namespaces/activate")
- `status_code`: HTTP response status code
- `duration_ms`: Request duration in milliseconds
- `namespace`: Kubernetes namespace being operated on
- `cost_center`: Cost center associated with the operation
- `user_id`: User identifier (from request or system)
- `requested_by`: Primary user tracking field
- `cluster_name`: EKS cluster name
- `task_id`: Scheduled task identifier
- `remote_addr`: Client IP address
- `user_agent`: Client user agent string

### Exception Fields
Added when logging exceptions:

- `exception`: Full exception stack trace

## Usage Examples

### Production Configuration (JSON Logging)

```yaml
env:
- name: LOG_LEVEL
  value: "INFO"
- name: LOG_FORMAT
  value: "json"
- name: LOG_FILE
  value: "/app/logs/app.log"
```

### Development Configuration (Text Logging)

```yaml
env:
- name: LOG_LEVEL
  value: "DEBUG"
- name: LOG_FORMAT
  value: "text"
- name: LOG_FILE
  value: "/app/logs/app.log"
```

### Troubleshooting Configuration

```yaml
env:
- name: LOG_LEVEL
  value: "DEBUG"
- name: LOG_FORMAT
  value: "json"
- name: LOG_FILE
  value: "/app/logs/app.log"
```

## Log File Management

### Rotation Policy
- Maximum file size: 10 MB
- Backup files retained: 5
- Naming pattern: `app.log`, `app.log.1`, `app.log.2`, etc.
- Oldest files are automatically deleted when limit is reached

### Log Directory
The application automatically creates the log directory if it doesn't exist. Ensure the container has write permissions to the log directory.

### Volume Mounting
For persistent logs, mount a volume to `/app/logs`:

```yaml
volumeMounts:
- name: logs
  mountPath: /app/logs
volumes:
- name: logs
  emptyDir: {}
```

For production, consider using a persistent volume or shipping logs to a centralized logging system.

## Request Tracing

### Request ID Generation
- Automatically generated for each request using UUID4
- Can be provided by client via `X-Request-ID` header
- Returned in response via `X-Request-ID` header
- Included in all logs related to that request

### Tracing a Request
1. Client sends request (optionally with `X-Request-ID` header)
2. Server logs incoming request with request_id
3. All operations log with the same request_id
4. Server logs completion with request_id and duration
5. Response includes `X-Request-ID` header

Example log sequence for a single request:

```json
{"timestamp": "2026-02-16T10:30:45.000Z", "level": "INFO", "message": "Incoming request: POST /api/namespaces/activate", "request_id": "abc-123", ...}
{"timestamp": "2026-02-16T10:30:45.100Z", "level": "INFO", "message": "Validating cost center permissions", "request_id": "abc-123", ...}
{"timestamp": "2026-02-16T10:30:45.200Z", "level": "INFO", "message": "Scaling namespace resources", "request_id": "abc-123", ...}
{"timestamp": "2026-02-16T10:30:45.234Z", "level": "INFO", "message": "Request completed: POST /api/namespaces/activate - 200", "request_id": "abc-123", "duration_ms": 234}
```

## Integration with Log Aggregation Systems

### CloudWatch Logs
The JSON format is compatible with CloudWatch Logs Insights. Example queries:

```
# Find all errors in the last hour
fields @timestamp, message, exception
| filter level = "ERROR"
| sort @timestamp desc

# Track request performance
fields @timestamp, operation, duration_ms
| filter operation like /POST/
| stats avg(duration_ms), max(duration_ms), count() by operation

# Audit user activity
fields @timestamp, requested_by, operation, namespace, cost_center
| filter requested_by != "system"
| sort @timestamp desc
```

### ELK Stack (Elasticsearch, Logstash, Kibana)
The JSON format can be directly ingested by Logstash or Filebeat. Configure Filebeat to read from `/app/logs/app.log`.

### Splunk
Use the Splunk Universal Forwarder to ship logs. The JSON format will be automatically parsed.

## Best Practices

1. **Use JSON format in production** for better integration with log aggregation tools
2. **Use INFO level in production** to balance detail with log volume
3. **Use DEBUG level sparingly** as it generates significant log volume
4. **Monitor log file sizes** and adjust rotation settings if needed
5. **Ship logs to centralized system** rather than relying on local files
6. **Include request IDs in client logs** for end-to-end tracing
7. **Set up alerts** on ERROR and CRITICAL level logs
8. **Regularly review logs** for performance issues and errors

## Troubleshooting

### Logs not appearing
- Check that log directory exists and is writable
- Verify LOG_LEVEL is not set too high (e.g., ERROR when you want INFO)
- Check container logs: `kubectl logs <pod-name>`

### Log files growing too large
- Reduce LOG_LEVEL (e.g., from DEBUG to INFO)
- Adjust rotation settings in code if needed
- Ensure logs are being shipped to external system

### Missing contextual fields
- Verify the operation is using the contextual logging helper
- Check that request middleware is properly configured
- Ensure Flask request context is available

### Performance impact
- JSON formatting has minimal overhead
- File I/O is buffered for efficiency
- Consider async logging for very high-volume scenarios
- Use INFO level instead of DEBUG in production

## Related Documentation

- [Deployment Configuration](deployment-configuration.md) - Environment variable configuration
- [Audit Logging Implementation](../kubectl-runner/src/AUDIT_LOGGING_IMPLEMENTATION.md) - Audit-specific logging
- [DynamoDB Table Design](dynamodb-table-design.md) - Audit log storage
