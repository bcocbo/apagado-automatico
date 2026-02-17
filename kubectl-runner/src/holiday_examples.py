#!/usr/bin/env python3
"""
Examples of different ways to configure holidays for business hours detection
"""

import holidays
from datetime import datetime

def show_holiday_options():
    """Show different options for configuring holidays"""
    
    print("Holiday Configuration Options")
    print("=" * 50)
    
    # Option 1: US Federal Holidays
    print("\n1. US Federal Holidays (2024):")
    us_holidays = holidays.US(years=2024)
    for date, name in sorted(us_holidays.items()):
        print(f"   {date}: {name}")
    
    # Option 2: US with specific state (e.g., New York)
    print("\n2. US New York State Holidays (2024):")
    ny_holidays = holidays.US(state='NY', years=2024)
    for date, name in sorted(ny_holidays.items()):
        print(f"   {date}: {name}")
    
    # Option 3: Other countries
    print("\n3. Canada Federal Holidays (2024):")
    ca_holidays = holidays.Canada(years=2024)
    for date, name in sorted(ca_holidays.items())[:10]:  # Show first 10
        print(f"   {date}: {name}")
    
    print("\n4. UK Holidays (2024):")
    uk_holidays = holidays.UK(years=2024)
    for date, name in sorted(uk_holidays.items()):
        print(f"   {date}: {name}")
    
    # Option 4: Generate environment variable strings
    print("\n5. Environment Variable Examples:")
    
    # US Federal holidays as comma-separated string
    us_dates = [date.strftime('%Y-%m-%d') for date in sorted(us_holidays.keys())]
    print(f"\n   US Federal (manual):")
    print(f"   BUSINESS_HOLIDAYS=\"{','.join(us_dates)}\"")
    
    # Automatic configuration
    print(f"\n   US Federal (automatic):")
    print(f"   BUSINESS_HOLIDAYS_COUNTRY=\"US\"")
    print(f"   BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")
    
    print(f"\n   US New York (automatic):")
    print(f"   BUSINESS_HOLIDAYS_COUNTRY=\"US\"")
    print(f"   BUSINESS_HOLIDAYS_SUBDIVISION=\"NY\"")
    
    print(f"\n   Canada (automatic):")
    print(f"   BUSINESS_HOLIDAYS_COUNTRY=\"CA\"")
    print(f"   BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")
    
    print(f"\n   UK (automatic):")
    print(f"   BUSINESS_HOLIDAYS_COUNTRY=\"GB\"")
    print(f"   BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")

def show_supported_countries():
    """Show supported countries and subdivisions"""
    
    print("\n\nSupported Countries and Subdivisions")
    print("=" * 50)
    
    # Get list of supported countries
    supported = holidays.list_supported_countries()
    
    print(f"\nTotal supported countries: {len(supported)}")
    print("\nMost common countries:")
    
    common_countries = [
        ('US', 'United States'),
        ('CA', 'Canada'), 
        ('GB', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('AU', 'Australia'),
        ('JP', 'Japan'),
        ('BR', 'Brazil'),
        ('MX', 'Mexico'),
        ('IN', 'India')
    ]
    
    for code, name in common_countries:
        if code in supported:
            print(f"   {code}: {name}")
            
            # Show subdivisions if available
            try:
                country_class = getattr(holidays, code)
                if hasattr(country_class, 'subdivisions'):
                    subdivisions = country_class.subdivisions
                    if subdivisions:
                        subdiv_list = list(subdivisions.keys())[:5]  # Show first 5
                        print(f"      Subdivisions: {', '.join(subdiv_list)}")
            except:
                pass

def generate_yearly_config(country='US', subdivision=None, year=2024):
    """Generate a complete yearly holiday configuration"""
    
    print(f"\n\nYearly Holiday Configuration Generator")
    print("=" * 50)
    
    try:
        if subdivision:
            country_holidays = holidays.country_holidays(country, subdiv=subdivision, years=year)
            location = f"{country}/{subdivision}"
        else:
            country_holidays = holidays.country_holidays(country, years=year)
            location = country
        
        print(f"\nHolidays for {location} in {year}:")
        print(f"Total holidays: {len(country_holidays)}")
        
        # Generate manual configuration
        holiday_dates = [date.strftime('%Y-%m-%d') for date in sorted(country_holidays.keys())]
        manual_config = ','.join(holiday_dates)
        
        print(f"\nManual Configuration:")
        print(f"BUSINESS_HOLIDAYS=\"{manual_config}\"")
        
        print(f"\nAutomatic Configuration:")
        print(f"BUSINESS_HOLIDAYS_COUNTRY=\"{country}\"")
        if subdivision:
            print(f"BUSINESS_HOLIDAYS_SUBDIVISION=\"{subdivision}\"")
        else:
            print(f"BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")
        
        print(f"\nDetailed Holiday List:")
        for date, name in sorted(country_holidays.items()):
            print(f"   {date}: {name}")
            
    except Exception as e:
        print(f"Error generating config for {country}: {e}")

if __name__ == "__main__":
    show_holiday_options()
    show_supported_countries()
    
    # Generate configs for different regions
    generate_yearly_config('US', None, 2024)
    generate_yearly_config('US', 'NY', 2024)
    generate_yearly_config('CA', None, 2024)
    generate_yearly_config('GB', None, 2024)