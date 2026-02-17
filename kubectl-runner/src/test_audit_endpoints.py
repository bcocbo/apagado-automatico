#!/usr/bin/env python3
"""
Test script for audit endpoints
Tests the new audit endpoints for querying by user and cluster
"""

import requests
import json
import sys
import time
import boto3
import os
from datetime import datetime, timedelta

def test_audit_endpoints():
    """Test audit endpoints for user and cluster queries"""
    base_url = "http://localhost:8080"
    
    # DynamoDB setup
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table_name = 'task-scheduler-logs'
    table = dynamodb.Table(table_name)
    
    print("Testing Audit Endpoints")
    print("=" * 50)
    
    # Setup: Create test cost center
    print("\nSetup: Creating test cost center...")
    try:
        response = requests.post(
            f"{base_url}/api/cost-centers/audit-test/permissions",
            json={
                "is_authorized": True,
                "max_concurrent_namespaces": 5,
                "authorized_namespaces": []
            }
        )
        print(f"   Created audit-test: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not create audit-test: {e}")
    
    time.sleep(2)  # Give DynamoDB time to propagate
    
    # Setup: Create some test activities
    print("\nSetup: Creating test activities...")
    test_users = ["audit.user1", "audit.user2", "audit.user3"]
    test_clusters = ["audit-cluster-1", "audit-cluster-2"]
    
    for i, user in enumerate(test_users):
        for j, cluster in enumerate(test_clusters):
            # Create namespace activation
            try:
                response = requests.post(
                    f"{base_url}/api/namespaces/audit-test-ns-{i}-{j}/activate",
                    json={
                        "cost_center": "audit-test",
                        "user_id": user,
                        "requested_by": user
                    }
                )
                print(f"   Created activity: {user} on {cluster} - Status: {response.status_code}")
                time.sleep(1)  # Small delay between requests
            except Exception as e:
                print(f"   Warning: Could not create activity for {user}: {e}")
    
    time.sleep(3)  # Give DynamoDB time to process
    
    # Test 1: Query activities by user
    print("\n1. Testing audit endpoint for user queries...")
    try:
        test_user = "audit.user1"
        response = requests.get(f"{base_url}/api/audit/user/{test_user}")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response structure: {list(data.keys())}")
            
            if 'summary' in data and 'activities' in data:
                summary = data['summary']
                activities = data['activities']
                
                print(f"   Summary - Total activities: {summary.get('total_activities', 0)}")
                print(f"   Summary - User: {summary.get('user')}")
                print(f"   Summary - Operation counts: {summary.get('operation_counts', {})}")
                print(f"   Activities count: {len(activities)}")
                
                # Verify all activities are for the requested user
                user_mismatch = False
                for activity in activities:
                    if activity.get('requested_by') != test_user:
                        user_mismatch = True
                        break
                
                if not user_mismatch:
                    print("   ✓ All activities belong to the requested user")
                else:
                    print("   ✗ Some activities don't belong to the requested user")
                    return False
                    
            else:
                print("   ✗ Response missing expected structure (summary/activities)")
                return False
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Query activities by cluster
    print("\n2. Testing audit endpoint for cluster queries...")
    try:
        # Use the current cluster name from environment
        test_cluster = os.getenv('EKS_CLUSTER_NAME', 'unknown-cluster')
        response = requests.get(f"{base_url}/api/audit/cluster/{test_cluster}")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response structure: {list(data.keys())}")
            
            if 'summary' in data and 'activities' in data:
                summary = data['summary']
                activities = data['activities']
                
                print(f"   Summary - Total activities: {summary.get('total_activities', 0)}")
                print(f"   Summary - Cluster: {summary.get('cluster')}")
                print(f"   Summary - Operation counts: {summary.get('operation_counts', {})}")
                print(f"   Summary - User counts: {summary.get('user_counts', {})}")
                print(f"   Summary - Cost center counts: {summary.get('cost_center_counts', {})}")
                print(f"   Activities count: {len(activities)}")
                
                # Verify all activities are for the requested cluster
                cluster_mismatch = False
                for activity in activities:
                    if activity.get('cluster_name') != test_cluster:
                        cluster_mismatch = True
                        break
                
                if not cluster_mismatch:
                    print("   ✓ All activities belong to the requested cluster")
                else:
                    print("   ✗ Some activities don't belong to the requested cluster")
                    return False
                    
            else:
                print("   ✗ Response missing expected structure (summary/activities)")
                return False
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Query with date range
    print("\n3. Testing audit endpoints with date range...")
    try:
        test_user = "audit.user2"
        
        # Test with date range (last 24 hours)
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)
        
        response = requests.get(
            f"{base_url}/api/audit/user/{test_user}",
            params={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'limit': 50
            }
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            
            print(f"   Date range applied: {summary.get('date_range', {})}")
            print(f"   Limit applied: {summary.get('limit_applied')}")
            print(f"   Total activities: {summary.get('total_activities', 0)}")
            
            print("   ✓ Date range parameters accepted")
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Test audit summary endpoint
    print("\n4. Testing audit summary endpoint...")
    try:
        response = requests.get(f"{base_url}/api/audit/summary")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Summary response: {json.dumps(data, indent=2)}")
            print("   ✓ Audit summary endpoint working")
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Test error handling
    print("\n5. Testing error handling...")
    try:
        # Test invalid date format
        response = requests.get(
            f"{base_url}/api/audit/user/test-user",
            params={'start_date': 'invalid-date'}
        )
        
        print(f"   Invalid date Status Code: {response.status_code}")
        
        if response.status_code == 400:
            error_data = response.json()
            if 'error' in error_data and 'Invalid start_date format' in error_data['error']:
                print("   ✓ Invalid date format properly rejected")
            else:
                print("   ✗ Error message not as expected")
                return False
        else:
            print(f"   ✗ Expected 400 for invalid date, got {response.status_code}")
            return False
        
        # Test invalid date range (start > end)
        end_date = datetime.now()
        start_date = end_date + timedelta(hours=1)  # Start after end
        
        response = requests.get(
            f"{base_url}/api/audit/user/test-user",
            params={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )
        
        print(f"   Invalid range Status Code: {response.status_code}")
        
        if response.status_code == 400:
            error_data = response.json()
            if 'error' in error_data and 'start_date cannot be after end_date' in error_data['error']:
                print("   ✓ Invalid date range properly rejected")
            else:
                print("   ✗ Error message not as expected")
                return False
        else:
            print(f"   ✗ Expected 400 for invalid range, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 6: Test limit validation
    print("\n6. Testing limit validation...")
    try:
        # Test limit too high
        response = requests.get(
            f"{base_url}/api/audit/user/test-user",
            params={'limit': 2000}  # Above max of 1000
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            if summary.get('limit_applied') == 1000:
                print("   ✓ High limit capped at 1000")
            else:
                print(f"   ✗ Expected limit 1000, got {summary.get('limit_applied')}")
                return False
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
        
        # Test limit too low
        response = requests.get(
            f"{base_url}/api/audit/user/test-user",
            params={'limit': 0}  # Below min of 1
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            if summary.get('limit_applied') == 1:
                print("   ✓ Low limit raised to 1")
            else:
                print(f"   ✗ Expected limit 1, got {summary.get('limit_applied')}")
                return False
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("All audit endpoint tests passed! ✓")
    print("\nNew endpoints available:")
    print("- GET /api/audit/user/<requested_by> - Query activities by user")
    print("- GET /api/audit/cluster/<cluster_name> - Query activities by cluster")
    print("- GET /api/audit/summary - Get audit summary")
    print("\nSupported parameters:")
    print("- start_date: ISO format (YYYY-MM-DDTHH:MM:SS)")
    print("- end_date: ISO format (YYYY-MM-DDTHH:MM:SS)")
    print("- limit: Number of results (1-1000, default 100)")
    return True

if __name__ == "__main__":
    try:
        success = test_audit_endpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)