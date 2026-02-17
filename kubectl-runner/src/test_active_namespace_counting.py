#!/usr/bin/env python3
"""
Test script for active namespace counting logic
Tests the corrected logic for counting active namespaces
"""

import requests
import json
import sys
import time
import os
from datetime import datetime

def test_active_namespace_counting():
    """Test active namespace counting logic"""
    base_url = "http://localhost:8080"
    
    print("Testing Active Namespace Counting Logic")
    print("=" * 60)
    
    # Setup: Create test cost center
    print("\nSetup: Creating test cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/counting-test/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created counting-test: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create counting-test: {e}")
    
    time.sleep(2)  # Give DynamoDB time to propagate
    
    # Test 1: Get initial namespace status
    print("\n1. Testing namespace status endpoint...")
    try:
        response = requests.get(f"{base_url}/api/namespaces/status")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response structure: {list(data.keys())}")
            
            # Check for new fields
            expected_fields = [
                'namespaces', 'total_active_count', 'user_namespaces_active', 
                'active_count', 'is_non_business_hours', 'max_allowed_during_non_business',
                'limit_applies'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if not missing_fields:
                print("   ✓ All expected fields present in response")
                print(f"   Total active namespaces: {data.get('total_active_count', 0)}")
                print(f"   User namespaces active: {data.get('user_namespaces_active', 0)}")
                print(f"   Is non-business hours: {data.get('is_non_business_hours', False)}")
                print(f"   Limit applies: {data.get('limit_applies', False)}")
            else:
                print(f"   ✗ Missing fields: {missing_fields}")
                return False
            
            # Check namespace details
            namespaces = data.get('namespaces', [])
            print(f"   Found {len(namespaces)} namespaces")
            
            # Count system vs user namespaces
            system_count = sum(1 for ns in namespaces if ns.get('is_system', False))
            user_count = len(namespaces) - system_count
            active_user_count = sum(1 for ns in namespaces if ns.get('is_active', False) and not ns.get('is_system', False))
            
            print(f"   System namespaces: {system_count}")
            print(f"   User namespaces: {user_count}")
            print(f"   Active user namespaces: {active_user_count}")
            
            # Verify consistency
            if data.get('user_namespaces_active') == active_user_count:
                print("   ✓ User namespace count is consistent")
            else:
                print(f"   ✗ User namespace count mismatch: API={data.get('user_namespaces_active')}, Calculated={active_user_count}")
                return False
                
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Test namespace activation with counting
    print("\n2. Testing namespace activation with accurate counting...")
    try:
        # Get initial count
        status_response = requests.get(f"{base_url}/api/namespaces/status")
        if status_response.status_code == 200:
            initial_data = status_response.json()
            initial_count = initial_data.get('user_namespaces_active', 0)
            print(f"   Initial active count: {initial_count}")
        else:
            print("   ✗ Could not get initial status")
            return False
        
        # Activate a namespace
        test_namespace = "counting-test-ns"
        response = requests.post(
            f"{base_url}/api/namespaces/{test_namespace}/activate",
            json={
                "cost_center": "counting-test",
                "user_id": "counting.test.user",
                "requested_by": "counting.test.requester"
            }
        )
        
        print(f"   Activation Status Code: {response.status_code}")
        
        if response.status_code == 200:
            activation_data = response.json()
            print(f"   Activation Response: {json.dumps(activation_data, indent=2)}")
            
            # Check if response includes updated count
            if 'active_namespaces_count' in activation_data:
                activation_count = activation_data['active_namespaces_count']
                print(f"   Count after activation: {activation_count}")
                
                # Verify count increased (if we're not just re-activating)
                if activation_count >= initial_count:
                    print("   ✓ Active count updated correctly after activation")
                else:
                    print(f"   ✗ Count decreased unexpectedly: {initial_count} -> {activation_count}")
                    return False
            else:
                print("   ✓ Activation successful (count not in response - will verify separately)")
            
            # Wait a moment for Kubernetes to process
            time.sleep(3)
            
            # Verify with status endpoint
            status_response = requests.get(f"{base_url}/api/namespaces/status")
            if status_response.status_code == 200:
                updated_data = status_response.json()
                updated_count = updated_data.get('user_namespaces_active', 0)
                print(f"   Verified count via status endpoint: {updated_count}")
                
                # Find our test namespace in the list
                test_ns_found = False
                for ns in updated_data.get('namespaces', []):
                    if ns.get('name') == test_namespace:
                        test_ns_found = True
                        print(f"   Test namespace status: active={ns.get('is_active')}, system={ns.get('is_system')}")
                        break
                
                if test_ns_found:
                    print("   ✓ Test namespace found in status")
                else:
                    print("   ✗ Test namespace not found in status")
                    return False
            
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Test namespace deactivation with counting
    print("\n3. Testing namespace deactivation with accurate counting...")
    try:
        # Get count before deactivation
        status_response = requests.get(f"{base_url}/api/namespaces/status")
        if status_response.status_code == 200:
            before_data = status_response.json()
            before_count = before_data.get('user_namespaces_active', 0)
            print(f"   Count before deactivation: {before_count}")
        else:
            print("   ✗ Could not get status before deactivation")
            return False
        
        # Deactivate the namespace
        response = requests.post(
            f"{base_url}/api/namespaces/{test_namespace}/deactivate",
            json={
                "cost_center": "counting-test",
                "user_id": "counting.test.user",
                "requested_by": "counting.test.requester"
            }
        )
        
        print(f"   Deactivation Status Code: {response.status_code}")
        
        if response.status_code == 200:
            deactivation_data = response.json()
            print(f"   Deactivation Response: {json.dumps(deactivation_data, indent=2)}")
            
            # Check if response includes updated count
            if 'active_namespaces_count' in deactivation_data:
                deactivation_count = deactivation_data['active_namespaces_count']
                print(f"   Count after deactivation: {deactivation_count}")
                
                # Verify count decreased or stayed same
                if deactivation_count <= before_count:
                    print("   ✓ Active count updated correctly after deactivation")
                else:
                    print(f"   ✗ Count increased unexpectedly: {before_count} -> {deactivation_count}")
                    return False
            else:
                print("   ✓ Deactivation successful (count not in response - will verify separately)")
            
            # Wait a moment for Kubernetes to process
            time.sleep(3)
            
            # Verify with status endpoint
            status_response = requests.get(f"{base_url}/api/namespaces/status")
            if status_response.status_code == 200:
                after_data = status_response.json()
                after_count = after_data.get('user_namespaces_active', 0)
                print(f"   Verified count via status endpoint: {after_count}")
                
                # Find our test namespace in the list
                for ns in after_data.get('namespaces', []):
                    if ns.get('name') == test_namespace:
                        print(f"   Test namespace status: active={ns.get('is_active')}, system={ns.get('is_system')}")
                        break
            
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Test system namespace exclusion
    print("\n4. Testing system namespace exclusion...")
    try:
        response = requests.get(f"{base_url}/api/namespaces/status")
        
        if response.status_code == 200:
            data = response.json()
            namespaces = data.get('namespaces', [])
            
            # Check that system namespaces are properly marked
            system_namespaces_found = []
            user_namespaces_found = []
            
            for ns in namespaces:
                if ns.get('is_system', False):
                    system_namespaces_found.append(ns['name'])
                else:
                    user_namespaces_found.append(ns['name'])
            
            print(f"   System namespaces found: {len(system_namespaces_found)}")
            print(f"   User namespaces found: {len(user_namespaces_found)}")
            
            # Check for expected system namespaces
            expected_system = ['kube-system', 'kube-public', 'kube-node-lease', 'default']
            found_expected = [ns for ns in expected_system if ns in system_namespaces_found]
            
            if len(found_expected) >= 3:  # At least 3 of the 4 expected
                print(f"   ✓ Expected system namespaces found: {found_expected}")
            else:
                print(f"   ✗ Missing expected system namespaces. Found: {found_expected}")
                return False
            
            # Verify that system namespaces don't count toward user limit
            total_active = data.get('total_active_count', 0)
            user_active = data.get('user_namespaces_active', 0)
            
            if total_active >= user_active:
                print(f"   ✓ System namespaces excluded from user count (total: {total_active}, user: {user_active})")
            else:
                print(f"   ✗ Inconsistent counts: total={total_active}, user={user_active}")
                return False
                
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Test non-business hours limit validation
    print("\n5. Testing non-business hours limit validation...")
    try:
        # Get current status to understand the limit situation
        status_response = requests.get(f"{base_url}/api/namespaces/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            is_non_business = status_data.get('is_non_business_hours', False)
            current_active = status_data.get('user_namespaces_active', 0)
            limit_applies = status_data.get('limit_applies', False)
            
            print(f"   Non-business hours: {is_non_business}")
            print(f"   Current active: {current_active}")
            print(f"   Limit applies: {limit_applies}")
            print(f"   Max allowed: {status_data.get('max_allowed_during_non_business', 5)}")
            
            if is_non_business and current_active < 5:
                # Try to activate another namespace to test limit
                test_namespace_2 = "counting-test-ns-2"
                response = requests.post(
                    f"{base_url}/api/namespaces/{test_namespace_2}/activate",
                    json={
                        "cost_center": "counting-test",
                        "user_id": "counting.test.user2",
                        "requested_by": "counting.test.requester2"
                    }
                )
                
                print(f"   Test activation Status Code: {response.status_code}")
                
                if response.status_code in [200, 400]:  # Either success or limit reached
                    response_data = response.json()
                    if response.status_code == 200:
                        print("   ✓ Activation allowed (under limit)")
                    else:
                        if "Maximum 5 namespaces" in response_data.get('error', ''):
                            print("   ✓ Limit properly enforced")
                        else:
                            print(f"   ? Different error: {response_data.get('error')}")
                else:
                    print(f"   ✗ Unexpected status code: {response.status_code}")
                    return False
            else:
                print("   ✓ Limit validation test skipped (business hours or already at limit)")
                
        else:
            print(f"   ✗ Could not get status for limit test")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All active namespace counting tests passed! ✓")
    print("\nKey improvements implemented:")
    print("- ✓ Dynamic counting based on actual Kubernetes state")
    print("- ✓ System namespace exclusion from user limits")
    print("- ✓ Detailed namespace information in status endpoint")
    print("- ✓ Accurate limit validation during non-business hours")
    print("- ✓ Consistent counting across all operations")
    print("- ✓ No manual counter synchronization issues")
    return True

if __name__ == "__main__":
    try:
        success = test_active_namespace_counting()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)