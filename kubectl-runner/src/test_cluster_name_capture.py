#!/usr/bin/env python3
"""
Test script for cluster name capture in all operations
Tests that cluster_name field is properly captured in all operations
"""

import requests
import json
import sys
import time
import boto3
import os
from datetime import datetime

def test_cluster_name_capture():
    """Test cluster name capture for all operations"""
    base_url = "http://localhost:8080"
    
    # DynamoDB setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table_name = 'task-scheduler-logs'
    table = dynamodb.Table(table_name)
    
    # Expected cluster name from environment or default
    expected_cluster_name = os.getenv('EKS_CLUSTER_NAME', 'unknown-cluster')
    
    print("Testing Cluster Name Capture in All Operations")
    print("=" * 70)
    print(f"Expected cluster name: {expected_cluster_name}")
    
    # Setup: Create test cost center
    print("\nSetup: Creating test cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/cluster-test/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created cluster-test: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create cluster-test: {e}")
    
    time.sleep(2)  # Give DynamoDB time to propagate
    
    # Test 1: Namespace activation with cluster_name capture
    print("\n1. Testing cluster name capture in NAMESPACE ACTIVATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "cluster-test",
                "user_id": "cluster.test.user",
                "requested_by": "cluster.test.requester"
            }
        )
        print(f"   Activation Status Code: {response.status_code}")
        print(f"   Activation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for activity log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'default',
                    ':ts': timestamp_before
                }
            )
            
            activity_logs = query_response.get('Items', [])
            activation_logs = [
                log for log in activity_logs 
                if log.get('operation_type') == 'manual_activation'
            ]
            
            print(f"   Found {len(activation_logs)} activation log(s)")
            
            if len(activation_logs) > 0:
                log = activation_logs[0]
                print(f"   Activity Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify cluster_name field
                if log.get('cluster_name') == expected_cluster_name:
                    print(f"   ✓ Test passed: cluster_name captured correctly ({expected_cluster_name})")
                else:
                    print(f"   ✗ Test failed: cluster_name={log.get('cluster_name')}, expected={expected_cluster_name}")
                    return False
            else:
                print("   ✗ Test failed: No activation log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Namespace deactivation with cluster_name capture
    print("\n2. Testing cluster name capture in NAMESPACE DEACTIVATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/deactivate",
            json={
                "cost_center": "cluster-test",
                "user_id": "cluster.test.user2",
                "requested_by": "cluster.test.requester2"
            }
        )
        print(f"   Deactivation Status Code: {response.status_code}")
        print(f"   Deactivation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for activity log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'default',
                    ':ts': timestamp_before
                }
            )
            
            activity_logs = query_response.get('Items', [])
            deactivation_logs = [
                log for log in activity_logs 
                if log.get('operation_type') == 'manual_deactivation'
            ]
            
            print(f"   Found {len(deactivation_logs)} deactivation log(s)")
            
            if len(deactivation_logs) > 0:
                log = deactivation_logs[0]
                print(f"   Activity Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify cluster_name field
                if log.get('cluster_name') == expected_cluster_name:
                    print(f"   ✓ Test passed: cluster_name captured correctly ({expected_cluster_name})")
                else:
                    print(f"   ✗ Test failed: cluster_name={log.get('cluster_name')}, expected={expected_cluster_name}")
                    return False
            else:
                print("   ✗ Test failed: No deactivation log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Task creation with cluster_name capture
    print("\n3. Testing cluster name capture in TASK CREATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Cluster Name Test Task",
                "operation_type": "activate",
                "namespace": "cluster-test-namespace",
                "cost_center": "cluster-test",
                "user_id": "cluster.task.user",
                "requested_by": "cluster.task.requester",
                "schedule": "0 9 * * 1-5"
            }
        )
        print(f"   Task Creation Status Code: {response.status_code}")
        print(f"   Task Creation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 201:
            print(f"   ✗ Test failed: Expected 201, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for task creation log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'cluster-test-namespace',
                    ':ts': timestamp_before
                }
            )
            
            activity_logs = query_response.get('Items', [])
            task_logs = [
                log for log in activity_logs 
                if log.get('operation_type') == 'task_created'
            ]
            
            print(f"   Found {len(task_logs)} task creation log(s)")
            
            if len(task_logs) > 0:
                log = task_logs[0]
                print(f"   Activity Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify cluster_name field
                if log.get('cluster_name') == expected_cluster_name:
                    print(f"   ✓ Test passed: cluster_name captured correctly in task creation ({expected_cluster_name})")
                else:
                    print(f"   ✗ Test failed: cluster_name={log.get('cluster_name')}, expected={expected_cluster_name}")
                    return False
            else:
                print("   ✗ Test failed: No task creation log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Validation with cluster_name capture
    print("\n4. Testing cluster name capture in VALIDATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.get(
            f"{base_url}/api/cost-centers/cluster-test/validate",
            params={
                "user_id": "cluster.validation.user",
                "requested_by": "cluster.validation.requester",
                "operation_type": "cluster_test_validation",
                "namespace": "cluster-validation-test-ns"
            }
        )
        print(f"   Validation Status Code: {response.status_code}")
        print(f"   Validation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for validation log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'cluster-validation-test-ns',
                    ':ts': timestamp_before
                }
            )
            
            audit_logs = query_response.get('Items', [])
            validation_logs = [
                log for log in audit_logs 
                if log.get('operation_type', '').startswith('validation_')
            ]
            
            print(f"   Found {len(validation_logs)} validation log(s)")
            
            if len(validation_logs) > 0:
                log = validation_logs[0]
                print(f"   Validation Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify cluster_name field
                if log.get('cluster_name') == expected_cluster_name:
                    print(f"   ✓ Test passed: cluster_name captured correctly in validation ({expected_cluster_name})")
                else:
                    print(f"   ✗ Test failed: cluster_name={log.get('cluster_name')}, expected={expected_cluster_name}")
                    return False
            else:
                print("   ✗ Test failed: No validation log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Verify cluster_name in all existing logs
    print("\n5. Testing cluster_name presence in recent logs...")
    try:
        # Query recent logs to ensure all have cluster_name
        timestamp_cutoff = int(time.time()) - 3600  # Last hour
        
        scan_response = table.scan(
            FilterExpression='timestamp_start >= :ts',
            ExpressionAttributeValues={
                ':ts': timestamp_cutoff
            }
        )
        
        recent_logs = scan_response.get('Items', [])
        print(f"   Found {len(recent_logs)} recent log(s)")
        
        logs_without_cluster = []
        for log in recent_logs:
            if 'cluster_name' not in log or not log['cluster_name']:
                logs_without_cluster.append(log)
        
        if len(logs_without_cluster) == 0:
            print("   ✓ Test passed: All recent logs have cluster_name field")
        else:
            print(f"   ✗ Test failed: {len(logs_without_cluster)} logs missing cluster_name:")
            for log in logs_without_cluster[:3]:  # Show first 3
                print(f"      - {log.get('operation_type', 'unknown')} on {log.get('namespace_name', 'unknown')}")
            return False
                
    except Exception as e:
        print(f"   ✗ Test failed scanning DynamoDB: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("All cluster name capture tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_cluster_name_capture()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)