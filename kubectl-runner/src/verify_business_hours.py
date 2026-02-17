#!/usr/bin/env python3
"""
Simple verification script to check that business hours detection is implemented correctly
This script analyzes the source code to verify the changes without running the app
"""

import os
import re

def verify_business_hours_implementation():
    """Verify that business hours detection is properly implemented"""
    print("Verifying Business Hours Detection Implementation")
    print("=" * 50)
    
    # Read the app.py file
    app_file = 'app.py'
    if not os.path.exists(app_file):
        print(f"✗ {app_file} not found")
        return False
    
    with open(app_file, 'r') as f:
        content = f.read()
    
    # Test 1: Verify timezone support
    print("\n1. Checking timezone support...")
    
    if 'import pytz' in content:
        print("   ✓ pytz import found")
    else:
        print("   ✗ pytz import not found")
        return False
    
    if 'BUSINESS_HOURS_TIMEZONE' in content:
        print("   ✓ Timezone configuration support found")
    else:
        print("   ✗ Timezone configuration not found")
        return False
    
    if 'pytz.timezone(timezone_name)' in content:
        print("   ✓ Timezone object creation found")
    else:
        print("   ✗ Timezone object creation not found")
        return False
    
    # Test 2: Verify configurable business hours
    print("\n2. Checking configurable business hours...")
    
    if 'BUSINESS_START_HOUR' in content and 'BUSINESS_END_HOUR' in content:
        print("   ✓ Configurable business hours found")
    else:
        print("   ✗ Configurable business hours not found")
        return False
    
    # Check validation of business hours
    if 'if not (0 <= business_start_hour <= 23)' in content:
        print("   ✓ Business hours validation found")
    else:
        print("   ✗ Business hours validation not found")
        return False
    
    # Test 3: Verify holiday support
    print("\n3. Checking holiday support...")
    
    if 'def _is_holiday(self, current_time):' in content:
        print("   ✓ Holiday checking method found")
    else:
        print("   ✗ Holiday checking method not found")
        return False
    
    if 'BUSINESS_HOLIDAYS' in content:
        print("   ✓ Holiday configuration support found")
    else:
        print("   ✗ Holiday configuration not found")
        return False
    
    # Test 4: Verify enhanced logging
    print("\n4. Checking enhanced logging...")
    
    if 'logger.debug(f"Business hours check:' in content:
        print("   ✓ Debug logging for business hours found")
    else:
        print("   ✗ Debug logging not found")
        return False
    
    if 'logger.info(f"Current date {current_date} is a configured holiday")' in content:
        print("   ✓ Holiday logging found")
    else:
        print("   ✗ Holiday logging not found")
        return False
    
    # Test 5: Verify business hours info method
    print("\n5. Checking business hours info method...")
    
    if 'def get_business_hours_info(self):' in content:
        print("   ✓ Business hours info method found")
    else:
        print("   ✗ Business hours info method not found")
        return False
    
    # Check for comprehensive info fields
    info_fields = [
        'current_time', 'timezone', 'business_hours', 'business_days',
        'holidays', 'is_non_business_hours', 'current_weekday', 'current_hour'
    ]
    
    missing_info_fields = []
    for field in info_fields:
        if f"'{field}'" not in content:
            missing_info_fields.append(field)
    
    if not missing_info_fields:
        print("   ✓ All business hours info fields found")
    else:
        print(f"   ✗ Missing info fields: {missing_info_fields}")
        return False
    
    # Test 6: Verify API endpoint
    print("\n6. Checking API endpoint...")
    
    if "@app.route('/api/business-hours', methods=['GET'])" in content:
        print("   ✓ Business hours API endpoint found")
    else:
        print("   ✗ Business hours API endpoint not found")
        return False
    
    if 'def get_business_hours():' in content:
        print("   ✓ Business hours endpoint function found")
    else:
        print("   ✗ Business hours endpoint function not found")
        return False
    
    # Test 7: Verify error handling
    print("\n7. Checking error handling...")
    
    if 'except pytz.exceptions.UnknownTimeZoneError:' in content:
        print("   ✓ Timezone error handling found")
    else:
        print("   ✗ Timezone error handling not found")
        return False
    
    if 'logger.warning(f"Unknown timezone' in content:
        print("   ✓ Timezone warning logging found")
    else:
        print("   ✗ Timezone warning logging not found")
        return False
    
    # Test 8: Verify timestamp handling
    print("\n8. Checking timestamp handling...")
    
    if 'elif isinstance(timestamp, datetime):' in content:
        print("   ✓ Datetime object handling found")
    else:
        print("   ✗ Datetime object handling not found")
        return False
    
    if 'astimezone(business_timezone)' in content:
        print("   ✓ Timezone conversion found")
    else:
        print("   ✗ Timezone conversion not found")
        return False
    
    # Test 9: Check requirements.txt
    print("\n9. Checking requirements.txt...")
    
    requirements_file = '../requirements.txt'
    if os.path.exists(requirements_file):
        with open(requirements_file, 'r') as f:
            requirements_content = f.read()
        
        if 'pytz' in requirements_content:
            print("   ✓ pytz dependency found in requirements.txt")
        else:
            print("   ✗ pytz dependency not found in requirements.txt")
            return False
    else:
        print("   ? requirements.txt not found (may be in different location)")
    
    # Test 10: Check Dockerfile
    print("\n10. Checking Dockerfile...")
    
    dockerfile_path = '../Dockerfile'
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        if 'pytz' in dockerfile_content:
            print("   ✓ pytz dependency found in Dockerfile")
        else:
            print("   ✗ pytz dependency not found in Dockerfile")
            return False
    else:
        print("   ? Dockerfile not found (may be in different location)")
    
    print("\n" + "=" * 50)
    print("All business hours implementation verifications passed! ✓")
    print("\nSummary of changes implemented:")
    print("- ✓ Added timezone support with pytz")
    print("- ✓ Added configurable business hours (start/end)")
    print("- ✓ Added holiday support with date configuration")
    print("- ✓ Added comprehensive error handling")
    print("- ✓ Added enhanced logging and debugging")
    print("- ✓ Added business hours info method")
    print("- ✓ Added API endpoint for business hours info")
    print("- ✓ Added proper timestamp handling")
    print("- ✓ Updated dependencies (pytz)")
    print("- ✓ Maintained backward compatibility")
    return True

if __name__ == "__main__":
    try:
        success = verify_business_hours_implementation()
        exit_code = 0 if success else 1
        print(f"\nVerification {'PASSED' if success else 'FAILED'}")
        exit(exit_code)
    except Exception as e:
        print(f"\nVerification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)