#!/usr/bin/env python3
"""
Basic tests for the enhanced namespace controller functionality.
These tests focus on core logic without external dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time
from datetime import datetime, timedelta

# Add controller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'controller'))

class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality"""
    
    def setUp(self):
        # Mock the dependencies
        with patch.multiple('scaler',
                          boto3=Mock(),
                          subprocess=Mock(),
                          structlog=Mock(),
                          prometheus_client=Mock(),
                          pytz=Mock(),
                          uuid=Mock()):
            from scaler import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState
            self.CircuitBreaker = CircuitBreaker
            self.CircuitBreakerConfig = CircuitBreakerConfig
            self.CircuitBreakerState = CircuitBreakerState
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state allows operations"""
        cb = self.CircuitBreaker()
        
        def test_func():
            return "success"
        
        result = cb.call(test_func)
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, self.CircuitBreakerState.CLOSED)
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        config = self.CircuitBreakerConfig(failure_threshold=2, timeout=60)
        cb = self.CircuitBreaker(config)
        
        def failing_func():
            raise Exception("Test failure")
        
        # First failure
        with self.assertRaises(Exception):
            cb.call(failing_func)
        self.assertEqual(cb.state, self.CircuitBreakerState.CLOSED)
        
        # Second failure should open the circuit
        with self.assertRaises(Exception):
            cb.call(failing_func)
        self.assertEqual(cb.state, self.CircuitBreakerState.OPEN)
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout"""
        config = self.CircuitBreakerConfig(failure_threshold=1, timeout=1)
        cb = self.CircuitBreaker(config)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Trigger failure to open circuit
        with self.assertRaises(Exception):
            cb.call(failing_func)
        self.assertEqual(cb.state, self.CircuitBreakerState.OPEN)
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Next call should transition to half-open
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, self.CircuitBreakerState.CLOSED)


class TestRollbackManager(unittest.TestCase):
    """Test rollback manager functionality"""
    
    def setUp(self):
        with patch.multiple('scaler',
                          boto3=Mock(),
                          subprocess=Mock(),
                          structlog=Mock(),
                          prometheus_client=Mock(),
                          pytz=Mock(),
                          uuid=Mock()):
            from scaler import EnhancedRollbackManager, DeploymentState
            self.EnhancedRollbackManager = EnhancedRollbackManager
            self.DeploymentState = DeploymentState
    
    def test_save_and_retrieve_state(self):
        """Test saving and retrieving rollback state"""
        rollback_manager = self.EnhancedRollbackManager()
        
        deployments = [
            {'name': 'app1', 'replicas': 3},
            {'name': 'app2', 'replicas': 2}
        ]
        
        operation_id = rollback_manager.save_state('test-namespace', deployments)
        
        self.assertIsNotNone(operation_id)
        self.assertIn('test-namespace', rollback_manager.rollback_history)
        
        rollback_data = rollback_manager.get_rollback_history('test-namespace')
        self.assertIsNotNone(rollback_data)
        self.assertEqual(len(rollback_data.deployments), 2)
        self.assertEqual(rollback_data.deployments[0].name, 'app1')
        self.assertEqual(rollback_data.deployments[0].replicas, 3)
    
    def test_rollback_in_progress_tracking(self):
        """Test tracking of rollback operations in progress"""
        rollback_manager = self.EnhancedRollbackManager()
        
        # Initially no rollback in progress
        self.assertFalse(rollback_manager.is_rollback_in_progress('test-namespace'))
        
        # Simulate rollback in progress
        rollback_manager.rollback_in_progress.add('test-namespace')
        self.assertTrue(rollback_manager.is_rollback_in_progress('test-namespace'))
        
        # Clear rollback
        rollback_manager.rollback_in_progress.discard('test-namespace')
        self.assertFalse(rollback_manager.is_rollback_in_progress('test-namespace'))


class TestPrometheusMetrics(unittest.TestCase):
    """Test Prometheus metrics functionality"""
    
    def setUp(self):
        with patch.multiple('scaler',
                          boto3=Mock(),
                          subprocess=Mock(),
                          structlog=Mock(),
                          prometheus_client=Mock(),
                          pytz=Mock(),
                          uuid=Mock()):
            from scaler import PrometheusMetrics
            self.PrometheusMetrics = PrometheusMetrics
    
    def test_metrics_initialization(self):
        """Test metrics class initializes correctly"""
        metrics = self.PrometheusMetrics()
        
        # Check that metrics objects are assigned
        self.assertIsNotNone(metrics.scaling_operations)
        self.assertIsNotNone(metrics.scaling_duration)
        self.assertIsNotNone(metrics.active_namespaces)
        self.assertIsNotNone(metrics.controller_errors)
    
    def test_record_scaling_operation(self):
        """Test recording scaling operation metrics"""
        metrics = self.PrometheusMetrics()
        
        # Mock the metrics objects
        metrics.scaling_operations = Mock()
        metrics.scaling_duration = Mock()
        
        # Record a successful operation
        metrics.record_scaling_operation('test-ns', 'shutdown', 'success', 1.5)
        
        # Verify metrics were called
        metrics.scaling_operations.labels.assert_called_with(
            namespace='test-ns', 
            operation='shutdown', 
            status='success'
        )
        metrics.scaling_operations.labels().inc.assert_called_once()
        
        metrics.scaling_duration.labels.assert_called_with(
            namespace='test-ns', 
            operation='shutdown'
        )
        metrics.scaling_duration.labels().observe.assert_called_with(1.5)


class TestStructuredLogging(unittest.TestCase):
    """Test structured logging functionality"""
    
    def setUp(self):
        with patch.multiple('scaler',
                          boto3=Mock(),
                          subprocess=Mock(),
                          structlog=Mock(),
                          prometheus_client=Mock(),
                          pytz=Mock(),
                          uuid=Mock()):
            from scaler import ContextualLogger, OperationLogger
            self.ContextualLogger = ContextualLogger
            self.OperationLogger = OperationLogger
    
    def test_contextual_logger_binding(self):
        """Test contextual logger context binding"""
        base_logger = Mock()
        logger = self.ContextualLogger(base_logger)
        
        # Bind context
        bound_logger = logger.bind(namespace='test-ns', operation='scale')
        
        # Verify context is preserved
        self.assertEqual(bound_logger.context['namespace'], 'test-ns')
        self.assertEqual(bound_logger.context['operation'], 'scale')
    
    def test_operation_logger_context_manager(self):
        """Test operation logger as context manager"""
        with patch('scaler.time.time', return_value=1000.0):
            op_logger = self.OperationLogger('test_operation', namespace='test-ns')
            
            with op_logger as logger:
                self.assertIsNotNone(logger.correlation_id)
                self.assertEqual(op_logger.operation_name, 'test_operation')
                self.assertEqual(op_logger.namespace, 'test-ns')


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)