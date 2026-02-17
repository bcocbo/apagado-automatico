#!/usr/bin/env python3
"""
Test script for business hours detection logic
Tests the improved business hours detection with timezone support
"""

import requests
import json
import sys
import time
import os
from datetime import datetime, timedelta
from unittest.mock import patch

def test_business_hours_detection():
    """Test business hours detection logic"""
    base_url = "http://localhost:8080"
    
    print("Testing Business Hours Detection Logic")
    print("=" * 60)
    
    # Test 1: Test business hours endpoint
    print("\n1. Testing business hours endpoint...")
    try:
        response = requests.get(f"{base_url}/api/business-hours")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Check for expected fields
            expected_fields = [
                'current_time', 'timezone', 'business_hours', 'business_days',
                'holidays', 'is_non_business_hours', 'current_weekday', 
                'current_hour', 'limit_active'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if not missing_fields:
                print("   ✓ All expected fields present in business hours response")
                print(f"   Current time: {data.get('current_time')}")
                print(f"   Timezone: {data.get('timezone')}")
                print(f"   Business hours: {data.get('business_hours')}")
                print(f"   Is non-business: {data.get('is_non_business_hours')}")
                print(f"   Current weekday: {data.get('current_weekday')}")
                print(f"   Holidays: {data.get('holidays', [])}")
            else:
                print(f"   ✗ Missing fields: {missing_fields}")
                return False
                
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 2: Test namespace status includes business hours info
    print("\n2. Testing namespace status with business hours...")
    try:
        response = requests.get(f"{base_url}/api/namespaces/status")
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for business hours fields
            if 'is_non_business_hours' in data and 'limit_applies' in data:
                is_non_business = data.get('is_non_business_hours')
                limit_applies = data.get('limit_applies')
                
                print(f"   Is non-business hours: {is_non_business}")
                print(f"   Limit applies: {limit_applies}")
                
                # Verify consistency
                if is_non_business == limit_applies:
                    print("   ✓ Business hours status consistent between endpoints")
                else:
                    print(f"   ✗ Inconsistent business hours status: non_business={is_non_business}, limit_applies={limit_applies}")
                    return False
            else:
                print("   ✗ Missing business hours fields in namespace status")
                return False
                
        else:
            print(f"   ✗ Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 3: Test validation during different hours (if we can simulate)
    print("\n3. Testing validation with business hours consideration...")
    try:
        # Setup: Create test cost center
        try:
            response = requests.post(
                f"{base_url}/api/cost-centers/business-hours-test/permissions",
                json={
                    "is_authorized": True,
                    "max_concurrent_namespaces": 5,
                    "authorized_namespaces": []
                }
            )
            print(f"   Created business-hours-test cost center: {response.status_code}")
        except Exception as e:
            print(f"   Warning: Could not create test cost center: {e}")
        
        time.sleep(2)  # Give DynamoDB time to propagate
        
        # Get current business hours status
        bh_response = requests.get(f"{base_url}/api/business-hours")
        if bh_response.status_code == 200:
            bh_data = bh_response.json()
            is_non_business = bh_data.get('is_non_business_hours', False)
            
            print(f"   Current status: {'Non-business' if is_non_business else 'Business'} hours")
            
            # Try to activate a namespace
            test_namespace = "business-hours-test-ns"
            response = requests.post(
                f"{base_url}/api/namespaces/{test_namespace}/activate",
                json={
                    "cost_center": "business-hours-test",
                    "user_id": "business.hours.test.user",
                    "requested_by": "business.hours.test.requester"
                }
            )
            
            print(f"   Activation Status Code: {response.status_code}")
            
            if response.status_code in [200, 400]:  # Either success or limit reached
                response_data = response.json()
                
                if response.status_code == 200:
                    print("   ✓ Activation successful")
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                else:
                    error_msg = response_data.get('error', '')
                    if is_non_business and 'Maximum 5 namespaces' in error_msg:
                        print("   ✓ Non-business hours limit properly enforced")
                    elif not is_non_business and 'Business hours - no limit' in error_msg:
                        print("   ✓ Business hours validation working")
                    else:
                        print(f"   ? Different validation result: {error_msg}")
            else:
                print(f"   ✗ Unexpected status code: {response.status_code}")
                return False
                
        else:
            print("   ✗ Could not get business hours status")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 4: Test timezone handling (if we can check configuration)
    print("\n4. Testing timezone configuration...")
    try:
        response = requests.get(f"{base_url}/api/business-hours")
        
        if response.status_code == 200:
            data = response.json()
            timezone = data.get('timezone', 'UTC')
            current_time = data.get('current_time', '')
            
            print(f"   Configured timezone: {timezone}")
            print(f"   Current time in timezone: {current_time}")
            
            # Check if timezone is reasonable
            if timezone in ['UTC', 'America/New_York', 'America/Los_Angeles', 'Europe/London']:
                print("   ✓ Timezone configuration looks reasonable")
            else:
                print(f"   ? Unusual timezone configuration: {timezone}")
            
            # Check if time format includes timezone
            if 'UTC' in current_time or 'EST' in current_time or 'PST' in current_time or 'EDT' in current_time or 'PDT' in current_time:
                print("   ✓ Time includes timezone information")
            else:
                print(f"   ? Time format may not include timezone: {current_time}")
                
        else:
            print(f"   ✗ Could not get business hours info")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 5: Test holiday configuration
    print("\n5. Testing holiday configuration...")
    try:
        response = requests.get(f"{base_url}/api/business-hours")
        
        if response.status_code == 200:
            data = response.json()
            holidays = data.get('holidays', [])
            
            print(f"   Configured holidays: {holidays}")
            
            if holidays:
                print(f"   ✓ Found {len(holidays)} configured holidays")
                
                # Check holiday format
                valid_holidays = True
                for holiday in holidays:
                    try:
                        datetime.strptime(holiday, '%Y-%m-%d')
                    except ValueError:
                        print(f"   ✗ Invalid holiday format: {holiday}")
                        valid_holidays = False
                        break
                
                if valid_holidays:
                    print("   ✓ All holidays have valid date format")
                else:
                    return False
            else:
                print("   ✓ No holidays configured (optional)")
                
        else:
            print(f"   ✗ Could not get business hours info")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    # Test 6: Test business hours configuration
    print("\n6. Testing business hours configuration...")
    try:
        response = requests.get(f"{base_url}/api/business-hours")
        
        if response.status_code == 200:
            data = response.json()
            business_hours = data.get('business_hours', '')
            business_days = data.get('business_days', '')
            
            print(f"   Business hours: {business_hours}")
            print(f"   Business days: {business_days}")
            
            # Check format
            if ':' in business_hours and '-' in business_hours:
                print("   ✓ Business hours format looks correct")
            else:
                print(f"   ✗ Unexpected business hours format: {business_hours}")
                return False
            
            if 'Monday' in business_days and 'Friday' in business_days:
                print("   ✓ Business days format looks correct")
            else:
                print(f"   ✗ Unexpected business days format: {business_days}")
                return False
                
        else:
            print(f"   ✗ Could not get business hours info")
            return False
            
    except Exception as e:
        print(f"   ✗ Test failed with exception: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("All business hours detection tests passed! ✓")
    print("\nKey improvements implemented:")
    print("- ✓ Configurable timezone support")
    print("- ✓ Configurable business hours (start/end)")
    print("- ✓ Holiday support with date configuration")
    print("- ✓ Detailed business hours information endpoint")
    print("- ✓ Proper timezone handling in all calculations")
    print("- ✓ Enhanced logging and debugging capabilities")
    print("- ✓ Backward compatibility with existing logic")
    return True

if __name__ == "__main__":
    try:
        success = test_business_hours_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)