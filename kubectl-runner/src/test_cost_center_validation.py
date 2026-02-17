#!/usr/bin/env python3
"""
Test script for cost center validation endpoint
"""

import requests
import json
import sys

def test_validate_cost_center_endpoint():
    """Test the cost center validation endpoint"""
    base_url = "http://localhost:8080"
    
    print("Testing Cost Center Validation Endpoint")
    print("=" * 50)
    
    # Test 1: Validate an authorized cost center
    print("\n1. Testing authorized cost center...")
    try:
        response = requests.get(f"{base_url}/api/cost-centers/development/validate")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if 'is_authorized' in data and 'cost_center' in data:
                print("   ✓ Test passed: Response has expected structure")
            else:
                print("   ✗ Test failed: Response missing expected fields")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Validate a non-existent cost center
    print("\n2. Testing non-existent cost center...")
    try:
        response = requests.get(f"{base_url}/api/cost-centers/nonexistent/validate")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('is_authorized') == False:
                print("   ✓ Test passed: Non-existent cost center returns unauthorized")
            else:
                print("   ✗ Test failed: Non-existent cost center should be unauthorized")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Set permissions and validate
    print("\n3. Testing set permissions and validate...")
    try:
        # Set permissions
        set_response = requests.post(
            f"{base_url}/api/cost-centers/test-center/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 3,
                "authorized_namespaces": ["test-ns-1", "test-ns-2"]
            }
        )
        print(f"   Set Permissions Status: {set_response.status_code}")
        
        if set_response.status_code != 200:
            print(f"   ✗ Failed to set permissions: {set_response.text}")
            return False
        
        # Validate the newly set permissions
        validate_response = requests.get(f"{base_url}/api/cost-centers/test-center/validate")
        print(f"   Validate Status: {validate_response.status_code}")
        print(f"   Response: {json.dumps(validate_response.json(), indent=2)}")
        
        if validate_response.status_code == 200:
            data = validate_response.json()
            if data.get('is_authorized') == True and data.get('details'):
                details = data['details']
                if (details.get('max_concurrent_namespaces') == 3 and 
                    len(details.get('authorized_namespaces', [])) == 2):
                    print("   ✓ Test passed: Permissions set and validated correctly")
                else:
                    print("   ✗ Test failed: Details don't match set permissions")
                    return False
            else:
                print("   ✗ Test failed: Expected authorized with details")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {validate_response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_validate_cost_center_endpoint()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
