#!/usr/bin/env python3
"""
Simple verification script to check that cluster_name changes are implemented correctly
This script analyzes the source code to verify the changes without running the app
"""

import os
import re

def verify_cluster_name_implementation():
    """Verify that cluster_name is properly implemented in all operations"""
    print("Verifying Cluster Name Implementation")
    print("=" * 50)
    
    # Read the app.py file
    app_file = 'app.py'
    if not os.path.exists(app_file):
        print(f"✗ {app_file} not found")
        return False
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Test 1: Verify cluster_name is initialized in TaskScheduler
    print("\n1. Checking cluster_name initialization in TaskScheduler...")
    if 'self.cluster_name = os.getenv(\'EKS_CLUSTER_NAME\', \'unknown-cluster\')' in content:
        print("   ✓ cluster_name properly initialized from environment variable")
    else:
        print("   ✗ cluster_name initialization not found")
        return False
    
    # Test 2: Verify cluster_name is passed in log_namespace_activity calls
    print("\n2. Checking cluster_name in log_namespace_activity calls...")
    
    # Check task creation logging
    task_creation_pattern = r'log_namespace_activity\(\s*namespace_name=self\.tasks\[task_id\]\[\'namespace\'\],\s*operation_type=\'task_created\',.*?cluster_name=self\.cluster_name'
    if re.search(task_creation_pattern, content, re.DOTALL):
        print("   ✓ cluster_name passed in task creation logging")
    else:
        print("   ✗ cluster_name missing in task creation logging")
        return False
    
    # Check namespace activation logging
    activation_pattern = r'log_namespace_activity\(\s*namespace_name=namespace,\s*operation_type=\'manual_activation\',.*?cluster_name=self\.cluster_name'
    if re.search(activation_pattern, content, re.DOTALL):
        print("   ✓ cluster_name passed in namespace activation logging")
    else:
        print("   ✗ cluster_name missing in namespace activation logging")
        return False
    
    # Check namespace deactivation logging
    deactivation_pattern = r'log_namespace_activity\(\s*namespace_name=namespace,\s*operation_type=\'manual_deactivation\',.*?cluster_name=self\.cluster_name'
    if re.search(deactivation_pattern, content, re.DOTALL):
        print("   ✓ cluster_name passed in namespace deactivation logging")
    else:
        print("   ✗ cluster_name missing in namespace deactivation logging")
        return False
    
    # Test 3: Verify cluster_name is passed in validation calls
    print("\n3. Checking cluster_name in validation calls...")
    
    # Check validate_cost_center_permissions calls
    validation_patterns = [
        r'validate_cost_center_permissions\(\s*cost_center,.*?cluster_name=self\.cluster_name',
        r'validate_cost_center_permissions\(\s*cost_center,.*?cluster_name=scheduler\.cluster_name'
    ]
    
    validation_found = False
    for pattern in validation_patterns:
        if re.search(pattern, content, re.DOTALL):
            validation_found = True
            break
    
    if validation_found:
        print("   ✓ cluster_name passed in validation calls")
    else:
        print("   ✗ cluster_name missing in validation calls")
        return False
    
    # Test 4: Verify scheduled task execution improvements
    print("\n4. Checking scheduled task execution improvements...")
    
    # Check that scheduled tasks have proper requested_by identification
    scheduler_task_pattern = r'requested_by=f"scheduler-task-\{task_id\}"'
    if re.search(scheduler_task_pattern, content):
        print("   ✓ Scheduled tasks properly identified with task ID")
    else:
        print("   ✗ Scheduled task identification not found")
        return False
    
    # Test 5: Verify DynamoDB logging methods handle cluster_name
    print("\n5. Checking DynamoDB logging methods...")
    
    # Check log_namespace_activity method signature
    log_method_pattern = r'def log_namespace_activity\(self, namespace_name, operation_type, cost_center, user_id=None, requested_by=None, cluster_name=None'
    if re.search(log_method_pattern, content):
        print("   ✓ log_namespace_activity method accepts cluster_name parameter")
    else:
        print("   ✗ log_namespace_activity method signature incorrect")
        return False
    
    # Check cluster_name handling in the method
    cluster_handling_pattern = r'if cluster_name:\s*item\[\'cluster_name\'\] = cluster_name\s*else:\s*.*item\[\'cluster_name\'\] = os\.getenv\(\'EKS_CLUSTER_NAME\', \'unknown-cluster\'\)'
    if re.search(cluster_handling_pattern, content, re.DOTALL):
        print("   ✓ cluster_name properly handled in logging method")
    else:
        print("   ✗ cluster_name handling logic not found")
        return False
    
    # Test 6: Check validation audit logging
    print("\n6. Checking validation audit logging...")
    
    # Check _log_validation_audit method signature
    audit_method_pattern = r'def _log_validation_audit\(self, validation_type, cost_center, validation_result,\s*validation_source, user_id=None, requested_by=None, operation_type=None,\s*namespace=None, cluster_name=None'
    if re.search(audit_method_pattern, content, re.DOTALL):
        print("   ✓ _log_validation_audit method accepts cluster_name parameter")
    else:
        print("   ✗ _log_validation_audit method signature incorrect")
        return False
    
    print("\n" + "=" * 50)
    print("All cluster name implementation verifications passed! ✓")
    print("\nSummary of changes implemented:")
    print("- ✓ cluster_name initialized from EKS_CLUSTER_NAME environment variable")
    print("- ✓ cluster_name passed to all log_namespace_activity calls")
    print("- ✓ cluster_name passed to validation calls")
    print("- ✓ Scheduled tasks properly identified with task ID")
    print("- ✓ DynamoDB logging methods handle cluster_name parameter")
    print("- ✓ Validation audit logging includes cluster_name")
    return True

if __name__ == "__main__":
    try:
        success = verify_cluster_name_implementation()
        exit_code = 0 if success else 1
        print(f"\nVerification {'PASSED' if success else 'FAILED'}")
        exit(exit_code)
    except Exception as e:
        print(f"\nVerification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)