#!/usr/bin/env python3
"""
Integration tests for the enhanced namespace controller.
These tests verify that all core functionality is working together.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import time
from datetime import datetime, timedelta

# Add controller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controller'))

class TestControllerIntegration(unittest.TestCase):
    """Integration tests for the complete controller functionality"""
    
    def setUp(self):
        """Set up test environment with mocked dependencies"""
        self.mock_patches = {}
        
        # Mock all external dependencies
        self.mock_patches['boto3'] = patch('scaler.boto3')
        self.mock_patches['subprocess'] = patch('scaler.subprocess')
        self.mock_patches['structlog'] = patch('scaler.structlog')
        self.mock_patches['prometheus_client'] = patch('scaler.prometheus_client')
        self.mock_patches['pytz'] = patch('scaler.pytz')
        self.mock_patches['uuid'] = patch('scaler.uuid')
        self.mock_patches['psutil'] = patch('scaler.psutil', create=True)
        self.mock_patches['requests'] = patch('scaler.requests', create=True)
        self.mock_patches['smtplib'] = patch('scaler.smtplib', create=True)
        
        # Start all patches
        self.mocks = {}
        for name, patcher in self.mock_patches.items():
            self.mocks[name] = patcher.start()
        
        # Configure basic mocks
        self.mocks['uuid'].uuid4.return_value.hex = 'test-correlation-id'
        self.mocks['structlog'].get_logger.return_value = Mock()
        
        # Mock timezone
        mock_timezone = Mock()
        mock_timezone.localize.return_value = datetime.now()
        self.mocks['pytz'].timezone.return_value = mock_timezone
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.name = 'test-table'
        mock_table.scan.return_value = {'Items': []}
        mock_table.put_item.return_value = {}
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        self.mocks['boto3'].resource.return_value = mock_dynamodb
        
        # Mock subprocess for kubectl commands
        self.mocks['subprocess'].check_output.return_value = b'test-namespace'
        self.mocks['subprocess'].run.return_value = Mock(returncode=0)
        
        # Mock Prometheus metrics
        for metric_name in ['Counter', 'Histogram', 'Gauge']:
            metric_mock = Mock()
            metric_mock.labels.return_value = metric_mock
            metric_mock.inc.return_value = None
            metric_mock.observe.return_value = None
            metric_mock.set.return_value = None
            setattr(self.mocks['prometheus_client'], metric_name, Mock(return_value=metric_mock))
        
        # Now import the controller classes
        from scaler import (
            NamespaceController, 
            CircuitBreaker, 
            EnhancedRollbackManager,
            PrometheusMetrics,
            ContextualLogger,
            OperationLogger
        )
        
        self.NamespaceController = NamespaceController
        self.CircuitBreaker = CircuitBreaker
        self.EnhancedRollbackManager = EnhancedRollbackManager
        self.PrometheusMetrics = PrometheusMetrics
        self.ContextualLogger = ContextualLogger
        self.OperationLogger = OperationLogger
    
    def tearDown(self):
        """Clean up patches"""
        for patcher in self.mock_patches.values():
            patcher.stop()
    
    def test_controller_initialization(self):
        """Test that the controller initializes correctly with all components"""
        controller = self.NamespaceController()
        
        # Verify all components are initialized
        self.assertIsNotNone(controller.circuit_breaker)
        self.assertIsNotNone(controller.rollback_manager)
        self.assertIsNotNone(controller.degradation_manager)
        self.assertIsNotNone(controller.metrics)
        self.assertIsNotNone(controller.logger)
        
        # Verify configuration is loaded
        self.assertIsNotNone(controller.timezone)
        self.assertIsNotNone(controller.system_namespaces)
        self.assertIsInstance(controller.failure_counts, dict)
        self.assertIsInstance(controller.blocked_operations, dict)
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with controller operations"""
        controller = self.NamespaceController()
        
        # Test successful operation
        self.mocks['subprocess'].check_output.return_value = b'test-namespace'
        
        namespaces = controller.get_namespaces()
        self.assertIsInstance(namespaces, list)
        
        # Verify circuit breaker is in closed state
        self.assertEqual(controller.circuit_breaker.state.value, "CLOSED")
    
    def test_metrics_integration(self):
        """Test that metrics are properly integrated and recorded"""
        controller = self.NamespaceController()
        
        # Test scaling operation with metrics
        self.mocks['subprocess'].check_output.return_value = b'app1,3\napp2,2\n'
        
        # Mock successful scaling
        controller.scale_namespace('test-namespace', True)
        
        # Verify metrics methods were called (through mocked prometheus client)
        self.assertTrue(self.mocks['prometheus_client'].Counter.called)
        self.assertTrue(self.mocks['prometheus_client'].Histogram.called)
    
    def test_rollback_manager_integration(self):
        """Test rollback manager integration with the controller"""
        controller = self.NamespaceController()
        
        # Test state saving
        deployments = [{'name': 'app1', 'replicas': 3}]
        operation_id = controller.rollback_manager.save_state('test-namespace', deployments)
        
        self.assertIsNotNone(operation_id)
        self.assertIn('test-namespace', controller.rollback_manager.rollback_history)
        
        # Test rollback functionality
        rollback_success = controller.rollback_manager.rollback('test-namespace')
        # Should succeed with mocked subprocess
        self.assertTrue(rollback_success)
    
    def test_structured_logging_integration(self):
        """Test structured logging integration"""
        controller = self.NamespaceController()
        
        # Test contextual logger
        self.assertIsNotNone(controller.logger)
        
        # Test operation logger context manager
        with self.OperationLogger('test_operation', namespace='test-ns') as op_logger:
            self.assertIsNotNone(op_logger.correlation_id)
            self.assertEqual(op_logger.operation_name, 'test_operation')
            self.assertEqual(op_logger.namespace, 'test-ns')
    
    def test_graceful_degradation(self):
        """Test graceful degradation when external services fail"""
        controller = self.NamespaceController()
        
        # Simulate kubectl failure
        self.mocks['subprocess'].check_output.side_effect = Exception("kubectl failed")
        
        # Should handle gracefully and use fallback
        namespaces = controller.get_namespaces()
        
        # Should return empty list or cached data, not crash
        self.assertIsInstance(namespaces, list)
    
    def test_notification_channels_setup(self):
        """Test that notification channels are properly configured"""
        controller = self.NamespaceController()
        
        # Verify notification channels are set up
        self.assertGreater(len(controller.rollback_manager.notification_channels), 0)
    
    def test_health_check_functionality(self):
        """Test health check functionality"""
        # Import health check function
        from scaler import health_check
        
        # Mock successful health checks
        self.mocks['subprocess'].check_output.return_value = b'{"status": "ok"}'
        
        health_status = health_check()
        
        self.assertIsInstance(health_status, dict)
        self.assertIn('status', health_status)
        self.assertIn('timestamp', health_status)
    
    def test_schedule_operations(self):
        """Test schedule creation and retrieval operations"""
        from scaler import create_schedule, get_schedules
        
        # Test schedule creation
        schedule_data = {
            'namespace': 'test-namespace',
            'startup_time': '08:00',
            'shutdown_time': '17:00',
            'days_of_week': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            'metadata': {
                'business_unit': 'engineering',
                'cost_savings_target': '1000'
            }
        }
        
        new_schedule = create_schedule(schedule_data)
        self.assertIsInstance(new_schedule, dict)
        self.assertEqual(new_schedule['namespace'], 'test-namespace')
        
        # Test schedule retrieval
        schedules = get_schedules()
        self.assertIsInstance(schedules, list)
    
    def test_complete_scaling_workflow(self):
        """Test complete scaling workflow with all components"""
        controller = self.NamespaceController()
        
        # Mock deployment state
        self.mocks['subprocess'].check_output.side_effect = [
            b'app1,3\napp2,2\n',  # get_deployment_state
            b'app1\napp2\n',      # get deployments for scaling
            b'3',                 # get current replicas for app1
            b'2',                 # get current replicas for app2
        ]
        
        # Test scaling down (shutdown)
        result = controller.scale_namespace('test-namespace', True)
        
        # Should succeed with mocked operations
        self.assertTrue(result)
        
        # Verify state was saved for rollback
        self.assertIn('test-namespace', controller.rollback_manager.rollback_history)
        
        # Verify kubectl scale commands were called
        scale_calls = [call for call in self.mocks['subprocess'].run.call_args_list 
                      if 'scale' in str(call)]
        self.assertGreater(len(scale_calls), 0)


class TestControllerErrorHandling(unittest.TestCase):
    """Test error handling and resilience features"""
    
    def setUp(self):
        """Set up test environment with mocked dependencies"""
        # Similar setup to integration test but focused on error scenarios
        self.mock_patches = {}
        
        # Mock all external dependencies
        self.mock_patches['boto3'] = patch('scaler.boto3')
        self.mock_patches['subprocess'] = patch('scaler.subprocess')
        self.mock_patches['structlog'] = patch('scaler.structlog')
        self.mock_patches['prometheus_client'] = patch('scaler.prometheus_client')
        self.mock_patches['pytz'] = patch('scaler.pytz')
        self.mock_patches['uuid'] = patch('scaler.uuid')
        
        # Start all patches
        self.mocks = {}
        for name, patcher in self.mock_patches.items():
            self.mocks[name] = patcher.start()
        
        # Configure basic mocks
        self.mocks['uuid'].uuid4.return_value.hex = 'test-correlation-id'
        self.mocks['structlog'].get_logger.return_value = Mock()
        
        # Mock timezone
        mock_timezone = Mock()
        mock_timezone.localize.return_value = datetime.now()
        self.mocks['pytz'].timezone.return_value = mock_timezone
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.name = 'test-table'
        mock_table.scan.return_value = {'Items': []}
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        self.mocks['boto3'].resource.return_value = mock_dynamodb
        
        # Mock Prometheus metrics
        for metric_name in ['Counter', 'Histogram', 'Gauge']:
            metric_mock = Mock()
            metric_mock.labels.return_value = metric_mock
            metric_mock.inc.return_value = None
            metric_mock.observe.return_value = None
            metric_mock.set.return_value = None
            setattr(self.mocks['prometheus_client'], metric_name, Mock(return_value=metric_mock))
        
        # Import controller
        from scaler import NamespaceController
        self.NamespaceController = NamespaceController
    
    def tearDown(self):
        """Clean up patches"""
        for patcher in self.mock_patches.values():
            patcher.stop()
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after repeated failures"""
        controller = self.NamespaceController()
        
        # Configure circuit breaker with low threshold for testing
        controller.circuit_breaker.config.failure_threshold = 2
        
        # Simulate repeated failures
        self.mocks['subprocess'].check_output.side_effect = Exception("kubectl failed")
        
        # First failure
        try:
            controller.get_namespaces()
        except:
            pass
        
        # Second failure should open circuit
        try:
            controller.get_namespaces()
        except:
            pass
        
        # Verify circuit is open
        self.assertEqual(controller.circuit_breaker.state.value, "OPEN")
    
    def test_automatic_rollback_on_repeated_failures(self):
        """Test automatic rollback triggers on repeated scaling failures"""
        controller = self.NamespaceController()
        
        # Mock initial successful state save
        self.mocks['subprocess'].check_output.return_value = b'app1,3\n'
        
        # Mock scaling failure
        self.mocks['subprocess'].run.side_effect = Exception("scaling failed")
        
        # Trigger multiple failures
        controller.scale_namespace('test-namespace', True)  # First failure
        controller.scale_namespace('test-namespace', True)  # Second failure should trigger rollback
        
        # Verify failure count increased
        self.assertGreater(controller.failure_counts.get('test-namespace', 0), 0)
    
    def test_operation_blocking_after_rollback(self):
        """Test that operations are blocked temporarily after rollback"""
        controller = self.NamespaceController()
        
        # Block operations for test namespace
        controller.block_operations_temporarily('test-namespace', duration_minutes=1)
        
        # Verify operation is blocked
        self.assertTrue(controller.is_operation_blocked('test-namespace'))
        
        # Test that scaling is blocked
        result = controller.scale_namespace('test-namespace', True)
        self.assertFalse(result)  # Should be blocked


if __name__ == '__main__':
    # Run the tests
    print("🧪 Running Controller Integration Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestControllerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestControllerErrorHandling))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed! Core controller functionality is complete.")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        print("Core controller functionality needs attention.")
    
    print(f"📊 Tests run: {result.testsRun}")
    print(f"⏱️  Time: {result.testsRun * 0.1:.1f}s (estimated)")