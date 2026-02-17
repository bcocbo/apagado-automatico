#!/usr/bin/env python3
"""
Tests for resource scaling functionality
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Mock logging before importing app
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Create mock for logging to avoid file handler issues
with patch('logging.FileHandler'):
    from app import TaskScheduler


class TestResourceScaling:
    """Test suite for scale_namespace_resources function"""
    
    @pytest.fixture
    def scheduler(self):
        """Create a TaskScheduler instance with mocked dependencies"""
        with patch('app.DynamoDBManager'):
            scheduler = TaskScheduler()
            scheduler.dynamodb_manager = Mock()
            return scheduler
    
    def test_scale_down_deployments_to_zero(self, scheduler):
        """Test scaling down deployments to 0 replicas"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 3}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': True,
            'stdout': 'deployment.apps/app-deployment scaled'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments
                scale_response,  # scale deployment
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is True
            assert result['total_scaled'] == 1
            assert result['total_failed'] == 0
            assert len(result['scaled_resources']) == 1
            assert result['scaled_resources'][0]['from_replicas'] == 3
            assert result['scaled_resources'][0]['to_replicas'] == 0
    
    def test_scale_up_deployments(self, scheduler):
        """Test scaling up deployments from 0 to specific replicas"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 0}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': True,
            'stdout': 'deployment.apps/app-deployment scaled'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments
                scale_response,  # scale deployment
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=3)
            
            assert result['success'] is True
            assert result['total_scaled'] == 1
            assert result['scaled_resources'][0]['from_replicas'] == 0
            assert result['scaled_resources'][0]['to_replicas'] == 3
    
    def test_scale_statefulsets(self, scheduler):
        """Test scaling statefulsets"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'db-statefulset'},
                        'spec': {'replicas': 2}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': True,
            'stdout': 'statefulset.apps/db-statefulset scaled'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,  # get deployments (empty)
                get_statefulsets,  # get statefulsets
                scale_response  # scale statefulset
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is True
            assert result['total_scaled'] == 1
            assert result['scaled_resources'][0]['type'] == 'statefulsets'
            assert result['scaled_resources'][0]['name'] == 'db-statefulset'
    
    def test_skip_already_scaled_resources(self, scheduler):
        """Test that resources already at target replicas are skipped"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 0}
                    }
                ]
            })
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is True
            assert result['total_scaled'] == 1
            assert result['scaled_resources'][0]['status'] == 'skipped'
            assert result['scaled_resources'][0]['reason'] == 'already at target'
    
    def test_handle_scale_failure(self, scheduler):
        """Test handling of scale command failures"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 3}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': False,
            'stderr': 'Error: deployment not found'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments
                scale_response,  # scale deployment (fails)
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is False
            assert result['total_failed'] == 1
            assert len(result['failed_resources']) == 1
            assert 'Error: deployment not found' in result['failed_resources'][0]['error']
    
    def test_handle_empty_namespace(self, scheduler):
        """Test handling of namespace with no scalable resources"""
        # Mock kubectl responses - empty results
        empty_response = {
            'success': True,
            'stdout': json.dumps({'items': []})
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                empty_response,  # get deployments (empty)
                empty_response   # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is True
            assert result['total_scaled'] == 0
            assert result['total_failed'] == 0
            assert 'No scalable resources found' in result['message']
    
    def test_handle_multiple_resources(self, scheduler):
        """Test scaling multiple resources in a namespace"""
        # Mock kubectl responses
        get_deployments = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 3}
                    },
                    {
                        'metadata': {'name': 'worker-deployment'},
                        'spec': {'replicas': 2}
                    }
                ]
            })
        }
        
        get_statefulsets = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'db-statefulset'},
                        'spec': {'replicas': 1}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': True,
            'stdout': 'scaled'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_deployments,  # get deployments
                scale_response,   # scale app-deployment
                scale_response,   # scale worker-deployment
                get_statefulsets, # get statefulsets
                scale_response    # scale db-statefulset
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            assert result['success'] is True
            assert result['total_scaled'] == 3
            assert result['total_failed'] == 0
    
    def test_restore_replicas_from_zero(self, scheduler):
        """Test restoring replicas from 0 (should restore to 1)"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': json.dumps({
                'items': [
                    {
                        'metadata': {'name': 'app-deployment'},
                        'spec': {'replicas': 0}
                    }
                ]
            })
        }
        
        scale_response = {
            'success': True,
            'stdout': 'deployment.apps/app-deployment scaled'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments
                scale_response,  # scale deployment
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=None)
            
            assert result['success'] is True
            assert result['total_scaled'] == 1
            assert result['scaled_resources'][0]['from_replicas'] == 0
            assert result['scaled_resources'][0]['to_replicas'] == 1
    
    def test_handle_json_decode_error(self, scheduler):
        """Test handling of invalid JSON response"""
        # Mock kubectl responses
        get_response = {
            'success': True,
            'stdout': 'invalid json'
        }
        
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.side_effect = [
                get_response,  # get deployments (invalid JSON)
                {'success': True, 'stdout': json.dumps({'items': []})}  # get statefulsets (empty)
            ]
            
            result = scheduler.scale_namespace_resources('test-namespace', target_replicas=0)
            
            # Should handle error gracefully
            assert 'errors' in result
            assert any('Failed to parse JSON' in error for error in result['errors'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
