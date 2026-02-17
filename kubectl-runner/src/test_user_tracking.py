#!/usr/bin/env python3
"""
Test script for user tracking in all operations
Tests that requested_by field is properly captured in all operations
"""

import requests
import json
import sys
import time
import boto3
from datetime import datetime

def test_user_tracking():
    """Test user tracking for all operations"""
    base_url = "http://localhost:8080"
    
    # DynamoDB setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table_name = 'task-scheduler-logs'
    table = dynamodb.Table(table_name)
    
    print("Testing User Tracking in All Operations")
    print("=" * 70)
    
    # Setup: Create test cost center
    print("\nSetup: Creating test cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/user-tracking-test/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created user-tracking-test: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create user-tracking-test: {e}")
    
    time.sleep(2)  # Give DynamoDB time to propagate
    
    # Test 1: Namespace activation with requested_by
    print("\n1. Testing user tracking in NAMESPACE ACTIVATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "user-tracking-test",
                "user_id": "john.doe",
                "requested_by": "jane.smith"  # Different from user_id
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
                
                # Verify requested_by field
                if (log.get('requested_by') == 'jane.smith' and
                    log.get('user_id') == 'jane.smith' and
                    log.get('cost_center') == 'user-tracking-test'):
                    print("   ✓ Test passed: requested_by captured correctly")
                else:
                    print(f"   ✗ Test failed: requested_by={log.get('requested_by')}, expected=jane.smith")
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
    
    # Test 2: Namespace deactivation with requested_by
    print("\n2. Testing user tracking in NAMESPACE DEACTIVATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/deactivate",
            json={
                "cost_center": "user-tracking-test",
                "user_id": "alice.jones",
                "requested_by": "bob.wilson"
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
                
                # Verify requested_by field
                if (log.get('requested_by') == 'bob.wilson' and
                    log.get('user_id') == 'bob.wilson'):
                    print("   ✓ Test passed: requested_by captured correctly")
                else:
                    print(f"   ✗ Test failed: requested_by={log.get('requested_by')}, expected=bob.wilson")
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
    
    # Test 3: Task creation with requested_by
    print("\n3. Testing user tracking in TASK CREATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "User Tracking Test Task",
                "operation_type": "activate",
                "namespace": "user-tracking-namespace",
                "cost_center": "user-tracking-test",
                "user_id": "charlie.brown",
                "requested_by": "david.miller",
                "schedule": "0 9 * * 1-5"
            }
        )
        print(f"   Task Creation Status Code: {response.status_code}")
        print(f"   Task Creation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 201:
            print(f"   ✗ Test failed: Expected 201, got {response.status_code}")
            return False
        
        task_data = response.json()
        
        # Verify created_by field in task
        if task_data.get('created_by') == 'david.miller':
            print("   ✓ Task has created_by field set correctly")
        else:
            print(f"   ✗ Test failed: created_by={task_data.get('created_by')}, expected=david.miller")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for task creation log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'user-tracking-namespace',
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
                
                # Verify requested_by field
                if (log.get('requested_by') == 'david.miller' and
                    log.get('user_id') == 'david.miller'):
                    print("   ✓ Test passed: requested_by captured correctly in task creation")
                else:
                    print(f"   ✗ Test failed: requested_by={log.get('requested_by')}, expected=david.miller")
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
    
    # Test 4: Validation with requested_by
    print("\n4. Testing user tracking in VALIDATION...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.get(
            f"{base_url}/api/cost-centers/user-tracking-test/validate",
            params={
                "user_id": "emily.davis",
                "requested_by": "frank.garcia",
                "operation_type": "test_validation",
                "namespace": "validation-test-ns"
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
                    ':ns': 'validation-test-ns',
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
                
                # Verify requested_by field
                if (log.get('requested_by') == 'frank.garcia' and
                    log.get('user_id') == 'frank.garcia'):
                    print("   ✓ Test passed: requested_by captured correctly in validation")
                else:
                    print(f"   ✗ Test failed: requested_by={log.get('requested_by')}, expected=frank.garcia")
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
    
    # Test 5: Default to 'system' when no user provided
    print("\n5. Testing default to 'system' when no user provided...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "user-tracking-test"
                # No user_id or requested_by provided
            }
        )
        print(f"   Activation Status Code: {response.status_code}")
        
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
            
            if len(activation_logs) > 0:
                log = activation_logs[0]
                
                # Verify defaults to 'anonymous' (from endpoint default)
                if log.get('requested_by') == 'anonymous':
                    print("   ✓ Test passed: Defaults to 'anonymous' when no user provided")
                else:
                    print(f"   ✗ Test failed: requested_by={log.get('requested_by')}, expected=anonymous")
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
    
    print("\n" + "=" * 70)
    print("All user tracking tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_user_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
