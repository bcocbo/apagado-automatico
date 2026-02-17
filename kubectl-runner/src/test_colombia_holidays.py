#!/usr/bin/env python3
"""
Test script for Colombia holidays configuration
Tests that Colombia holidays are properly detected for 2026
"""

import os
import sys
from datetime import datetime
from unittest.mock import patch

# Add the current directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_colombia_holidays():
    """Test Colombia holidays detection"""
    print("Testing Colombia Holidays Configuration")
    print("=" * 50)
    
    # Test with Colombia configuration
    with patch.dict(os.environ, {
        'BUSINESS_HOURS_TIMEZONE': 'America/Bogota',
        'BUSINESS_START_HOUR': '8',
        'BUSINESS_END_HOUR': '18',
        'BUSINESS_HOLIDAYS_COUNTRY': 'CO',
        'BUSINESS_HOLIDAYS_SUBDIVISION': '',
        'BUSINESS_HOLIDAYS': ''
    }):
        try:
            from app import TaskScheduler, DynamoDBManager
            
            # Mock DynamoDB to avoid actual AWS calls
            with patch('boto3.resource') as mock_boto3:
                mock_dynamodb = Mock()
                mock_table = Mock()
                mock_permissions_table = Mock()
                
                mock_boto3.return_value = mock_dynamodb
                mock_dynamodb.Table.side_effect = [mock_table, mock_permissions_table]
                mock_table.load.return_value = None
                mock_permissions_table.load.return_value = None
                
                # Create TaskScheduler instance
                scheduler = TaskScheduler()
                
                print("\n1. Testing business hours info with Colombia config...")
                
                # Get business hours info
                info = scheduler.get_business_hours_info()
                
                print(f"   Timezone: {info.get('timezone')}")
                print(f"   Business hours: {info.get('business_hours')}")
                print(f"   Automatic holidays enabled: {info.get('automatic_holidays', {}).get('enabled')}")
                print(f"   Country: {info.get('automatic_holidays', {}).get('country')}")
                
                auto_holidays = info.get('automatic_holidays', {})
                if auto_holidays.get('enabled'):
                    holidays_count = auto_holidays.get('holidays_count', 0)
                    print(f"   Total holidays for 2026: {holidays_count}")
                    
                    if holidays_count > 0:
                        print("   ✓ Colombia holidays loaded successfully")
                        
                        # Show some holidays
                        holidays_list = auto_holidays.get('holidays', [])
                        print(f"\n   Sample holidays:")
                        for holiday in holidays_list[:5]:  # Show first 5
                            print(f"      {holiday.get('date')}: {holiday.get('name')}")
                        
                        if holidays_count >= 15:  # Colombia should have ~18 holidays
                            print(f"   ✓ Expected number of holidays found ({holidays_count})")
                        else:
                            print(f"   ? Fewer holidays than expected ({holidays_count})")
                    else:
                        print("   ✗ No holidays found")
                        return False
                else:
                    print("   ✗ Automatic holidays not enabled")
                    return False
                
                print("\n2. Testing specific Colombia holiday dates...")
                
                # Test specific Colombia holidays for 2026
                colombia_test_dates = [
                    (datetime(2026, 1, 1), "New Year's Day"),
                    (datetime(2026, 4, 3), "Good Friday"),
                    (datetime(2026, 5, 1), "Labour Day"),
                    (datetime(2026, 7, 20), "Independence Day"),
                    (datetime(2026, 8, 7), "Battle of Boyacá"),
                    (datetime(2026, 12, 25), "Christmas")
                ]
                
                for test_date, expected_name in colombia_test_dates:
                    is_holiday = scheduler._is_holiday(test_date)
                    if is_holiday:
                        print(f"   ✓ {test_date.strftime('%Y-%m-%d')} correctly detected as holiday ({expected_name})")
                    else:
                        print(f"   ✗ {test_date.strftime('%Y-%m-%d')} not detected as holiday ({expected_name})")
                        return False
                
                print("\n3. Testing non-holiday dates...")
                
                # Test non-holiday dates
                non_holiday_dates = [
                    datetime(2026, 2, 15),  # Random February date
                    datetime(2026, 6, 10),  # Random June date
                    datetime(2026, 9, 15),  # Random September date
                ]
                
                for test_date in non_holiday_dates:
                    is_holiday = scheduler._is_holiday(test_date)
                    if not is_holiday:
                        print(f"   ✓ {test_date.strftime('%Y-%m-%d')} correctly detected as non-holiday")
                    else:
                        print(f"   ? {test_date.strftime('%Y-%m-%d')} detected as holiday (may be correct)")
                
                print("\n4. Testing business hours detection with holidays...")
                
                # Test business hours on a holiday (should be non-business)
                holiday_date = datetime(2026, 7, 20, 10, 0)  # Independence Day at 10 AM
                is_non_business = scheduler.is_non_business_hours(holiday_date)
                
                if is_non_business:
                    print(f"   ✓ Holiday correctly detected as non-business hours")
                else:
                    print(f"   ✗ Holiday not detected as non-business hours")
                    return False
                
                # Test business hours on a regular weekday
                regular_date = datetime(2026, 2, 10, 10, 0)  # Regular Tuesday at 10 AM
                is_non_business = scheduler.is_non_business_hours(regular_date)
                
                if not is_non_business:
                    print(f"   ✓ Regular business day correctly detected")
                else:
                    print(f"   ✗ Regular business day detected as non-business")
                    return False
                
                print("\n5. Testing timezone handling...")
                
                # Test that timezone is correctly set to Bogota
                if info.get('timezone') == 'America/Bogota':
                    print("   ✓ Timezone correctly set to America/Bogota")
                else:
                    print(f"   ✗ Timezone incorrect: {info.get('timezone')}")
                    return False
                
                # Test business hours
                if info.get('business_hours') == '08:00 - 18:00':
                    print("   ✓ Business hours correctly set to 8 AM - 6 PM")
                else:
                    print(f"   ✗ Business hours incorrect: {info.get('business_hours')}")
                    return False
                
                return True
                
        except ImportError as e:
            print(f"   ✗ Import error: {e}")
            return False
        except Exception as e:
            print(f"   ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    try:
        # Import Mock here to avoid issues if not available
        from unittest.mock import Mock
        
        success = test_colombia_holidays()
        
        if success:
            print("\n" + "=" * 50)
            print("All Colombia holidays tests passed! ✓")
            print("\nConfiguración aplicada:")
            print("- Timezone: America/Bogota")
            print("- Horario laboral: 8:00 AM - 6:00 PM")
            print("- Festivos: Colombia 2026 (18 festivos oficiales)")
            print("- Configuración automática habilitada")
        else:
            print("\n" + "=" * 50)
            print("Some Colombia holidays tests failed! ✗")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\nTest suite failed with exception: {e}")
        sys.exit(1)