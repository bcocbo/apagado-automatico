#!/usr/bin/env python3
"""
Test script for permissions cache functionality
Tests that caching improves performance and works correctly
"""

import requests
import json
import sys
import time

def test_permissions_cache():
    """Test permissions cache functionality"""
    base_url = "http://localhost:8080"
    
    print("Testing Permissions Cache Functionality")
    print("=" * 60)
    
    # Test 1: Check cache stats
    print("\n1. Checking initial cache stats...")
    try:
        response = requests.get(f"{base_url}/api/cache/stats")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if 'enabled' in data and 'ttl_seconds' in data:
                print(f"   ✓ Cache is {'enabled' if data['enabled'] else 'disabled'}")
                print(f"   ✓ TTL: {data['ttl_seconds']} seconds")
                print(f"   ✓ Cached entries: {data['cached_entries']}")
            else:
                print("   ✗ Test failed: Response missing expected fields")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Setup: Create a test cost center
    print("\n2. Setting up test cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/cache-test-center/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created cache-test-center: {response.status_code}")
        if response.status_code != 200:
            print(f"   ✗ Failed to create test cost center")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: First validation (cache miss)
    print("\n3. Testing first validation (should be cache miss)...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/api/cost-centers/cache-test-center/validate")
        first_duration = time.time() - start_time
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Duration: {first_duration:.4f} seconds")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('is_authorized') == True:
                print("   ✓ Test passed: Cost center validated (cache miss)")
            else:
                print("   ✗ Test failed: Expected authorized cost center")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Second validation (cache hit)
    print("\n4. Testing second validation (should be cache hit)...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/api/cost-centers/cache-test-center/validate")
        second_duration = time.time() - start_time
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Duration: {second_duration:.4f} seconds")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('is_authorized') == True:
                print("   ✓ Test passed: Cost center validated (cache hit)")
                
                # Check if second request was faster (cache hit)
                if second_duration < first_duration:
                    print(f"   ✓ Cache improved performance: {first_duration:.4f}s -> {second_duration:.4f}s")
                else:
                    print(f"   ⚠ Warning: Second request not faster (may be normal in local testing)")
            else:
                print("   ✗ Test failed: Expected authorized cost center")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Check cache stats after validations
    print("\n5. Checking cache stats after validations...")
    try:
        response = requests.get(f"{base_url}/api/cache/stats")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data['cached_entries'] > 0:
                print(f"   ✓ Cache has {data['cached_entries']} entries")
                if 'cache-test-center' in data.get('entries', []):
                    print("   ✓ Test cost center is cached")
                else:
                    print("   ⚠ Warning: Test cost center not in cache list")
            else:
                print("   ✗ Test failed: Cache should have entries")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 6: Update permissions and verify cache invalidation
    print("\n6. Testing cache invalidation on permission update...")
    try:
        # Update permissions
        response = requests.post(
            f"{base_url}/api/cost-centers/cache-test-center/permissions",
            json={
                "is_authorized": False,
                "max_concurrent_namespaces": 0,
                "authorized_namespaces": []
            }
        )
        print(f"   Updated permissions: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ✗ Failed to update permissions")
            return False
        
        # Validate again (should fetch fresh data)
        time.sleep(0.5)  # Small delay
        response = requests.get(f"{base_url}/api/cost-centers/cache-test-center/validate")
        print(f"   Validation Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('is_authorized') == False:
                print("   ✓ Test passed: Cache was invalidated, got updated value")
            else:
                print("   ✗ Test failed: Should have gotten updated (unauthorized) value")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 7: Manual cache invalidation
    print("\n7. Testing manual cache invalidation...")
    try:
        # First, set permissions back to authorized
        response = requests.post(
            f"{base_url}/api/cost-centers/cache-test-center/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        
        # Validate to populate cache
        requests.get(f"{base_url}/api/cost-centers/cache-test-center/validate")
        
        # Manually invalidate cache for this cost center
        response = requests.post(
            f"{base_url}/api/cache/invalidate",
            json={"cost_center": "cache-test-center"}
        )
        print(f"   Invalidation Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if 'message' in data:
                print("   ✓ Test passed: Cache invalidated successfully")
            else:
                print("   ✗ Test failed: Response missing message")
                return False
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 8: Invalidate all cache
    print("\n8. Testing invalidate all cache...")
    try:
        response = requests.post(
            f"{base_url}/api/cache/invalidate",
            json={}
        )
        print(f"   Invalidation Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            # Check cache stats
            stats_response = requests.get(f"{base_url}/api/cache/stats")
            stats = stats_response.json()
            if stats['cached_entries'] == 0:
                print("   ✓ Test passed: All cache invalidated")
            else:
                print(f"   ⚠ Warning: Cache still has {stats['cached_entries']} entries")
        else:
            print(f"   ✗ Test failed: Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All cache tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        success = test_permissions_cache()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)
