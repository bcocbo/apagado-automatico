# Task Persistence Implementation

## Overview

This document describes the implementation of robust task persistence with backup/recovery, validation, export/import, and automatic saving capabilities.

## Features

### 1. Atomic Write Operations

Tasks are saved using atomic write operations to prevent data corruption:

```python
# Write to temporary file
with open(temp_file, 'w') as f:
    json.dump(self.tasks, f, indent=2, sort_keys=True)

# Verify the file is valid JSON
with open(temp_file, 'r') as f:
    json.load(f)

# Atomic rename (replaces old file)
os.replace(temp_file, tasks_file)
```

**Benefits:**
- Prevents partial writes
- Ensures file is always in valid state
- No data loss if write fails mid-operation

### 2. Automatic Backup

Before each save, the current file is backed up:

```python
if os.path.exists(tasks_file):
    shutil.copy2(tasks_file, backup_file)
```

**Backup Strategy:**
- Backup created before every save
- Single backup file (most recent)
- Used for recovery if main file is corrupted

### 3. Validation and Recovery

Tasks are validated when loaded, with automatic recovery from backup:

```python
# Try to load from main file
if os.path.exists(tasks_file):
    loaded_tasks = json.load(f)
    if self._validate_tasks(loaded_tasks):
        self.tasks = loaded_tasks
        return

# If main file fails, try backup
if os.path.exists(backup_file):
    loaded_tasks = json.load(f)
    if self._validate_tasks(loaded_tasks):
        self.tasks = loaded_tasks
        self.save_tasks()  # Restore main file
        return
```

**Validation Checks:**
- Tasks must be a dictionary
- Each task must be a dictionary
- Required fields: `title`, `status`
- Status must be valid: `pending`, `running`, `completed`, `failed`, `cancelled`

### 4. Export/Import

Tasks can be exported with metadata and imported later:

**Export Format:**
```json
{
  "version": "1.0",
  "exported_at": "2024-01-15T10:30:00",
  "task_count": 10,
  "cluster_name": "production-cluster",
  "tasks": {
    "task-123": {
      "title": "Activate namespace",
      "status": "pending",
      ...
    }
  }
}
```

**Export Method:**
```python
# Export with automatic timestamp
export_path = scheduler.export_tasks()

# Export to specific path
export_path = scheduler.export_tasks('/app/config/my_export.json')
```

**Import Modes:**
- **Replace**: Replace all existing tasks with imported tasks
- **Merge**: Add imported tasks to existing tasks (keeps both)

**Import Method:**
```python
# Replace all tasks
imported_count = scheduler.import_tasks('/app/config/tasks_export.json', merge=False)

# Merge with existing tasks
imported_count = scheduler.import_tasks('/app/config/tasks_export.json', merge=True)
```

**Backward Compatibility:**
- Supports both new format (with metadata) and old format (direct tasks dict)
- Automatically detects format and handles appropriately

### 5. Automatic Saving

Tasks are automatically saved at regular intervals using a background daemon thread:

```python
def start_auto_save(self, interval_seconds=300):
    """Start automatic periodic saving of tasks"""
    def auto_save_loop():
        while True:
            try:
                time.sleep(interval_seconds)
                self.save_tasks()
                logger.debug(f"Auto-saved tasks (interval: {interval_seconds}s)")
            except Exception as e:
                logger.error(f"Error in auto-save: {e}")
    
    auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
    auto_save_thread.start()
    logger.info(f"Started auto-save thread (interval: {interval_seconds}s)")
```

**Features:**
- Runs in background daemon thread (doesn't block shutdown)
- Configurable save interval
- Error handling to prevent thread crashes
- Detailed logging for monitoring

**Configuration:**
- `AUTO_SAVE_ENABLED`: Enable/disable auto-save (default: true)
- `AUTO_SAVE_INTERVAL_SECONDS`: Save interval (default: 300 seconds / 5 minutes)

### 6. Task Statistics

Get comprehensive statistics about tasks:

```python
stats = scheduler.get_task_statistics()
```

**Returns:**
```python
{
    'total': 10,
    'by_status': {
        'pending': 5,
        'completed': 3,
        'failed': 2
    },
    'by_operation_type': {
        'activate': 6,
        'deactivate': 4
    },
    'by_cost_center': {
        'engineering': 7,
        'operations': 3
    },
    'scheduled': 8,      # Tasks with cron schedule
    'one_time': 2,       # Tasks without schedule
    'total_runs': 45,
    'total_successes': 40,
    'total_failures': 5
}
```

**Use Cases:**
- Dashboard metrics
- Monitoring and alerting
- Capacity planning
- Cost center reporting

### 7. Cleanup Old Tasks

Remove old completed/failed tasks to prevent file bloat:

```python
# Remove tasks older than 30 days
removed_count = scheduler.cleanup_old_tasks(days=30)

# Remove tasks older than 7 days
removed_count = scheduler.cleanup_old_tasks(days=7)
```

**Cleanup Rules:**
- Only removes `completed` or `failed` tasks
- Based on `last_run` timestamp
- Configurable age threshold (default: 30 days)
- Preserves `pending` and `running` tasks
- Automatically saves after cleanup

**Error Handling:**
- Handles invalid date formats gracefully
- Logs warnings for tasks with invalid dates
- Returns 0 on error (doesn't crash)

## File Structure

```
/app/config/
├── tasks.json           # Main task file
├── tasks.json.backup    # Backup of previous version
├── tasks.json.tmp       # Temporary file during save (deleted after)
└── tasks_export_*.json  # Export files (timestamped)
```

## API Endpoints

### Get Task Statistics

```
GET /api/tasks/stats
```

Response:
```json
{
  "max_workers": 5,
  "running_tasks": 2,
  "total": 10,
  "by_status": {
    "pending": 5,
    "completed": 3
  },
  "scheduled": 8,
  "one_time": 2
}
```

### Export Tasks

```
POST /api/tasks/export
Content-Type: application/json

{
  "path": "/app/config/my_export.json"  // Optional
}
```

Response:
```json
{
  "success": true,
  "message": "Tasks exported successfully",
  "path": "/app/config/tasks_export_20240115_103000.json",
  "task_count": 10
}
```

### Import Tasks

```
POST /api/tasks/import
Content-Type: application/json

{
  "path": "/app/config/tasks_export_20240115_103000.json",
  "merge": false  // true to merge, false to replace
}
```

Response:
```json
{
  "success": true,
  "message": "Successfully imported 10 tasks",
  "imported_count": 10,
  "total_tasks": 10,
  "merge": false
}
```

### Cleanup Old Tasks

```
POST /api/tasks/cleanup
Content-Type: application/json

{
  "days": 30  // Optional, default: 30
}
```

Response:
```json
{
  "success": true,
  "message": "Cleaned up 5 old tasks",
  "removed_count": 5,
  "remaining_tasks": 5
}
```

## Configuration

### Environment Variables

```bash
# Auto-save configuration
AUTO_SAVE_ENABLED=true
AUTO_SAVE_INTERVAL_SECONDS=300

# File paths (defaults shown)
# Tasks are saved to /app/config/tasks.json
```

### Initialization

Auto-save is started automatically when TaskScheduler initializes:

```python
scheduler = TaskScheduler()
# Auto-save starts automatically if enabled
```

## Error Handling

### Save Errors

```python
try:
    scheduler.save_tasks()
except Exception as e:
    logger.error(f"Error saving tasks: {e}")
    # Temporary file is cleaned up automatically
```

### Load Errors

```python
# Automatic fallback chain:
# 1. Try main file
# 2. Try backup file
# 3. Start with empty tasks
```

### Validation Errors

```python
if not self._validate_tasks(loaded_tasks):
    logger.error("Tasks failed validation")
    # Try backup or start empty
```

## Best Practices

### 1. Regular Exports

Create periodic exports for disaster recovery:

```bash
# Export tasks weekly
curl -X POST http://localhost:8080/api/tasks/export
```

### 2. Cleanup Old Tasks

Run cleanup periodically to prevent file bloat:

```bash
# Cleanup tasks older than 30 days
curl -X POST http://localhost:8080/api/tasks/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

### 3. Monitor Auto-Save

Check logs to ensure auto-save is working:

```
INFO - Started auto-save thread (interval: 300s)
DEBUG - Auto-saved tasks (interval: 300s)
```

### 4. Backup Strategy

- Auto-save handles recent backups
- Create manual exports for long-term retention
- Store exports outside the container for disaster recovery

### 5. Validation

Always validate imported tasks:

```python
# Import will automatically validate
# Returns None if validation fails
imported_count = scheduler.import_tasks(path)
if imported_count is None:
    print("Import failed validation")
```

## Recovery Scenarios

### Scenario 1: Corrupted Main File

```
1. Load attempts to read tasks.json
2. JSON parsing fails
3. Automatically loads from tasks.json.backup
4. Restores main file from backup
5. System continues normally
```

### Scenario 2: Both Files Corrupted

```
1. Load attempts main file - fails
2. Load attempts backup file - fails
3. Starts with empty task list
4. Logs warning
5. Import from export file if available
```

### Scenario 3: Accidental Task Deletion

```
1. Stop the service
2. Restore from backup:
   cp /app/config/tasks.json.backup /app/config/tasks.json
3. Or import from export:
   curl -X POST http://localhost:8080/api/tasks/import \
     -d '{"path": "/app/config/tasks_export_*.json"}'
4. Restart service
```

## Testing

The implementation includes comprehensive tests:

1. **Save and Load**: Basic persistence
2. **Backup Recovery**: Recovery from corrupted main file
3. **Validation**: Rejection of invalid task structures
4. **Export**: Export with metadata
5. **Import Replace**: Replace all tasks
6. **Import Merge**: Merge with existing tasks
7. **Statistics**: Task statistics calculation
8. **Cleanup**: Removal of old tasks
9. **Atomic Write**: Verification of atomic operations

All tests pass successfully.

## Performance Considerations

### File Size

- JSON format is human-readable but larger
- Consider cleanup for large task counts
- Typical task: ~500 bytes
- 1000 tasks: ~500 KB
- 10000 tasks: ~5 MB

### Save Performance

- Atomic write adds minimal overhead
- Backup copy is fast (same filesystem)
- Auto-save runs in background thread
- No impact on task execution

### Load Performance

- JSON parsing is fast for typical sizes
- Validation adds minimal overhead
- Backup fallback only on errors
- Loads once at startup

## Monitoring

### Metrics to Track

- Save success/failure rate
- Load success/failure rate
- Backup recovery events
- Export/import operations
- Cleanup operations
- Auto-save intervals

### Log Messages

```
INFO - Loaded 10 tasks from /app/config/tasks.json
INFO - Loaded 10 tasks from backup /app/config/tasks.json.backup
WARNING - Could not load tasks from file or backup, starting with empty task list
DEBUG - Saved 10 tasks to /app/config/tasks.json
INFO - Exported 10 tasks to /app/config/tasks_export_20240115_103000.json
INFO - Merged 5 new tasks (total: 15)
INFO - Cleaned up 3 old tasks (older than 30 days)
DEBUG - Auto-saved tasks (interval: 300s)
```

## Future Enhancements

Potential improvements:

1. **Compression**: Gzip compression for large files
2. **Encryption**: Encrypt sensitive task data
3. **Versioning**: Keep multiple backup versions
4. **Cloud Storage**: S3/GCS backup integration
5. **Database Backend**: PostgreSQL/MySQL option
6. **Incremental Saves**: Only save changed tasks
7. **Replication**: Multi-node synchronization
8. **Audit Trail**: Track all changes to tasks
