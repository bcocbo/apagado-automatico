# Task Creation Validation Implementation

## Overview
This document describes the implementation of cost center validation for scheduled task creation, completing task 2.1.3 from the namespace-scheduler specification.

## Changes Made

### 1. Backend Validation (app.py)

#### Modified `TaskScheduler.add_task()` method
- Added cost center validation before creating a task
- Validates that the cost center is authorized using `validate_cost_center_permissions()`
- Raises `ValueError` if the cost center is not authorized
- Location: Lines ~411-430 in `kubectl-runner/src/app.py`

```python
def add_task(self, task_data):
    """Add a new task"""
    task_id = task_data.get('id', str(uuid.uuid4()))
    cost_center = task_data.get('cost_center', 'default')
    
    # Validate cost center permissions before creating task
    if not self.dynamodb_manager.validate_cost_center_permissions(cost_center):
        raise ValueError(f"Cost center '{cost_center}' is not authorized")
    
    # Enhanced task structure for namespace scheduling
    self.tasks[task_id] = {
        'id': task_id,
        'title': task_data.get('title', ''),
        'command': task_data.get('command', ''),
        'schedule': task_data.get('schedule', ''),
        'namespace': task_data.get('namespace', 'default'),
        'cost_center': cost_center,
        'operation_type': task_data.get('operation_type', 'command'),
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        # ... additional fields
    }
```

#### Modified `/api/tasks` POST endpoint
- Added validation for required `cost_center` field
- Returns 400 error if cost_center is missing
- Returns 403 error if cost_center is not authorized
- Returns 201 on successful task creation

```python
@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        task_data = request.get_json()
        
        # Validate required fields
        if not task_data.get('cost_center'):
            return jsonify({'error': 'cost_center is required'}), 400
        
        task = scheduler.add_task(task_data)
        return jsonify(task), 201
    except ValueError as e:
        # Cost center validation error
        logger.warning(f"Task creation failed: {e}")
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': str(e)}), 400
```

### 2. Test Suite

#### Created `test_task_creation_validation.py`
Comprehensive test suite that validates:

1. **Test 1**: Task creation with authorized cost center (should succeed)
2. **Test 2**: Task creation with unauthorized cost center (should fail with 403)
3. **Test 3**: Task creation with non-existent cost center (should fail with 403)
4. **Test 4**: Task creation without cost center field (should fail with 400)
5. **Test 5**: Task creation with command operation type (should succeed)

#### Created `run_all_tests.sh`
Bash script to run all validation tests in sequence:
- Checks if API is running
- Runs cost center validation tests
- Runs namespace validation tests
- Runs task creation validation tests

## Validation Flow

```
User creates task
    ↓
POST /api/tasks
    ↓
Validate cost_center field exists → NO → Return 400 error
    ↓ YES
Check cost_center in DynamoDB permissions table
    ↓
Cost center authorized? → NO → Return 403 error
    ↓ YES
Create task and save to tasks.json
    ↓
Log task creation to DynamoDB
    ↓
Return 201 with task details
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "cost_center is required"
}
```

### 403 Forbidden
```json
{
  "error": "Cost center 'unauthorized-center' is not authorized"
}
```

### 201 Created
```json
{
  "id": "uuid",
  "title": "Task Title",
  "cost_center": "authorized-center",
  "namespace": "test-namespace",
  "operation_type": "activate",
  "status": "pending",
  "created_at": "2024-01-01T12:00:00",
  "next_run": "2024-01-02T09:00:00",
  ...
}
```

## Testing

### Prerequisites
- Backend API running at http://localhost:8080
- DynamoDB tables configured and accessible
- Python 3 with requests library installed

### Running Tests

```bash
# Run all tests
cd kubectl-runner/src
./run_all_tests.sh

# Run only task creation tests
python3 test_task_creation_validation.py
```

## Integration with Existing Features

This implementation integrates seamlessly with:

1. **Cost Center Permissions System**: Uses the same `validate_cost_center_permissions()` method used by namespace activation/deactivation
2. **DynamoDB Logging**: Task creation is logged to DynamoDB with operation_type='task_created'
3. **Task Scheduler**: Validated tasks are added to the scheduler and executed according to their cron schedule

## Compliance with Requirements

This implementation satisfies:
- **Requirement 2.1**: Validates cost center permissions before creating scheduled tasks
- **Requirement 4.2**: Validates permissions of the cost center
- **Requirement 5.2**: Registers task creation operations in DynamoDB

## Next Steps

The following related tasks remain:
- Task 2.1.5: Implement cache of permissions for better performance
- Task 2.1.6: Add logs of auditoría for validations
- Task 2.1.7: Implement capture of requesting user in all operations
- Task 2.1.8: Implement capture of cluster name in all operations
