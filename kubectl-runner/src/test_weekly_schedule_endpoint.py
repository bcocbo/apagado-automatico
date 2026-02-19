#!/usr/bin/env python3
"""
Test script for the weekly schedule endpoint
Tests the new /api/weekly-schedule/{week_start_date} endpoint functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app and scheduler
from app import app, scheduler

class TestWeeklyScheduleEndpoint:
    """Test the weekly schedule endpoint functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Clear any existing tasks and cache
        scheduler.tasks.clear()
        scheduler.weekly_cache.clear()
    
    def test_get_weekly_scheduled_tasks_empty(self):
        """Test getting weekly tasks when no tasks exist"""
        week_start = datetime(2024, 1, 15)  # Monday
        
        weekly_tasks = scheduler.get_weekly_scheduled_tasks(week_start)
        
        assert isinstance(weekly_tasks, list)
        assert len(weekly_tasks) == 0
    
    def test_get_weekly_scheduled_tasks_with_tasks(self):
        """Test getting weekly tasks with some scheduled tasks"""
        # Add a test task
        task_data = {
            'id': 'test-task-1',
            'title': 'Test Weekly Task',
            'schedule': '0 9 * * 1-5',  # 9 AM weekdays
            'namespace': 'test-namespace',
            'cost_center': 'test-center',
            'operation_type': 'activate'
        }
        
        # Mock the cost center validation to return True
        with patch.object(scheduler.dynamodb_manager, 'validate_cost_center_permissions', return_value=True):
            scheduler.add_task(task_data)
        
        week_start = datetime(2024, 1, 15)  # Monday
        weekly_tasks = scheduler.get_weekly_scheduled_tasks(week_start)
        
        assert isinstance(weekly_tasks, list)
        assert len(weekly_tasks) > 0
        
        # Check that tasks have the expected structure
        for task in weekly_tasks:
            assert 'task_id' in task
            assert 'namespace' in task
            assert 'cost_center' in task
            assert 'scheduled_time' in task
            assert 'day_of_week' in task
            assert 'hour' in task
            assert 'minute' in task
    
    def test_process_weekly_tasks_to_time_slots(self):
        """Test processing weekly tasks into time slots"""
        # Create sample weekly tasks
        weekly_tasks = [
            {
                'task_id': 'test-1',
                'title': 'Test Task 1',
                'namespace': 'test-ns',
                'cost_center': 'test-cc',
                'operation_type': 'activate',
                'scheduled_time': '2024-01-15T09:00:00',  # Monday 9 AM
                'day_of_week': 0,
                'hour': 9,
                'minute': 0
            }
        ]
        
        week_start = datetime(2024, 1, 15)
        time_slots = scheduler.process_weekly_tasks_to_time_slots(weekly_tasks, week_start)
        
        assert isinstance(time_slots, dict)
        assert 'monday' in time_slots
        assert '09' in time_slots['monday']
        assert len(time_slots['monday']['09']) == 1
        
        task_slot = time_slots['monday']['09'][0]
        assert task_slot['task_id'] == 'test-1'
        assert task_slot['namespace_name'] == 'test-ns'
        assert task_slot['cost_center'] == 'test-cc'
    
    def test_format_weekly_schedule_response(self):
        """Test formatting weekly schedule response"""
        week_start = datetime(2024, 1, 15)
        time_slots = {
            'monday': {
                '09': [
                    {
                        'task_id': 'test-1',
                        'namespace_name': 'test-ns',
                        'cost_center': 'test-cc',
                        'operation_type': 'activate'
                    }
                ]
            },
            'tuesday': {},
            'wednesday': {},
            'thursday': {},
            'friday': {},
            'saturday': {},
            'sunday': {}
        }
        
        # Fill empty hours for all days
        for day in time_slots:
            for hour in range(24):
                hour_key = f"{hour:02d}"
                if hour_key not in time_slots[day]:
                    time_slots[day][hour_key] = []
        
        response = scheduler.format_weekly_schedule_response(week_start, time_slots)
        
        assert response['success'] is True
        assert 'data' in response
        assert response['data']['week_start_date'] == '2024-01-15'
        assert response['data']['week_end_date'] == '2024-01-21'
        assert 'time_slots' in response['data']
        assert 'metadata' in response['data']
        
        metadata = response['data']['metadata']
        assert 'total_tasks' in metadata
        assert 'active_namespaces' in metadata
        assert 'cost_centers' in metadata
    
    def test_weekly_cache_functionality(self):
        """Test weekly cache get/put functionality"""
        week_start = datetime(2024, 1, 15)
        test_data = {'test': 'data'}
        
        # Test cache miss
        cached_data = scheduler._get_weekly_cache(week_start)
        assert cached_data is None
        
        # Test cache put
        scheduler._put_weekly_cache(week_start, test_data)
        
        # Test cache hit
        cached_data = scheduler._get_weekly_cache(week_start)
        assert cached_data == test_data
        
        # Test cache stats
        stats = scheduler.get_weekly_cache_stats()
        assert stats['enabled'] is True
        assert stats['cached_entries'] == 1
    
    @patch.object(scheduler.dynamodb_manager, 'validate_cost_center_permissions', return_value=True)
    def test_weekly_schedule_api_endpoint(self, mock_validate):
        """Test the API endpoint for weekly schedule"""
        # Add a test task
        task_data = {
            'id': 'api-test-task',
            'title': 'API Test Task',
            'schedule': '0 10 * * 1',  # 10 AM Mondays
            'namespace': 'api-test-ns',
            'cost_center': 'api-test-cc',
            'operation_type': 'activate'
        }
        
        scheduler.add_task(task_data)
        
        # Test the API endpoint
        response = self.app.get('/api/weekly-schedule/2024-01-15')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'success' in data
        assert 'data' in data
        
        if data['success']:
            assert 'week_start_date' in data['data']
            assert 'time_slots' in data['data']
            assert 'metadata' in data['data']
    
    def test_weekly_schedule_api_invalid_date(self):
        """Test API endpoint with invalid date format"""
        response = self.app.get('/api/weekly-schedule/invalid-date')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_weekly_cache_stats_endpoint(self):
        """Test the weekly cache stats API endpoint"""
        response = self.app.get('/api/weekly-schedule/cache/stats')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'enabled' in data
        assert 'cached_entries' in data
    
    def test_weekly_cache_invalidate_endpoint(self):
        """Test the weekly cache invalidate API endpoint"""
        # Test invalidating all cache
        response = self.app.post('/api/weekly-schedule/cache/invalidate',
                               json={})
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
        
        # Test invalidating specific week
        response = self.app.post('/api/weekly-schedule/cache/invalidate',
                               json={'week_start_date': '2024-01-15'})
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data

if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])