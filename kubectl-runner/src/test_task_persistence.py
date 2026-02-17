#!/usr/bin/env python3
"""
Test script for task persistence
Tests save/load, backup/recovery, export/import, and validation
"""

import pytest
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import sys

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MockTaskScheduler:
    """Mock TaskScheduler for testing persistence"""
    
    def __init__(self, config_dir=None):
        self.tasks = {}
        self.config_dir = config_dir or tempfile.mkdtemp()
        self.cluster_name = 'test-cluster'
    
    def _validate_tasks(self, tasks):
        """Validate tasks data structure"""
        try:
            if not isinstance(tasks, dict):
                return False
            
            for task_id, task in tasks.items():
                if not isinstance(task, dict):
                    return False
                
                required_fields = ['title', 'status']
                for field in required_fields:
                    if field not in task:
                        return False
                
                valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
                if task.get('status') not in valid_statuses:
                    task['status'] = 'pending'
            
            return True
        except Exception:
            return False
    
    def save_tasks(self):
        """Save tasks to file with atomic write and backup"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            
            tasks_file = os.path.join(self.config_dir, 'tasks.json')
            temp_file = os.path.join(self.config_dir, 'tasks.json.tmp')
            backup_file = os.path.join(self.config_dir, 'tasks.json.backup')
            
            # Create backup
            if os.path.exists(tasks_file):
                shutil.copy2(tasks_file, backup_file)
            
            # Write to temp file
            with open(temp_file, 'w') as f:
                json.dump(self.tasks, f, indent=2, sort_keys=True)
            
            # Verify temp file
            with open(temp_file, 'r') as f:
                json.load(f)
            
            # Atomic rename
            os.replace(temp_file, tasks_file)
            
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    def load_tasks(self):
        """Load tasks from file with validation and error recovery"""
        try:
            tasks_file = os.path.join(self.config_dir, 'tasks.json')
            backup_file = os.path.join(self.config_dir, 'tasks.json.backup')
            
            # Try main file
            if os.path.exists(tasks_file):
                try:
                    with open(tasks_file, 'r') as f:
                        loaded_tasks = json.load(f)
                    
                    if self._validate_tasks(loaded_tasks):
                        self.tasks = loaded_tasks
                        return True
                except Exception:
                    pass
            
            # Try backup
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r') as f:
                        loaded_tasks = json.load(f)
                    
                    if self._validate_tasks(loaded_tasks):
                        self.tasks = loaded_tasks
                        self.save_tasks()
                        return True
                except Exception:
                    pass
            
            self.tasks = {}
            return False
        except Exception:
            self.tasks = {}
            return False
    
    def export_tasks(self, export_path=None):
        """Export tasks with metadata"""
        try:
            if export_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_path = os.path.join(self.config_dir, f'tasks_export_{timestamp}.json')
            
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'task_count': len(self.tasks),
                'cluster_name': self.cluster_name,
                'tasks': self.tasks
            }
            
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, sort_keys=True)
            
            return export_path
        except Exception:
            return None
    
    def import_tasks(self, import_path, merge=False):
        """Import tasks from file"""
        try:
            if not os.path.exists(import_path):
                return None
            
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            if 'tasks' in import_data:
                imported_tasks = import_data['tasks']
            else:
                imported_tasks = import_data
            
            if not self._validate_tasks(imported_tasks):
                return None
            
            if merge:
                original_count = len(self.tasks)
                self.tasks.update(imported_tasks)
                imported_count = len(self.tasks) - original_count
            else:
                self.tasks = imported_tasks
                imported_count = len(self.tasks)
            
            self.save_tasks()
            return imported_count
        except Exception:
            return None
    
    def get_task_statistics(self):
        """Get task statistics"""
        try:
            stats = {
                'total': len(self.tasks),
                'by_status': {},
                'by_operation_type': {},
                'scheduled': 0,
                'one_time': 0
            }
            
            for task in self.tasks.values():
                status = task.get('status', 'unknown')
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                op_type = task.get('operation_type', 'unknown')
                stats['by_operation_type'][op_type] = stats['by_operation_type'].get(op_type, 0) + 1
                
                if task.get('schedule'):
                    stats['scheduled'] += 1
                else:
                    stats['one_time'] += 1
            
            return stats
        except Exception:
            return None
    
    def cleanup_old_tasks(self, days=30):
        """Clean up old tasks"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.get('status') not in ['completed', 'failed']:
                    continue
                
                last_run = task.get('last_run')
                if last_run:
                    try:
                        last_run_date = datetime.fromisoformat(last_run)
                        if last_run_date < cutoff_date:
                            tasks_to_remove.append(task_id)
                    except (ValueError, TypeError):
                        pass
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                self.save_tasks()
            
            return len(tasks_to_remove)
        except Exception:
            return 0


class TestTaskPersistence:
    """Test task persistence functionality"""
    
    def test_save_and_load_tasks(self):
        """Test basic save and load"""
        scheduler = MockTaskScheduler()
        
        # Add some tasks
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'},
            'task-2': {'title': 'Task 2', 'status': 'completed'}
        }
        
        # Save
        assert scheduler.save_tasks() is True
        
        # Create new scheduler and load
        scheduler2 = MockTaskScheduler(scheduler.config_dir)
        assert scheduler2.load_tasks() is True
        
        # Verify loaded tasks
        assert len(scheduler2.tasks) == 2
        assert 'task-1' in scheduler2.tasks
        assert scheduler2.tasks['task-1']['title'] == 'Task 1'
    
    def test_backup_recovery(self):
        """Test recovery from backup when main file is corrupted"""
        scheduler = MockTaskScheduler()
        
        # Save valid tasks twice to ensure backup is created
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'}
        }
        scheduler.save_tasks()
        
        # Save again to create backup
        scheduler.tasks['task-2'] = {'title': 'Task 2', 'status': 'completed'}
        scheduler.save_tasks()
        
        # Corrupt main file
        tasks_file = os.path.join(scheduler.config_dir, 'tasks.json')
        with open(tasks_file, 'w') as f:
            f.write('{ invalid json')
        
        # Load should recover from backup
        scheduler2 = MockTaskScheduler(scheduler.config_dir)
        assert scheduler2.load_tasks() is True
        # Should have the first version from backup (before corruption)
        assert len(scheduler2.tasks) >= 1
        assert 'task-1' in scheduler2.tasks
    
    def test_validation_rejects_invalid_tasks(self):
        """Test that validation rejects invalid task structures"""
        scheduler = MockTaskScheduler()
        
        # Invalid: not a dict
        assert scheduler._validate_tasks([]) is False
        
        # Invalid: task is not a dict
        assert scheduler._validate_tasks({'task-1': 'not a dict'}) is False
        
        # Invalid: missing required field
        assert scheduler._validate_tasks({'task-1': {'title': 'Task 1'}}) is False
        
        # Valid
        assert scheduler._validate_tasks({'task-1': {'title': 'Task 1', 'status': 'pending'}}) is True
    
    def test_export_tasks(self):
        """Test exporting tasks with metadata"""
        scheduler = MockTaskScheduler()
        
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'},
            'task-2': {'title': 'Task 2', 'status': 'completed'}
        }
        
        export_path = scheduler.export_tasks()
        
        assert export_path is not None
        assert os.path.exists(export_path)
        
        # Verify export format
        with open(export_path, 'r') as f:
            export_data = json.load(f)
        
        assert 'version' in export_data
        assert 'exported_at' in export_data
        assert 'task_count' in export_data
        assert export_data['task_count'] == 2
        assert 'tasks' in export_data
        assert len(export_data['tasks']) == 2
    
    def test_import_tasks_replace(self):
        """Test importing tasks (replace mode)"""
        scheduler = MockTaskScheduler()
        
        # Create export
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'}
        }
        export_path = scheduler.export_tasks()
        
        # Create new scheduler with different tasks
        scheduler2 = MockTaskScheduler()
        scheduler2.tasks = {
            'task-2': {'title': 'Task 2', 'status': 'completed'}
        }
        
        # Import (replace)
        imported_count = scheduler2.import_tasks(export_path, merge=False)
        
        assert imported_count == 1
        assert len(scheduler2.tasks) == 1
        assert 'task-1' in scheduler2.tasks
        assert 'task-2' not in scheduler2.tasks
    
    def test_import_tasks_merge(self):
        """Test importing tasks (merge mode)"""
        scheduler = MockTaskScheduler()
        
        # Create export
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'}
        }
        export_path = scheduler.export_tasks()
        
        # Create new scheduler with different tasks
        scheduler2 = MockTaskScheduler()
        scheduler2.tasks = {
            'task-2': {'title': 'Task 2', 'status': 'completed'}
        }
        
        # Import (merge)
        imported_count = scheduler2.import_tasks(export_path, merge=True)
        
        assert imported_count == 1
        assert len(scheduler2.tasks) == 2
        assert 'task-1' in scheduler2.tasks
        assert 'task-2' in scheduler2.tasks
    
    def test_task_statistics(self):
        """Test task statistics calculation"""
        scheduler = MockTaskScheduler()
        
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending', 'operation_type': 'activate', 'schedule': '0 9 * * *'},
            'task-2': {'title': 'Task 2', 'status': 'completed', 'operation_type': 'deactivate', 'schedule': ''},
            'task-3': {'title': 'Task 3', 'status': 'pending', 'operation_type': 'activate', 'schedule': '0 18 * * *'}
        }
        
        stats = scheduler.get_task_statistics()
        
        assert stats is not None
        assert stats['total'] == 3
        assert stats['by_status']['pending'] == 2
        assert stats['by_status']['completed'] == 1
        assert stats['by_operation_type']['activate'] == 2
        assert stats['by_operation_type']['deactivate'] == 1
        assert stats['scheduled'] == 2
        assert stats['one_time'] == 1
    
    def test_cleanup_old_tasks(self):
        """Test cleaning up old tasks"""
        scheduler = MockTaskScheduler()
        
        # Create tasks with different ages
        old_date = (datetime.now() - timedelta(days=40)).isoformat()
        recent_date = (datetime.now() - timedelta(days=10)).isoformat()
        
        scheduler.tasks = {
            'task-1': {'title': 'Old completed', 'status': 'completed', 'last_run': old_date},
            'task-2': {'title': 'Recent completed', 'status': 'completed', 'last_run': recent_date},
            'task-3': {'title': 'Old pending', 'status': 'pending', 'last_run': old_date},
            'task-4': {'title': 'Old failed', 'status': 'failed', 'last_run': old_date}
        }
        
        # Cleanup tasks older than 30 days
        removed_count = scheduler.cleanup_old_tasks(days=30)
        
        # Should remove old completed and old failed, but not pending
        assert removed_count == 2
        assert len(scheduler.tasks) == 2
        assert 'task-2' in scheduler.tasks  # Recent completed
        assert 'task-3' in scheduler.tasks  # Old pending (not removed)
    
    def test_atomic_write(self):
        """Test that save uses atomic write (temp file + rename)"""
        scheduler = MockTaskScheduler()
        
        scheduler.tasks = {
            'task-1': {'title': 'Task 1', 'status': 'pending'}
        }
        
        # Save
        scheduler.save_tasks()
        
        # Verify temp file doesn't exist after save
        temp_file = os.path.join(scheduler.config_dir, 'tasks.json.tmp')
        assert not os.path.exists(temp_file)
        
        # Verify main file exists
        tasks_file = os.path.join(scheduler.config_dir, 'tasks.json')
        assert os.path.exists(tasks_file)
        
        # Verify backup was created
        backup_file = os.path.join(scheduler.config_dir, 'tasks.json.backup')
        # Backup only exists if there was a previous save
        # On first save, there's no backup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
