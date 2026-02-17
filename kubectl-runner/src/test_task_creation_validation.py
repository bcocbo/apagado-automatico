#!/usr/bin/env python3
"""
Test script for task creation validation
Tests that cost center validation is enforced when creating scheduled tasks
"""

import requests
import json
import sys
import time

def test_task_creation_validation():
    """Test task creation with cost center validation"""
    base_url = "http://localhost:8080"
    
    print("Testing Task Creation Validation")
    print("=" * 60)
    
    # Setup: Create test cost centers
    print("\nSetup: Creating test cost centers...")
    
    # Authorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/task-authorized/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created task-authorized: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create task-authorized: {e}")
    
    # Unauthorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/task-unauthorized/permissions",
            json={
                "is_authorized": False,
                "max_concurrent_namespaces": 0,
                "authorized_namespaces": []
            }
        )
        print(f"   Created task-unauthorized: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create task-unauthorized: {e}")
    
    time.sleep(1)  # Give DynamoDB time to propagate
    
    # Test 1: Create task with authorized cost center
    print("\n1. Testing task creation with AUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Test Task - Authorized",
                "operation_type": "activate",
                "namespace": "test-namespace",
                "cost_center": "task-authorized",
                "schedule": "0 9 * * 1-5"  # 9 AM weekdays
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get('id') and data.get('cost_center') == 'task-authorized':
                print("   ✓ Test passed: Task created with authorized cost center")
                # Save task ID for cleanup
                task_id = data.get('id')
            else:
                print(f"   ✗ Test failed: Task missing expected fields")
                return False
        else:
            print(f"   ✗ Test failed: Expected 201, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Create task with unauthorized cost center
    print("\n2. Testing task creation with UNAUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Test Task - Unauthorized",
                "operation_type": "activate",
                "namespace": "test-namespace",
                "cost_center": "task-unauthorized",
                "schedule": "0 9 * * 1-5"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 403:
            data = response.json()
            if 'error' in data and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Task creation rejected with unauthorized cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 403, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Create task with non-existent cost center
    print("\n3. Testing task creation with NON-EXISTENT cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Test Task - Non-existent",
                "operation_type": "deactivate",
                "namespace": "test-namespace",
                "cost_center": "non-existent-task-center",
                "schedule": "0 18 * * 1-5"  # 6 PM weekdays
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 403:
            data = response.json()
            if 'error' in data and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Task creation rejected with non-existent cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 403, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Create task without cost center
    print("\n4. Testing task creation WITHOUT cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Test Task - No Cost Center",
                "operation_type": "activate",
                "namespace": "test-namespace",
                "schedule": "0 9 * * 1-5"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            data = response.json()
            if 'error' in data and 'required' in data.get('error', '').lower():
                print("   ✓ Test passed: Task creation rejected without cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Create task with command operation type
    print("\n5. Testing task creation with COMMAND operation type...")
    try:
        response = requests.post(
            f"{base_url}/api/tasks",
            json={
                "title": "Test Task - Command",
                "operation_type": "command",
                "command": "get pods",
                "namespace": "default",
                "cost_center": "task-authorized",
                "schedule": "*/5 * * * *"  # Every 5 minutes
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get('id') and data.get('operation_type') == 'command':
                print("   ✓ Test passed: Command task created with authorized cost center")
            else:
                print(f"   ✗ Test failed: Task missing expected fields")
                return False
        else:
            print(f"   ✗ Test failed: Expected 201, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All task creation validation tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_task_creation_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
