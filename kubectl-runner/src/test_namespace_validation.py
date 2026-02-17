#!/usr/bin/env python3
"""
Test script for namespace activation/deactivation validation
Tests that cost center validation is enforced on both operations
"""

import requests
import json
import sys
import time

def test_namespace_operations_validation():
    """Test namespace activation and deactivation with cost center validation"""
    base_url = "http://localhost:8080"
    
    print("Testing Namespace Operations Validation")
    print("=" * 60)
    
    # Setup: Create test cost centers
    print("\nSetup: Creating test cost centers...")
    
    # Authorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/authorized-center/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created authorized-center: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create authorized-center: {e}")
    
    # Unauthorized cost center
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/unauthorized-center/permissions",
            json={
                "is_authorized": False,
                "max_concurrent_namespaces": 0,
                "authorized_namespaces": []
            }
        )
        print(f"   Created unauthorized-center: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create unauthorized-center: {e}")
    
    time.sleep(1)  # Give DynamoDB time to propagate
    
    # Test 1: Activate namespace with authorized cost center
    print("\n1. Testing activation with AUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "authorized-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✓ Test passed: Activation allowed with authorized cost center")
            else:
                print(f"   ✗ Test failed: Activation rejected: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Activate namespace with unauthorized cost center
    print("\n2. Testing activation with UNAUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "unauthorized-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            data = response.json()
            if not data.get('success') and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Activation rejected with unauthorized cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Deactivate namespace with authorized cost center
    print("\n3. Testing deactivation with AUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/deactivate",
            json={
                "cost_center": "authorized-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✓ Test passed: Deactivation allowed with authorized cost center")
            else:
                print(f"   ✗ Test failed: Deactivation rejected: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Deactivate namespace with unauthorized cost center
    print("\n4. Testing deactivation with UNAUTHORIZED cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/deactivate",
            json={
                "cost_center": "unauthorized-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            data = response.json()
            if not data.get('success') and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Deactivation rejected with unauthorized cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Activate namespace with non-existent cost center
    print("\n5. Testing activation with NON-EXISTENT cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/activate",
            json={
                "cost_center": "non-existent-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            data = response.json()
            if not data.get('success') and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Activation rejected with non-existent cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 6: Deactivate namespace with non-existent cost center
    print("\n6. Testing deactivation with NON-EXISTENT cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/namespaces/default/deactivate",
            json={
                "cost_center": "non-existent-center",
                "user_id": "test-user"
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            data = response.json()
            if not data.get('success') and 'not authorized' in data.get('error', '').lower():
                print("   ✓ Test passed: Deactivation rejected with non-existent cost center")
            else:
                print(f"   ✗ Test failed: Wrong error message: {data.get('error')}")
                return False
        else:
            print(f"   ✗ Test failed: Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All validation tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_namespace_operations_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
