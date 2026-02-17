# Background Thread Execution Implementation

## Overview

This document describes the implementation of background thread execution for scheduled tasks using Python's `ThreadPoolExecutor` with timeout, retry, and robust error handling capabilities.

## Architecture

### Thread Pool Configuration

The system uses a `ThreadPoolExecutor` to manage concurrent task execution:

```python
self.max_workers = int(os.getenv('MAX_TASK_WORKERS', '5'))
self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix='task-worker')
```

**Configuration Environment Variables:**
- `MAX_TASK_WORKERS`: Maximum number of concurrent task workers (default: 5)
- `TASK_TIMEOUT_SECONDS`: Timeout for individual task execution (default: 300 seconds / 5 minutes)
- `TASK_MAX_RETRIES`: Maximum number of retry attempts for failed tasks (default: 3)
- `TASK_RETRY_DELAY_SECONDS`: Delay between retry attempts (default: 10 seconds)

### Task Execution Flow

```
1. run_task(task_id)
   ├─> Check if task exists and is not already running
   ├─> Create thread lock for task
   ├─> Update task status to 'running'
   ├─> Submit to ThreadPoolExecutor
   └─> Add completion callback

2. _execute_task_with_retry(task_id)
   ├─> Attempt 1
   │   ├─> _execute_task_with_timeout(task_id)
   │   │   └─> _execute_task(task_id)
   │   └─> If failed, wait and retry
   ├─> Attempt 2 (if needed)
   └─> Attempt 3 (if needed)

3. _task_completion_callback(task_id, future)
   └─> Clean up running_tasks tracking
```

## Key Features

### 1. Thread Pool Management

**Benefits:**
- Limits concurrent task execution to prevent resource exhaustion
- Reuses threads efficiently
- Provides better control over system resources

**Implementation:**
```python
future = self.executor.submit(self._execute_task_with_retry, task_id)
self.running_tasks[task_id] = future
self.task_futures[task_id] = future
```

### 2. Task Timeouts

Each task has a configurable timeout to prevent hanging operations:

```python
execution_future = self.executor.submit(self._execute_task, task_id)
result = execution_future.result(timeout=self.task_timeout)
```

**Timeout Handling:**
- If a task exceeds the timeout, it's cancelled
- The task is marked as failed with a timeout error
- Retry logic can attempt the task again

### 3. Automatic Retries

Failed tasks are automatically retried with exponential backoff:

```python
for attempt in range(self.max_retries):
    try:
        result = self._execute_task_with_timeout(task_id)
        if result.get('success', False):
            return result
        else:
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
    except Exception as e:
        if attempt < self.max_retries - 1:
            time.sleep(self.retry_delay)
```

**Retry Strategy:**
- Configurable number of retry attempts
- Configurable delay between retries
- Detailed logging of each attempt
- Preserves last error for debugging

### 4. Thread-Safe Operations

All task state modifications use thread locks to prevent race conditions:

```python
if task_id not in self.task_locks:
    self.task_locks[task_id] = threading.Lock()

with self.task_locks[task_id]:
    task['status'] = 'running'
    task['last_run'] = datetime.now().isoformat()
    task['run_count'] += 1
```

### 5. Detailed Logging

Comprehensive logging at every stage:

```python
logger.info(f"Starting execution of task {task_id}: {task.get('title', 'Untitled')}")
logger.debug(f"Task details: operation_type={task.get('operation_type')}, "
            f"namespace={task.get('namespace')}, cost_center={task.get('cost_center')}")
```

**Logged Information:**
- Task start and completion
- Execution time
- Success/failure status
- Error messages and stack traces
- Retry attempts

### 6. Task History

All task executions are recorded with detailed information:

```python
history_entry = {
    'task_id': task_id,
    'title': task['title'],
    'command': task.get('command', '...'),
    'timestamp': datetime.now().isoformat(),
    'execution_time_seconds': round(execution_time, 2),
    'success': result.get('success', False),
    'output': result.get('stdout', '')[:1000],
    'error': result.get('stderr', '')[:1000],
    'operation_type': task.get('operation_type'),
    'namespace': task.get('namespace'),
    'cost_center': task.get('cost_center')
}
```

### 7. Task Cancellation

Running tasks can be cancelled:

```python
def cancel_task(self, task_id):
    if task_id not in self.running_tasks:
        return False
    
    future = self.running_tasks[task_id]
    cancelled = future.cancel()
    
    if cancelled:
        with self.task_locks.get(task_id, threading.Lock()):
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'cancelled'
    
    return cancelled
```

### 8. Periodic Cleanup

Completed task futures are cleaned up periodically to prevent memory leaks:

```python
def cleanup_completed_tasks(self):
    completed_task_ids = []
    
    for task_id, future in list(self.running_tasks.items()):
        if future.done():
            completed_task_ids.append(task_id)
    
    for task_id in completed_task_ids:
        del self.running_tasks[task_id]
        if task_id in self.task_futures:
            del self.task_futures[task_id]
    
    return len(completed_task_ids)
```

**Cleanup Schedule:**
- Runs every 5 minutes in the scheduler loop
- Removes completed task futures from tracking
- Logs cleanup statistics

## API Endpoints

### Health Check with Thread Pool Status

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "tasks_count": 10,
  "running_tasks": 2,
  "thread_pool": {
    "max_workers": 5,
    "active_threads": 2,
    "task_timeout": 300,
    "max_retries": 3
  }
}
```

### Get Running Tasks

```
GET /api/tasks/running
```

Response:
```json
[
  {
    "task_id": "task-123",
    "title": "Activate namespace",
    "status": "running",
    "last_run": "2024-01-15T10:25:00",
    "run_count": 1,
    "is_done": false,
    "is_cancelled": false
  }
]
```

### Cancel Task

```
POST /api/tasks/{task_id}/cancel
```

Response:
```json
{
  "message": "Task cancelled successfully"
}
```

### Get Task Statistics

```
GET /api/tasks/stats
```

Response:
```json
{
  "max_workers": 5,
  "running_tasks": 2,
  "task_timeout": 300,
  "max_retries": 3,
  "retry_delay": 10,
  "total_tasks": 10,
  "pending_tasks": 5,
  "completed_tasks": 3,
  "failed_tasks": 0
}
```

## Error Handling

### Timeout Errors

```python
except FuturesTimeoutError:
    logger.error(f"Task {task_id} timed out after {self.task_timeout} seconds")
    execution_future.cancel()
    return {
        'success': False,
        'error': f'Task timed out after {self.task_timeout} seconds'
    }
```

### Execution Errors

```python
except Exception as e:
    logger.error(f"Unexpected error executing task {task_id}: {e}")
    logger.error(traceback.format_exc())
    
    task['status'] = 'failed'
    task['error_count'] += 1
```

### Retry Exhaustion

```python
return {
    'success': False,
    'error': f"Failed after {self.max_retries} attempts. Last error: {last_error}"
}
```

## Performance Considerations

### Thread Pool Sizing

The default of 5 workers is suitable for most use cases. Consider adjusting based on:

- **CPU-bound tasks**: Set to number of CPU cores
- **I/O-bound tasks**: Can be higher (10-20)
- **Memory constraints**: Lower if tasks use significant memory

### Timeout Configuration

Default 5-minute timeout works for most kubectl operations. Adjust if:

- Tasks consistently timeout: Increase timeout
- Tasks hang indefinitely: Decrease timeout
- Quick operations: Decrease for faster failure detection

### Retry Strategy

Default 3 retries with 10-second delay. Consider:

- **Transient failures**: Keep retries enabled
- **Permanent failures**: Reduce retries to fail faster
- **Rate limiting**: Increase delay between retries

## Testing

The implementation includes comprehensive tests:

1. **Basic Execution**: Single task execution
2. **Concurrent Execution**: Multiple tasks running simultaneously
3. **Already Running**: Prevents duplicate execution
4. **Retry Logic**: Automatic retries on failure
5. **Timeout Handling**: Tasks that exceed timeout
6. **Cancellation**: Cancelling running tasks
7. **Cleanup**: Removing completed task futures
8. **Thread Pool Limits**: Respecting max_workers

All tests pass successfully, ensuring robust operation.

## Monitoring and Debugging

### Logs to Monitor

```
INFO - Task {task_id} ({title}) submitted to thread pool
INFO - Executing task {task_id} (attempt {attempt}/{max_retries})
INFO - Task {task_id} completed successfully in {time}s
ERROR - Task {task_id} failed after {time}s: {error}
INFO - Periodic cleanup: removed {count} completed task futures
```

### Metrics to Track

- Number of running tasks
- Task execution time
- Success/failure rates
- Retry frequency
- Timeout occurrences
- Thread pool utilization

## Best Practices

1. **Set appropriate timeouts** based on expected task duration
2. **Monitor thread pool utilization** to adjust max_workers
3. **Review failed tasks** to identify systemic issues
4. **Use retries judiciously** to avoid masking problems
5. **Clean up completed tasks** to prevent memory leaks
6. **Log detailed information** for debugging
7. **Test under load** to ensure stability

## Future Enhancements

Potential improvements:

1. **Priority queues** for task scheduling
2. **Dynamic thread pool sizing** based on load
3. **Task dependencies** and execution ordering
4. **Distributed task execution** across multiple workers
5. **Advanced retry strategies** (exponential backoff, jitter)
6. **Task result caching** for idempotent operations
7. **Metrics export** to Prometheus/CloudWatch
