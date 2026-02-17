#!/usr/bin/env python3
"""
Simple test to verify cluster name implementation without running the full API server
Tests the core logic of cluster name capture
"""

import os
import sys
import json
from unittest.mock import Mock, patch
import tempfile

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cluster_name_implementation():
    """Test cluster name capture implementation"""
    print("Testing Cluster Name Implementation")
    print("=" * 50)
    
    # Test 1: Verify cluster_name is captured from environment
    print("\n1. Testing cluster name from environment variable...")
    
    with patch.dict(os.environ, {'EKS_CLUSTER_NAME': 'test-cluster-123'}):
        # Import after setting environment variable
        from app import TaskScheduler, DynamoDBManager
        
        # Mock DynamoDB to avoid actual AWS calls
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_permissions_table = Mock()
            
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.side_effect = [mock_table, mock_permissions_table]
            mock_table.load.return_value = None
            mock_permissions_table.load.return_value = None
            
            # Create TaskScheduler instance
            scheduler = TaskScheduler()
            
            # Verify cluster_name is set correctly
            if scheduler.cluster_name == 'test-cluster-123':
                print("   ✓ Cluster name captured from environment variable")
            else:
                print(f"   ✗ Expected 'test-cluster-123', got '{scheduler.cluster_name}'")
                return False
    
    # Test 2: Verify default cluster name when environment variable is not set
    print("\n2. Testing default cluster name...")
    
    # Remove EKS_CLUSTER_NAME from environment if it exists
    env_backup = os.environ.get('EKS_CLUSTER_NAME')
    if 'EKS_CLUSTER_NAME' in os.environ:
        del os.environ['EKS_CLUSTER_NAME']
    
    try:
        # Re-import to get fresh instance
        import importlib
        import app
        importlib.reload(app)
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_permissions_table = Mock()
            
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.side_effect = [mock_table, mock_permissions_table]
            mock_table.load.return_value = None
            mock_permissions_table.load.return_value = None
            
            scheduler = app.TaskScheduler()
            
            if scheduler.cluster_name == 'unknown-cluster':
                print("   ✓ Default cluster name used when environment variable not set")
            else:
                print(f"   ✗ Expected 'unknown-cluster', got '{scheduler.cluster_name}'")
                return False
    finally:
        # Restore environment variable
        if env_backup:
            os.environ['EKS_CLUSTER_NAME'] = env_backup
    
    # Test 3: Verify cluster_name is passed to DynamoDB logging
    print("\n3. Testing cluster name in DynamoDB logging...")
    
    with patch.dict(os.environ, {'EKS_CLUSTER_NAME': 'logging-test-cluster'}):
        import importlib
        import app
        importlib.reload(app)
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_permissions_table = Mock()
            
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.side_effect = [mock_table, mock_permissions_table]
            mock_table.load.return_value = None
            mock_permissions_table.load.return_value = None
            
            # Mock put_item to capture the data
            logged_items = []
            def capture_put_item(Item):
                logged_items.append(Item)
                return {'ResponseMetadata': {'HTTPStatusCode': 200}}
            
            mock_table.put_item.side_effect = capture_put_item
            
            # Create DynamoDBManager and test logging
            db_manager = app.DynamoDBManager()
            
            # Test log_namespace_activity
            db_manager.log_namespace_activity(
                namespace_name='test-namespace',
                operation_type='test_operation',
                cost_center='test-cost-center',
                user_id='test-user',
                requested_by='test-requester'
            )
            
            # Verify cluster_name was included
            if len(logged_items) > 0:
                logged_item = logged_items[0]
                if logged_item.get('cluster_name') == 'logging-test-cluster':
                    print("   ✓ Cluster name included in DynamoDB logging")
                else:
                    print(f"   ✗ Expected cluster_name='logging-test-cluster', got '{logged_item.get('cluster_name')}'")
                    return False
            else:
                print("   ✗ No items were logged to DynamoDB")
                return False
    
    # Test 4: Verify cluster_name in validation audit logging
    print("\n4. Testing cluster name in validation audit logging...")
    
    with patch.dict(os.environ, {'EKS_CLUSTER_NAME': 'audit-test-cluster'}):
        import importlib
        import app
        importlib.reload(app)
        
        with patch('boto3.resource') as mock_boto3:
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_permissions_table = Mock()
            
            mock_boto3.return_value = mock_dynamodb
            mock_dynamodb.Table.side_effect = [mock_table, mock_permissions_table]
            mock_table.load.return_value = None
            mock_permissions_table.load.return_value = None
            
            # Mock get_item to return authorized cost center
            mock_permissions_table.get_item.return_value = {
                'Item': {
                    'cost_center': 'test-cost-center',
                    'is_authorized': True
                }
            }
            
            # Mock put_item to capture audit logs
            audit_logs = []
            def capture_audit_log(Item):
                audit_logs.append(Item)
                return {'ResponseMetadata': {'HTTPStatusCode': 200}}
            
            mock_table.put_item.side_effect = capture_audit_log
            
            # Create DynamoDBManager and test validation
            db_manager = app.DynamoDBManager()
            
            # Test validation with audit logging
            result = db_manager.validate_cost_center_permissions(
                cost_center='test-cost-center',
                user_id='audit-test-user',
                requested_by='audit-test-requester',
                operation_type='test_validation',
                namespace='test-namespace'
            )
            
            # Verify audit log contains cluster_name
            if len(audit_logs) > 0:
                audit_log = audit_logs[0]
                if audit_log.get('cluster_name') == 'audit-test-cluster':
                    print("   ✓ Cluster name included in validation audit logging")
                else:
                    print(f"   ✗ Expected cluster_name='audit-test-cluster', got '{audit_log.get('cluster_name')}'")
                    return False
            else:
                print("   ✗ No audit logs were created")
                return False
    
    print("\n" + "=" * 50)
    print("All cluster name implementation tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_cluster_name_implementation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)