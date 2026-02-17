# Detailed Logging Implementation

## Overview

This document describes the implementation of a comprehensive, structured logging system with request tracking, contextual information, log rotation, and dynamic configuration.

## Features

### 1. Structured JSON Logging

Logs can be output in JSON format for easy parsing and analysis:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "__main__",
  "message": "Task completed successfully",
  "module": "app",
  "function": "_execute_task",
  "line": 2350,
  "request_id": "abc123-def456",
  "task_id": "task-789",
  "namespace": "production",
  "cost_center": "engineering",
  "duration_ms": 1234,
  "operation": "activate"
}
```

### 2. Log Formats

Two formats are supported:

**JSON Format** (default for production):
```bash
LOG_FORMAT=json
```

**Text Format** (human-readable for development):
```bash
LOG_FORMAT=text
```

Output:
```
2024-01-15 10:30:00,123 - __main__ - INFO - Task completed successfully
```

### 3. Log Levels

Configurable log levels via environment variable:

```bash
LOG_LEVEL=DEBUG    # Most verbose
LOG_LEVEL=INFO     # Default
LOG_LEVEL=WARNING
LOG_LEVEL=ERROR
LOG_LEVEL=CRITICAL # Least verbose
```

### 4. Log Rotation

Automatic log file rotation to prevent disk space issues:

- **Max file size**: 10 MB
- **Backup count**: 5 files
- **Files**: `app.log`, `app.log.1`, `app.log.2`, ..., `app.log.5`

Configuration:
```python
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
```

### 5. Request Tracking

Every HTTP request gets a unique `request_id` for tracing:

**Request ID Sources:**
1. Client-provided: `X-Request-ID` header
2. Auto-generated: UUID if not provided

**Request Logging:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Incoming request: POST /api/tasks",
  "request_id": "abc123-def456",
  "operation": "POST /api/tasks",
  "remote_addr": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

**Response Logging:**
```json
{
  "timestamp": "2024-01-15T10:30:01Z",
  "level": "INFO",
  "message": "Request completed: POST /api/tasks - 201",
  "request_id": "abc123-def456",
  "operation": "POST /api/tasks",
  "status_code": 201,
  "duration_ms": 1234
}
```

### 6. Contextual Logging

Helper function for adding context to logs:

```python
log_with_context(
    'info',
    'Task completed successfully',
    task_id='task-123',
    namespace='production',
    cost_center='engineering',
    duration_ms=1234,
    operation='activate'
)
```

**Supported Context Fields:**
- `request_id`: Request identifier
- `task_id`: Task identifier
- `user_id`: User identifier
- `namespace`: Kubernetes namespace
- `cost_center`: Cost center
- `duration_ms`: Operation duration in milliseconds
- `operation`: Operation type

### 7. Exception Logging

Unhandled exceptions are automatically logged with full context:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "message": "Unhandled exception: Division by zero",
  "request_id": "abc123-def456",
  "operation": "POST /api/tasks",
  "exception": "Traceback (most recent call last):\n  File..."
}
```

## API Endpoints

### Get Execution Logs (with filtering)

```
GET /api/logs?limit=50&task_id=task-123&namespace=production&success=true
```

Query Parameters:
- `limit`: Number of logs to return (default: 50)
- `task_id`: Filter by task ID
- `namespace`: Filter by namespace
- `cost_center`: Filter by cost center
- `success`: Filter by success status (true/false)

Response:
```json
{
  "logs": [
    {
      "task_id": "task-123",
      "title": "Activate namespace",
      "timestamp": "2024-01-15T10:30:00",
      "success": true,
      "execution_time_seconds": 1.23,
      "namespace": "production",
      "cost_center": "engineering"
    }
  ],
  "total": 10,
  "limit": 50
}
```

### Get Log File Contents

```
GET /api/logs/file?lines=100
```

Query Parameters:
- `lines`: Number of lines to return (default: 100)

Response:
```json
{
  "lines": [
    "{\"timestamp\":\"2024-01-15T10:30:00Z\",\"level\":\"INFO\",...}",
    "{\"timestamp\":\"2024-01-15T10:30:01Z\",\"level\":\"INFO\",...}"
  ],
  "total_lines": 100,
  "file": "/app/logs/app.log"
}
```

### Get Current Log Level

```
GET /api/logs/level
```

Response:
```json
{
  "level": "INFO",
  "numeric_level": 20
}
```

### Set Log Level Dynamically

```
POST /api/logs/level
Content-Type: application/json

{
  "level": "DEBUG"
}
```

Response:
```json
{
  "message": "Log level set to DEBUG",
  "level": "DEBUG"
}
```

Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Configuration

### Environment Variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (json or text)
LOG_FORMAT=json

# Log file path
LOG_FILE=/app/logs/app.log
```

### Docker/Kubernetes Configuration

```yaml
env:
- name: LOG_LEVEL
  value: "INFO"
- name: LOG_FORMAT
  value: "json"
- name: LOG_FILE
  value: "/app/logs/app.log"

volumeMounts:
- name: logs
  mountPath: /app/logs

volumes:
- name: logs
  emptyDir: {}
```

## Log Levels Guide

### DEBUG
Use for detailed diagnostic information:
- Variable values
- Function entry/exit
- Detailed state information

```python
log_with_context('debug', f"Task state: {task}", task_id=task_id)
```

### INFO
Use for general informational messages:
- Task started/completed
- Configuration loaded
- Normal operations

```python
log_with_context('info', 'Task completed successfully', task_id=task_id)
```

### WARNING
Use for potentially harmful situations:
- Deprecated features used
- Recoverable errors
- Performance issues

```python
log_with_context('warning', 'Task took longer than expected', duration_ms=5000)
```

### ERROR
Use for error events that might still allow the application to continue:
- Task failures
- API errors
- Validation failures

```python
log_with_context('error', f'Task failed: {error}', task_id=task_id)
```

### CRITICAL
Use for very severe error events that might cause the application to abort:
- Database connection lost
- Critical resource unavailable
- System failure

```python
log_with_context('critical', 'Cannot connect to DynamoDB')
```

## Best Practices

### 1. Use Structured Logging

Always use `log_with_context()` for contextual information:

```python
# Good
log_with_context(
    'info',
    'Task completed',
    task_id=task_id,
    duration_ms=duration_ms
)

# Avoid
logger.info(f"Task {task_id} completed in {duration_ms}ms")
```

### 2. Include Request ID

Always include request_id for tracing:

```python
# Automatically included when using log_with_context()
log_with_context('info', 'Processing request')
```

### 3. Log Performance Metrics

Include duration for performance monitoring:

```python
start_time = time.time()
# ... operation ...
duration_ms = int((time.time() - start_time) * 1000)

log_with_context(
    'info',
    'Operation completed',
    operation='activate_namespace',
    duration_ms=duration_ms
)
```

### 4. Limit Log Size

Truncate large outputs to prevent log bloat:

```python
output = result.get('stdout', '')[:1000]  # Limit to 1000 chars
```

### 5. Use Appropriate Log Levels

- Don't log sensitive information (passwords, tokens)
- Use DEBUG for development, INFO for production
- Use ERROR for failures, not warnings

## Log Analysis

### Using jq for JSON Logs

Filter by level:
```bash
cat app.log | jq 'select(.level == "ERROR")'
```

Filter by task_id:
```bash
cat app.log | jq 'select(.task_id == "task-123")'
```

Calculate average duration:
```bash
cat app.log | jq -s 'map(select(.duration_ms)) | map(.duration_ms) | add/length'
```

### Using grep for Text Logs

```bash
# Find errors
grep "ERROR" app.log

# Find specific task
grep "task-123" app.log

# Find slow operations
grep "duration_ms.*[5-9][0-9][0-9][0-9]" app.log
```

## Integration with Log Aggregation

### Elasticsearch/Kibana

JSON logs can be directly ingested:

```json
{
  "@timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Task completed",
  "task_id": "task-123",
  "duration_ms": 1234
}
```

### CloudWatch Logs

Configure log group and stream:

```python
import watchtower

handler = watchtower.CloudWatchLogHandler(
    log_group='/aws/ecs/task-scheduler',
    stream_name='app'
)
logger.addHandler(handler)
```

### Datadog

Use Datadog agent to collect logs:

```yaml
logs:
  - type: file
    path: /app/logs/app.log
    service: task-scheduler
    source: python
```

## Monitoring and Alerting

### Metrics to Monitor

1. **Error Rate**: Count of ERROR/CRITICAL logs
2. **Response Time**: Average `duration_ms`
3. **Request Volume**: Count of requests per minute
4. **Task Success Rate**: Ratio of successful to failed tasks

### Alert Examples

**High Error Rate:**
```
Count of ERROR logs > 10 in 5 minutes
```

**Slow Operations:**
```
Average duration_ms > 5000 for any operation
```

**Failed Tasks:**
```
Task failure rate > 10% in 10 minutes
```

## Troubleshooting

### No Logs Appearing

1. Check log file permissions:
```bash
ls -la /app/logs/app.log
```

2. Check log level:
```bash
curl http://localhost:8080/api/logs/level
```

3. Check disk space:
```bash
df -h /app/logs
```

### Log File Too Large

1. Check rotation settings
2. Reduce log level (INFO instead of DEBUG)
3. Increase rotation size or backup count

### Missing Context in Logs

1. Ensure using `log_with_context()` instead of `logger.info()`
2. Check that context fields are being passed
3. Verify JSON format is enabled

## Performance Considerations

### Log Volume

- DEBUG level: ~1000 logs/minute
- INFO level: ~100 logs/minute
- WARNING+ level: ~10 logs/minute

### Disk Usage

- JSON format: ~500 bytes/log
- Text format: ~200 bytes/log
- With rotation (5 files × 10 MB): ~50 MB total

### Performance Impact

- Logging overhead: <1% CPU
- File I/O: Buffered, minimal impact
- JSON serialization: ~0.1ms per log

## Future Enhancements

Potential improvements:

1. **Async Logging**: Queue-based logging for high throughput
2. **Log Sampling**: Sample DEBUG logs in production
3. **Structured Metrics**: Export metrics to Prometheus
4. **Log Compression**: Gzip old log files
5. **Remote Logging**: Direct streaming to log aggregation service
6. **Log Correlation**: Trace requests across services
7. **Custom Fields**: User-defined context fields
8. **Log Redaction**: Automatic PII removal
