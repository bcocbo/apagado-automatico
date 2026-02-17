#!/usr/bin/env python3
"""
Test script for audit logging of validations
Tests that validation events are properly logged to DynamoDB
"""

import requests
import json
import sys
import time
import boto3
from datetime import datetime

def test_audit_logging():
    """Test audit logging for validation events"""
    base_url = "http://localhost:8080"
    
    # DynamoDB setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table_name = 'task-scheduler-logs'
    table = dynamodb.Table(table_name)
    
    print("Testing Audit Logging for Validations")
    print("=" * 70)
    
    # Setup: Create test cost centers
    print("\nSetup: Creating test cost centers...")
    
    # Authorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/audit-test-authorized/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created audit-test-authorized: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create audit-test-authorized: {e}")
    
    # Unauthorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/audit-test-unauthorized/permissions",
            json={
                "is_authorized": False,
                "max_concurrent_namespaces": 0,
                "authorized_namespaces": []
            }
        )
        print(f"   Created audit-test-unauthorized: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create audit-test-unauthorized: {e}")
    
    time.sleep(2)  # Give DynamoDB time to propagate
    
    # Test 1: Validate authorized cost center and check audit log
    print("\n1. Testing audit log for AUTHORIZED cost center validation...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.get(
            f"{base_url}/api/cost-centers/audit-test-authorized/validate",
            params={
                "user_id": "test-user-1",
                "operation_type": "test_validation",
                "namespace": "test-namespace"
            }
        )
        print(f"   Validation Status Code: {response.status_code}")
        print(f"   Validation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for audit log
        try:
            # Query by namespace (since it's the hash key)
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'test-namespace',
                    ':ts': timestamp_before
                }
            )
            
            audit_logs = query_response.get('Items', [])
            validation_logs = [
                log for log in audit_logs 
                if log.get('operation_type', '').startswith('validation_')
            ]
            
            print(f"   Found {len(validation_logs)} validation audit log(s)")
            
            if len(validation_logs) > 0:
                log = validation_logs[0]
                print(f"   Audit Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify audit log fields
                if (log.get('cost_center') == 'audit-test-authorized' and
                    log.get('validation_result') == 'success' and
                    log.get('user_id') == 'test-user-1' and
                    log.get('requested_operation') == 'test_validation'):
                    print("   ✓ Test passed: Audit log created with correct fields")
                else:
                    print("   ✗ Test failed: Audit log missing expected fields")
                    return False
            else:
                print("   ✗ Test failed: No validation audit log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Validate unauthorized cost center and check audit log
    print("\n2. Testing audit log for UNAUTHORIZED cost center validation...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.get(
            f"{base_url}/api/cost-centers/audit-test-unauthorized/validate",
            params={
                "user_id": "test-user-2",
                "operation_type": "test_validation_fail",
                "namespace": "test-namespace-2"
            }
        )
        print(f"   Validation Status Code: {response.status_code}")
        print(f"   Validation Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for audit log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'test-namespace-2',
                    ':ts': timestamp_before
                }
            )
            
            audit_logs = query_response.get('Items', [])
            validation_logs = [
                log for log in audit_logs 
                if log.get('operation_type', '').startswith('validation_')
            ]
            
            print(f"   Found {len(validation_logs)} validation audit log(s)")
            
            if len(validation_logs) > 0:
                log = validation_logs[0]
                print(f"   Audit Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify audit log fields for failed validation
                if (log.get('cost_center') == 'audit-test-unauthorized' and
                    log.get('validation_result') == 'failure' and
                    log.get('user_id') == 'test-user-2' and
                    log.get('requested_operation') == 'test_validation_fail'):
                    print("   ✓ Test passed: Audit log created for failed validation")
                else:
                    print("   ✗ Test failed: Audit log missing expected fields")
                    return False
            else:
                print("   ✗ Test failed: No validation audit log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Namespace activation with audit logging
    print("\n3. Testing audit log for namespace ACTIVATION validation...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "audit-test-authorized",
                "user_id": "test-user-3"
            }
        )
        print(f"   Activation Status Code: {response.status_code}")
        print(f"   Activation Response: {json.dumps(response.json(), indent=2)}")
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for audit log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'default',
                    ':ts': timestamp_before
                }
            )
            
            audit_logs = query_response.get('Items', [])
            validation_logs = [
                log for log in audit_logs 
                if log.get('operation_type', '').startswith('validation_')
            ]
            
            print(f"   Found {len(validation_logs)} validation audit log(s)")
            
            if len(validation_logs) > 0:
                log = validation_logs[0]
                print(f"   Audit Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify audit log fields
                if (log.get('cost_center') == 'audit-test-authorized' and
                    log.get('validation_result') == 'success' and
                    log.get('user_id') == 'test-user-3' and
                    log.get('requested_operation') == 'namespace_activation'):
                    print("   ✓ Test passed: Audit log created for activation validation")
                else:
                    print("   ✗ Test failed: Audit log missing expected fields")
                    return False
            else:
                print("   ✗ Test failed: No validation audit log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Task creation with audit logging
    print("\n4. Testing audit log for TASK CREATION validation...")
    try:
        timestamp_before = int(time.time())
        
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Audit Test Task",
                "operation_type": "activate",
                "namespace": "audit-test-namespace",
                "cost_center": "audit-test-authorized",
                "user_id": "test-user-4",
                "schedule": "0 9 * * 1-5"
            }
        )
        print(f"   Task Creation Status Code: {response.status_code}")
        print(f"   Task Creation Response: {json.dumps(response.json(), indent=2)}")
        
        # Wait for DynamoDB to process
        time.sleep(2)
        
        # Query DynamoDB for audit log
        try:
            query_response = table.query(
                KeyConditionExpression='namespace_name = :ns AND timestamp_start >= :ts',
                ExpressionAttributeValues={
                    ':ns': 'audit-test-namespace',
                    ':ts': timestamp_before
                }
            )
            
            audit_logs = query_response.get('Items', [])
            validation_logs = [
                log for log in audit_logs 
                if log.get('operation_type', '').startswith('validation_')
            ]
            
            print(f"   Found {len(validation_logs)} validation audit log(s)")
            
            if len(validation_logs) > 0:
                log = validation_logs[0]
                print(f"   Audit Log: {json.dumps(log, indent=2, default=str)}")
                
                # Verify audit log fields
                if (log.get('cost_center') == 'audit-test-authorized' and
                    log.get('validation_result') == 'success' and
                    log.get('user_id') == 'test-user-4' and
                    log.get('requested_operation') == 'task_creation'):
                    print("   ✓ Test passed: Audit log created for task creation validation")
                else:
                    print("   ✗ Test failed: Audit log missing expected fields")
                    return False
            else:
                print("   ✗ Test failed: No validation audit log found")
                return False
                
        except Exception as e:
            print(f"   ✗ Test failed querying DynamoDB: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("All audit logging tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_audit_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
