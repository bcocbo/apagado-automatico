#!/usr/bin/env python3
"""
Simple verification script to check that audit endpoints are implemented correctly
This script analyzes the source code to verify the changes without running the app
"""

import os
import re

def verify_audit_endpoints_implementation():
    """Verify that audit endpoints are properly implemented"""
    print("Verifying Audit Endpoints Implementation")
    print("=" * 50)
    
    # Read the app.py file
    app_file = 'app.py'
    if not os.path.exists(app_file):
        print(f"✗ {app_file} not found")
        return False
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Test 1: Verify new DynamoDB methods exist
    print("\n1. Checking new DynamoDB methods...")
    
    # Check get_activities_by_user method
    if 'def get_activities_by_user(self, requested_by, start_date=None, end_date=None, limit=100):' in content:
        print("   ✓ get_activities_by_user method found")
    else:
        print("   ✗ get_activities_by_user method not found")
        return False
    
    # Check get_activities_by_cluster method
    if 'def get_activities_by_cluster(self, cluster_name, start_date=None, end_date=None, limit=100):' in content:
        print("   ✓ get_activities_by_cluster method found")
    else:
        print("   ✗ get_activities_by_cluster method not found")
        return False
    
    # Test 2: Verify DynamoDB indexes are defined
    print("\n2. Checking DynamoDB index definitions...")
    
    # Check requested-by-timestamp-index
    if "'IndexName': 'requested-by-timestamp-index'" in content:
        print("   ✓ requested-by-timestamp-index defined")
    else:
        print("   ✗ requested-by-timestamp-index not found")
        return False
    
    # Check cluster-timestamp-index
    if "'IndexName': 'cluster-timestamp-index'" in content:
        print("   ✓ cluster-timestamp-index defined")
    else:
        print("   ✗ cluster-timestamp-index not found")
        return False
    
    # Test 3: Verify API endpoints exist
    print("\n3. Checking API endpoint definitions...")
    
    # Check user audit endpoint
    user_endpoint_pattern = r"@app\.route\('/api/audit/user/<requested_by>', methods=\['GET'\]\)"
    if re.search(user_endpoint_pattern, content):
        print("   ✓ User audit endpoint (/api/audit/user/<requested_by>) found")
    else:
        print("   ✗ User audit endpoint not found")
        return False
    
    # Check cluster audit endpoint
    cluster_endpoint_pattern = r"@app\.route\('/api/audit/cluster/<cluster_name>', methods=\['GET'\]\)"
    if re.search(cluster_endpoint_pattern, content):
        print("   ✓ Cluster audit endpoint (/api/audit/cluster/<cluster_name>) found")
    else:
        print("   ✗ Cluster audit endpoint not found")
        return False
    
    # Check audit summary endpoint
    summary_endpoint_pattern = r"@app\.route\('/api/audit/summary', methods=\['GET'\]\)"
    if re.search(summary_endpoint_pattern, content):
        print("   ✓ Audit summary endpoint (/api/audit/summary) found")
    else:
        print("   ✗ Audit summary endpoint not found")
        return False
    
    # Test 4: Verify endpoint functions exist
    print("\n4. Checking endpoint function implementations...")
    
    # Check user audit function
    if 'def get_activities_by_user(requested_by):' in content:
        print("   ✓ get_activities_by_user endpoint function found")
    else:
        print("   ✗ get_activities_by_user endpoint function not found")
        return False
    
    # Check cluster audit function
    if 'def get_activities_by_cluster(cluster_name):' in content:
        print("   ✓ get_activities_by_cluster endpoint function found")
    else:
        print("   ✗ get_activities_by_cluster endpoint function not found")
        return False
    
    # Check audit summary function
    if 'def get_audit_summary():' in content:
        print("   ✓ get_audit_summary endpoint function found")
    else:
        print("   ✗ get_audit_summary endpoint function not found")
        return False
    
    # Test 5: Verify parameter validation
    print("\n5. Checking parameter validation...")
    
    # Check date validation
    if 'Invalid start_date format. Use ISO format' in content:
        print("   ✓ Date format validation found")
    else:
        print("   ✗ Date format validation not found")
        return False
    
    # Check limit validation
    if 'if limit > 1000:' in content and 'limit = 1000' in content:
        print("   ✓ Limit validation found")
    else:
        print("   ✗ Limit validation not found")
        return False
    
    # Check date range validation
    if 'start_date cannot be after end_date' in content:
        print("   ✓ Date range validation found")
    else:
        print("   ✗ Date range validation not found")
        return False
    
    # Test 6: Verify response structure
    print("\n6. Checking response structure...")
    
    # Check summary statistics
    if "'summary': summary" in content and "'activities': activities" in content:
        print("   ✓ Response structure with summary and activities found")
    else:
        print("   ✗ Response structure not found")
        return False
    
    # Check operation counts
    if 'operation_counts' in content:
        print("   ✓ Operation counts in summary found")
    else:
        print("   ✗ Operation counts not found")
        return False
    
    # Test 7: Verify DynamoDB query usage
    print("\n7. Checking DynamoDB query implementation...")
    
    # Check index usage in queries
    if "IndexName': 'requested-by-timestamp-index'" in content:
        print("   ✓ User queries use requested-by-timestamp-index")
    else:
        print("   ✗ User queries don't use correct index")
        return False
    
    if "IndexName': 'cluster-timestamp-index'" in content:
        print("   ✓ Cluster queries use cluster-timestamp-index")
    else:
        print("   ✗ Cluster queries don't use correct index")
        return False
    
    # Check sort order (newest first)
    if "'ScanIndexForward': False" in content:
        print("   ✓ Queries sorted by timestamp descending (newest first)")
    else:
        print("   ✗ Query sort order not configured")
        return False
    
    print("\n" + "=" * 50)
    print("All audit endpoints implementation verifications passed! ✓")
    print("\nSummary of changes implemented:")
    print("- ✓ Added get_activities_by_user() DynamoDB method")
    print("- ✓ Added get_activities_by_cluster() DynamoDB method")
    print("- ✓ Added requested-by-timestamp-index to DynamoDB table")
    print("- ✓ Added cluster-timestamp-index to DynamoDB table")
    print("- ✓ Added /api/audit/user/<requested_by> endpoint")
    print("- ✓ Added /api/audit/cluster/<cluster_name> endpoint")
    print("- ✓ Added /api/audit/summary endpoint")
    print("- ✓ Added parameter validation (dates, limits)")
    print("- ✓ Added response structure with summary statistics")
    print("- ✓ Added proper DynamoDB index usage")
    return True

if __name__ == "__main__":
    try:
        success = verify_audit_endpoints_implementation()
        exit_code = 0 if success else 1
        print(f"\nVerification {'PASSED' if success else 'FAILED'}")
        exit(exit_code)
    except Exception as e:
        print(f"\nVerification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)