#!/usr/bin/env python3
"""
Simple test for Colombia holidays configuration
Tests Colombia holidays without importing the full app
"""

import holidays
from datetime import datetime

def test_colombia_holidays_simple():
    """Simple test for Colombia holidays"""
    print("Testing Colombia Holidays (Simple)")
    print("=" * 40)
    
    try:
        # Test Colombia holidays for 2026
        colombia_holidays = holidays.Colombia(years=2026)
        
        print(f"\n1. Colombia holidays loaded successfully")
        print(f"   Total holidays: {len(colombia_holidays)}")
        
        if len(colombia_holidays) >= 15:
            print("   ✓ Expected number of holidays found")
        else:
            print("   ✗ Fewer holidays than expected")
            return False
        
        # Test specific dates
        test_dates = [
            (datetime(2026, 1, 1).date(), "New Year's Day"),
            (datetime(2026, 4, 3).date(), "Good Friday"),
            (datetime(2026, 5, 1).date(), "Labour Day"),
            (datetime(2026, 7, 20).date(), "Independence Day"),
            (datetime(2026, 8, 7).date(), "Battle of Boyacá"),
            (datetime(2026, 12, 25).date(), "Christmas")
        ]
        
        print(f"\n2. Testing specific holiday dates:")
        for test_date, expected_name in test_dates:
            if test_date in colombia_holidays:
                actual_name = colombia_holidays[test_date]
                print(f"   ✓ {test_date}: {actual_name}")
            else:
                print(f"   ✗ {test_date}: Not found (expected {expected_name})")
                return False
        
        # Test non-holiday dates
        print(f"\n3. Testing non-holiday dates:")
        non_holidays = [
            datetime(2026, 2, 15).date(),
            datetime(2026, 6, 10).date(),
            datetime(2026, 9, 15).date()
        ]
        
        for test_date in non_holidays:
            if test_date not in colombia_holidays:
                print(f"   ✓ {test_date}: Correctly not a holiday")
            else:
                print(f"   ? {test_date}: Is a holiday ({colombia_holidays[test_date]})")
        
        # Show all holidays by month
        print(f"\n4. All Colombia holidays for 2026:")
        by_month = {}
        for date, name in colombia_holidays.items():
            month = date.strftime('%B')
            if month not in by_month:
                by_month[month] = []
            by_month[month].append((date, name))
        
        for month in ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']:
            if month in by_month:
                print(f"\n   {month}:")
                for date, name in sorted(by_month[month]):
                    weekday = date.strftime('%A')
                    print(f"      {date.strftime('%d')} ({weekday}): {name}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_colombia_holidays_simple()
    
    if success:
        print("\n" + "=" * 40)
        print("Colombia holidays test passed! ✓")
        print("\nConfiguración recomendada:")
        print("BUSINESS_HOLIDAYS_COUNTRY=\"CO\"")
        print("BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")
        print("BUSINESS_HOURS_TIMEZONE=\"America/Bogota\"")
    else:
        print("\n" + "=" * 40)
        print("Colombia holidays test failed! ✗")
    
    exit(0 if success else 1)