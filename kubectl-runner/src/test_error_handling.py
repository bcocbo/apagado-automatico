#!/usr/bin/env python3
"""
Tests for robust error handling in namespace management
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Mock logging before importing app
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

with patch('logging.FileHandler'):
    from app import TaskScheduler


class TestErrorHandling:
    """Test suite for error handling in namespace management"""
    
    @pytest.fixture
    def scheduler(self):
        """Create a TaskScheduler instance with mocked dependencies"""
        with patch('app.DynamoDBManager'):
            scheduler = TaskScheduler()
            scheduler.dynamodb_manager = Mock()
            scheduler.cluster_name = 'test-cluster'
            return scheduler
    
    # Validation Tests
    
    def test_validate_activation_invalid_namespace(self, scheduler):
        """Test validation with invalid namespace parameter"""
        result = scheduler.validate_namespace_activation('cost-center', None)
        
        assert len(result) == 3
        is_valid, message, details = result
        assert is_valid is False
        assert 'Invalid namespace' in message
        assert details['error_type'] == 'validation_error'
    
    def test_validate_activation_invalid_cost_center(self, scheduler):
        """Test validation with invalid cost center parameter"""
        result = scheduler.validate_namespace_activation('', 'test-namespace')
        
        assert len(result) == 3
        is_valid, message, details = result
        assert is_valid is False
        assert 'Invalid cost center' in message
        assert details['error_type'] == 'validation_error'
    
    def test_validate_activation_namespace_not_found(self, scheduler):
        """Test validation when namespace doesn't exist"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {
                'success': False,
                'stderr': 'namespace not found'
            }
            
            result = scheduler.validate_namespace_activation('cost-center', 'nonexistent')
            
            is_valid, message, details = result
            assert is_valid is False
            assert 'does not exist' in message
            assert details['error_type'] == 'namespace_not_found'
    
    def test_validate_activation_permission_check_error(self, scheduler):
        """Test validation when permission check fails"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {'success': True, 'stdout': '{}'}
            
            scheduler.dynamodb_manager.validate_cost_center_permissions.side_effect = Exception('DynamoDB error')
            
            result = scheduler.validate_namespace_activation('cost-center', 'test-ns')
            
            is_valid, message, details = result
            assert is_valid is False
            assert 'Failed to validate permissions' in message
            assert details['error_type'] == 'permission_check_error'
    
    def test_validate_activation_count_error(self, scheduler):
        """Test validation when namespace count check fails"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {'success': True, 'stdout': '{}'}
            
            scheduler.dynamodb_manager.validate_cost_center_permissions.return_value = True
            
            with patch.object(scheduler, 'is_non_business_hours', return_value=True):
                with patch.object(scheduler, 'get_active_namespaces_count', side_effect=Exception('Count error')):
                    result = scheduler.validate_namespace_activation('cost-center', 'test-ns')
                    
                    is_valid, message, details = result
                    assert is_valid is False
                    assert 'Failed to check namespace limits' in message
                    assert details['error_type'] == 'count_error'
    
    # Activation Tests
    
    def test_activate_invalid_namespace(self, scheduler):
        """Test activation with invalid namespace"""
        result = scheduler.activate_namespace(None, 'cost-center')
        
        assert result['success'] is False
        assert 'Invalid namespace' in result['error']
        assert result['error_type'] == 'validation_error'
    
    def test_activate_invalid_cost_center(self, scheduler):
        """Test activation with invalid cost center"""
        result = scheduler.activate_namespace('test-ns', '')
        
        assert result['success'] is False
        assert 'Invalid cost center' in result['error']
        assert result['error_type'] == 'validation_error'
    
    def test_activate_validation_failed(self, scheduler):
        """Test activation when validation fails"""
        with patch.object(scheduler, 'validate_namespace_activation') as mock_validate:
            mock_validate.return_value = (False, 'Validation failed', {'error_type': 'test_error'})
            
            result = scheduler.activate_namespace('test-ns', 'cost-center')
            
            assert result['success'] is False
            assert 'Validation failed' in result['error']
            assert result['error_type'] == 'test_error'
    
    def test_activate_scaling_error(self, scheduler):
        """Test activation when scaling fails"""
        with patch.object(scheduler, 'validate_namespace_activation') as mock_validate:
            mock_validate.return_value = (True, 'Valid', {})
            
            with patch.object(scheduler, 'scale_namespace_resources', side_effect=Exception('Scaling error')):
                result = scheduler.activate_namespace('test-ns', 'cost-center')
                
                assert result['success'] is False
                assert 'Failed to scale namespace resources' in result['error']
                assert result['error_type'] == 'scaling_error'
    
    def test_activate_dynamodb_logging_failure(self, scheduler):
        """Test that activation succeeds even if DynamoDB logging fails"""
        with patch.object(scheduler, 'validate_namespace_activation') as mock_validate:
            mock_validate.return_value = (True, 'Valid', {})
            
            with patch.object(scheduler, 'scale_namespace_resources') as mock_scale:
                mock_scale.return_value = {
                    'success': True,
                    'scaled_resources': [],
                    'total_scaled': 0
                }
                
                scheduler.dynamodb_manager.log_namespace_activity.side_effect = Exception('DynamoDB error')
                
                with patch.object(scheduler, 'get_active_namespaces_count', return_value=1):
                    result = scheduler.activate_namespace('test-ns', 'cost-center')
                    
                    # Should succeed despite logging failure
                    assert result['success'] is True
                    assert 'activated successfully' in result['message']
    
    def test_activate_count_failure_non_critical(self, scheduler):
        """Test that activation succeeds even if count update fails"""
        with patch.object(scheduler, 'validate_namespace_activation') as mock_validate:
            mock_validate.return_value = (True, 'Valid', {})
            
            with patch.object(scheduler, 'scale_namespace_resources') as mock_scale:
                mock_scale.return_value = {
                    'success': True,
                    'scaled_resources': [],
                    'total_scaled': 0
                }
                
                with patch.object(scheduler, 'get_active_namespaces_count', side_effect=Exception('Count error')):
                    result = scheduler.activate_namespace('test-ns', 'cost-center')
                    
                    # Should succeed despite count failure
                    assert result['success'] is True
                    assert 'active_namespaces_count' not in result
    
    def test_activate_successful_with_details(self, scheduler):
        """Test successful activation returns detailed information"""
        with patch.object(scheduler, 'validate_namespace_activation') as mock_validate:
            mock_validate.return_value = (True, 'Valid', {})
            
            with patch.object(scheduler, 'scale_namespace_resources') as mock_scale:
                mock_scale.return_value = {
                    'success': True,
                    'scaled_resources': [
                        {'type': 'deployment', 'name': 'app', 'from_replicas': 0, 'to_replicas': 1}
                    ],
                    'total_scaled': 1
                }
                
                with patch.object(scheduler, 'get_active_namespaces_count', return_value=2):
                    result = scheduler.activate_namespace('test-ns', 'cost-center', user_id='test-user')
                    
                    assert result['success'] is True
                    assert result['namespace'] == 'test-ns'
                    assert result['cost_center'] == 'cost-center'
                    assert 'scaled_resources' in result
                    assert 'operation_duration' in result
                    assert result['active_namespaces_count'] == 2
    
    # Deactivation Tests
    
    def test_deactivate_invalid_namespace(self, scheduler):
        """Test deactivation with invalid namespace"""
        result = scheduler.deactivate_namespace(None, 'cost-center')
        
        assert result['success'] is False
        assert 'Invalid namespace' in result['error']
        assert result['error_type'] == 'validation_error'
    
    def test_deactivate_namespace_not_found(self, scheduler):
        """Test deactivation when namespace doesn't exist"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {
                'success': False,
                'stderr': 'namespace not found'
            }
            
            result = scheduler.deactivate_namespace('nonexistent', 'cost-center')
            
            assert result['success'] is False
            assert 'does not exist' in result['error']
            assert result['error_type'] == 'namespace_not_found'
    
    def test_deactivate_unauthorized(self, scheduler):
        """Test deactivation with unauthorized cost center"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {'success': True, 'stdout': '{}'}
            
            scheduler.dynamodb_manager.validate_cost_center_permissions.return_value = False
            
            result = scheduler.deactivate_namespace('test-ns', 'unauthorized-cc')
            
            assert result['success'] is False
            assert 'not authorized' in result['error']
            assert result['error_type'] == 'authorization_error'
    
    def test_deactivate_scaling_error(self, scheduler):
        """Test deactivation when scaling fails"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {'success': True, 'stdout': '{}'}
            
            scheduler.dynamodb_manager.validate_cost_center_permissions.return_value = True
            
            with patch.object(scheduler, 'scale_namespace_resources', side_effect=Exception('Scaling error')):
                result = scheduler.deactivate_namespace('test-ns', 'cost-center')
                
                assert result['success'] is False
                assert 'Failed to scale namespace resources' in result['error']
                assert result['error_type'] == 'scaling_error'
    
    def test_deactivate_successful_with_details(self, scheduler):
        """Test successful deactivation returns detailed information"""
        with patch.object(scheduler, 'execute_kubectl_command') as mock_kubectl:
            mock_kubectl.return_value = {'success': True, 'stdout': '{}'}
            
            scheduler.dynamodb_manager.validate_cost_center_permissions.return_value = True
            
            with patch.object(scheduler, 'scale_namespace_resources') as mock_scale:
                mock_scale.return_value = {
                    'success': True,
                    'scaled_resources': [
                        {'type': 'deployment', 'name': 'app', 'from_replicas': 1, 'to_replicas': 0}
                    ],
                    'total_scaled': 1
                }
                
                with patch.object(scheduler, 'get_active_namespaces_count', return_value=1):
                    result = scheduler.deactivate_namespace('test-ns', 'cost-center', requested_by='admin')
                    
                    assert result['success'] is True
                    assert result['namespace'] == 'test-ns'
                    assert result['cost_center'] == 'cost-center'
                    assert 'scaled_resources' in result
                    assert 'operation_duration' in result
                    assert result['active_namespaces_count'] == 1
    
    def test_unexpected_error_handling(self, scheduler):
        """Test that unexpected errors are caught and logged properly"""
        with patch.object(scheduler, 'validate_namespace_activation', side_effect=RuntimeError('Unexpected')):
            result = scheduler.activate_namespace('test-ns', 'cost-center')
            
            assert result['success'] is False
            assert 'Unexpected error' in result['error']
            assert result['error_type'] == 'unexpected_error'
            assert 'operation_duration' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
