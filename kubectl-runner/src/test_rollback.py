#!/usr/bin/env python3
"""
Tests for rollback functionality in namespace scaling
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call

# Mock logging before importing app
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

with patch('logging.FileHandler'):
    from app import TaskScheduler


class TestRollback:
    """Test suite for rollback functionality"""
    
    @pytest.fixture
    def scheduler(self):
        """Create a TaskScheduler instance with mocked dependencies"""
        with patch('app.DynamoDBManager'):
            scheduler = TaskScheduler()
            scheduler.dynamodb_manager = Mock()
            return scheduler
    
    def test_rollback_on_partial_failure(self, scheduler):
        """Test that rollback occurs when some resources fail to scale"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}},
                    {'metadata': {'name': 'app2'}, 'spec': {'replicas': 2}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        rollback_success = {'success': True, 'stdout': 'scaled'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_success,       # scale app1 (success)
                scale_failure,       # scale app2 (failure - triggers rollback)
                rollback_success,    # rollback app1
                get_statefulsets     # get statefulsets (not reached due to rollback)
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is True
            assert result['total_scaled'] == 1
            assert result['total_failed'] == 1
            assert len(result['rollback_results']) == 1
            assert result['rollback_results'][0]['status'] == 'success'
            assert result['rollback_results'][0]['restored_replicas'] == 3
    
    def test_no_rollback_when_disabled(self, scheduler):
        """Test that rollback doesn't occur when disabled"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}},
                    {'metadata': {'name': 'app2'}, 'spec': {'replicas': 2}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_success,       # scale app1 (success)
                scale_failure,       # scale app2 (failure - no rollback)
                get_statefulsets     # get statefulsets
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=False)
            
            assert result['success'] is False
            assert result['rollback_performed'] is False
            assert result['total_scaled'] == 1
            assert result['total_failed'] == 1
            assert 'rollback_results' not in result
    
    def test_rollback_on_json_parse_error(self, scheduler):
        """Test that rollback occurs on JSON parse error"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}}
                ]
            })
        }
        
        get_statefulsets_invalid = {
            'success': True,
            'stdout': 'invalid json'
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        rollback_success = {'success': True, 'stdout': 'scaled'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,           # get deployments
                scale_success,             # scale app1 (success)
                get_statefulsets_invalid,  # get statefulsets (invalid JSON - triggers rollback)
                rollback_success           # rollback app1
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is True
            assert len(result['rollback_results']) == 1
            assert 'Failed to parse JSON' in str(result['errors'])
    
    def test_rollback_failure_handling(self, scheduler):
        """Test handling when rollback itself fails"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'db1'}, 'spec': {'replicas': 2}}
                ]
            })
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        rollback_failure = {'success': False, 'stderr': 'Rollback failed'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_success,       # scale app1 (success)
                get_statefulsets,    # get statefulsets
                scale_failure,       # scale db1 (failure - triggers rollback)
                rollback_failure     # rollback app1 (fails)
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is True
            assert result['rollback_failed_count'] == 1
            assert result['rollback_success_count'] == 0
            assert result['rollback_results'][0]['status'] == 'failed'
    
    def test_no_rollback_when_no_successes(self, scheduler):
        """Test that rollback doesn't occur if no resources were successfully scaled"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_failure,       # scale app1 (failure - no rollback since no successes)
                get_statefulsets     # get statefulsets
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is False
            assert result['total_scaled'] == 0
            assert result['total_failed'] == 1
    
    def test_rollback_skips_already_at_target(self, scheduler):
        """Test that rollback skips resources that were already at target"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 0}},  # Already at target
                    {'metadata': {'name': 'app2'}, 'spec': {'replicas': 2}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'db1'}, 'spec': {'replicas': 1}}
                ]
            })
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        rollback_success = {'success': True, 'stdout': 'scaled'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                # app1 skipped (already at 0)
                scale_success,       # scale app2 (success)
                get_statefulsets,    # get statefulsets
                scale_failure,       # scale db1 (failure - triggers rollback)
                rollback_success     # rollback app2 only (app1 was skipped)
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is True
            # Only app2 should be rolled back (app1 was skipped)
            assert len(result['rollback_results']) == 1
            assert result['rollback_results'][0]['name'] == 'app2'
    
    def test_successful_scaling_no_rollback(self, scheduler):
        """Test that no rollback occurs when all scaling succeeds"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_success,       # scale app1 (success)
                get_statefulsets     # get statefulsets
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is True
            assert result['rollback_performed'] is False
            assert result['total_scaled'] == 1
            assert result['total_failed'] == 0
    
    def test_rollback_multiple_resources(self, scheduler):
        """Test rollback of multiple successfully scaled resources"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {'metadata': {'name': 'app1'}, 'spec': {'replicas': 3}},
                    {'metadata': {'name': 'app2'}, 'spec': {'replicas': 2}},
                    {'metadata': {'name': 'app3'}, 'spec': {'replicas': 1}}
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        scale_success = {'success': True, 'stdout': 'scaled'}
        scale_failure = {'success': False, 'stderr': 'Error scaling'}
        rollback_success = {'success': True, 'stdout': 'scaled'}
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,     # get deployments
                scale_success,       # scale app1 (success)
                scale_success,       # scale app2 (success)
                scale_failure,       # scale app3 (failure - triggers rollback)
                rollback_success,    # rollback app1
                rollback_success,    # rollback app2
                get_statefulsets     # not reached
            ]
            
            result = scheduler.scale_namespace_resources('test-ns', target_replicas=0, enable_rollback=True)
            
            assert result['success'] is False
            assert result['rollback_performed'] is True
            assert result['total_scaled'] == 2
            assert result['total_failed'] == 1
            assert len(result['rollback_results']) == 2
            assert result['rollback_success_count'] == 2
            assert result['rollback_failed_count'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
