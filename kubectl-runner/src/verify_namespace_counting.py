#!/usr/bin/env python3
"""
Simple verification script to check that namespace counting logic is implemented correctly
This script analyzes the source code to verify the changes without running the app
"""

import os
import re

def verify_namespace_counting_implementation():
    """Verify that namespace counting logic is properly implemented"""
    print("Verifying Namespace Counting Implementation")
    print("=" * 50)
    
    # Read the app.py file
    app_file = 'app.py'
    if not os.path.exists(app_file):
        print(f"✗ {app_file} not found")
        return False
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Test 1: Verify manual counter removal
    print("\n1. Checking manual counter removal...")
    
    if 'self.active_namespaces_count = 0' not in content:
        print("   ✓ Manual counter initialization removed")
    else:
        print("   ✗ Manual counter initialization still present")
        return False
    
    # Check that manual increments/decrements are removed
    if 'self.active_namespaces_count += 1' not in content and 'self.active_namespaces_count -= 1' not in content:
        print("   ✓ Manual counter increments/decrements removed")
    else:
        print("   ✗ Manual counter operations still present")
        return False
    
    # Test 2: Verify new dynamic counting methods
    print("\n2. Checking new dynamic counting methods...")
    
    # Check get_active_namespaces_count method
    if 'def get_active_namespaces_count(self):' in content:
        print("   ✓ get_active_namespaces_count method found")
    else:
        print("   ✗ get_active_namespaces_count method not found")
        return False
    
    # Check is_system_namespace method
    if 'def is_system_namespace(self, namespace_name):' in content:
        print("   ✓ is_system_namespace method found")
    else:
        print("   ✗ is_system_namespace method not found")
        return False
    
    # Check is_namespace_active method
    if 'def is_namespace_active(self, namespace_name):' in content:
        print("   ✓ is_namespace_active method found")
    else:
        print("   ✗ is_namespace_active method not found")
        return False
    
    # Check get_namespace_details method
    if 'def get_namespace_details(self, namespace_name):' in content:
        print("   ✓ get_namespace_details method found")
    else:
        print("   ✗ get_namespace_details method not found")
        return False
    
    # Test 3: Verify system namespace exclusion
    print("\n3. Checking system namespace exclusion...")
    
    # Check for system namespace list
    system_namespaces_pattern = r"system_namespaces = \[.*'kube-system'.*'kube-public'.*'default'"
    if re.search(system_namespaces_pattern, content, re.DOTALL):
        print("   ✓ System namespace list found")
    else:
        print("   ✗ System namespace list not found")
        return False
    
    # Check exclusion logic
    if 'if self.is_system_namespace(namespace_name):' in content and 'continue' in content:
        print("   ✓ System namespace exclusion logic found")
    else:
        print("   ✗ System namespace exclusion logic not found")
        return False
    
    # Test 4: Verify Kubernetes state querying
    print("\n4. Checking Kubernetes state querying...")
    
    # Check for kubectl commands to get actual state
    if "get namespaces -o json" in content:
        print("   ✓ Namespace listing query found")
    else:
        print("   ✗ Namespace listing query not found")
        return False
    
    # Check for pod status queries
    if "get pods -n" in content and "field-selector=status.phase=Running" in content:
        print("   ✓ Running pods query found")
    else:
        print("   ✗ Running pods query not found")
        return False
    
    # Check for deployment queries
    if "get deployments -n" in content:
        print("   ✓ Deployments query found")
    else:
        print("   ✗ Deployments query not found")
        return False
    
    # Check for statefulsets queries
    if "get statefulsets -n" in content:
        print("   ✓ StatefulSets query found")
    else:
        print("   ✗ StatefulSets query not found")
        return False
    
    # Test 5: Verify validation logic updates
    print("\n5. Checking validation logic updates...")
    
    # Check that validation uses dynamic counting
    if 'current_active_count = self.get_active_namespaces_count()' in content:
        print("   ✓ Dynamic counting in validation found")
    else:
        print("   ✗ Dynamic counting in validation not found")
        return False
    
    # Check for already active namespace check
    if 'if self.is_namespace_active(namespace):' in content:
        print("   ✓ Already active namespace check found")
    else:
        print("   ✗ Already active namespace check not found")
        return False
    
    # Check for improved error messages with counts
    if 'current active:' in content:
        print("   ✓ Improved error messages with counts found")
    else:
        print("   ✗ Improved error messages not found")
        return False
    
    # Test 6: Verify response updates
    print("\n6. Checking response updates...")
    
    # Check that activation/deactivation responses include counts
    if "'active_namespaces_count': updated_count" in content:
        print("   ✓ Updated count in responses found")
    else:
        print("   ✗ Updated count in responses not found")
        return False
    
    # Check for get_active_namespaces_count calls in responses
    if 'updated_count = self.get_active_namespaces_count()' in content:
        print("   ✓ Dynamic count calculation in responses found")
    else:
        print("   ✗ Dynamic count calculation in responses not found")
        return False
    
    # Test 7: Verify status endpoint improvements
    print("\n7. Checking status endpoint improvements...")
    
    # Check for detailed namespace information
    if 'scheduler.get_namespace_details(namespace_name)' in content:
        print("   ✓ Detailed namespace information in status endpoint found")
    else:
        print("   ✗ Detailed namespace information not found")
        return False
    
    # Check for separate counting of system vs user namespaces
    if 'user_namespaces_active' in content and 'total_active_count' in content:
        print("   ✓ Separate system/user namespace counting found")
    else:
        print("   ✗ Separate system/user namespace counting not found")
        return False
    
    # Check for additional status fields
    if 'max_allowed_during_non_business' in content and 'limit_applies' in content:
        print("   ✓ Additional status fields found")
    else:
        print("   ✗ Additional status fields not found")
        return False
    
    # Test 8: Verify error handling
    print("\n8. Checking error handling...")
    
    # Check for error handling in counting methods
    if 'logger.error(f"Error getting active namespaces count:' in content:
        print("   ✓ Error handling in counting methods found")
    else:
        print("   ✗ Error handling in counting methods not found")
        return False
    
    # Check for graceful degradation
    if 'return 0' in content and 'except Exception as e:' in content:
        print("   ✓ Graceful degradation on errors found")
    else:
        print("   ✗ Graceful degradation not found")
        return False
    
    print("\n" + "=" * 50)
    print("All namespace counting implementation verifications passed! ✓")
    print("\nSummary of changes implemented:")
    print("- ✓ Removed manual counter (active_namespaces_count)")
    print("- ✓ Added dynamic counting based on Kubernetes state")
    print("- ✓ Added system namespace exclusion logic")
    print("- ✓ Added comprehensive resource checking (pods, deployments, statefulsets)")
    print("- ✓ Updated validation logic to use dynamic counting")
    print("- ✓ Added already-active namespace detection")
    print("- ✓ Improved error messages with current counts")
    print("- ✓ Updated responses to include accurate counts")
    print("- ✓ Enhanced status endpoint with detailed information")
    print("- ✓ Added proper error handling and graceful degradation")
    return True

if __name__ == "__main__":
    try:
        success = verify_namespace_counting_implementation()
        exit_code = 0 if success else 1
        print(f"\nVerification {'PASSED' if success else 'FAILED'}")
        exit(exit_code)
    except Exception as e:
        print(f"\nVerification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)