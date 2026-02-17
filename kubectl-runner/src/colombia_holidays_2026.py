#!/usr/bin/env python3
"""
Generate Colombia holidays configuration for 2026
"""

import holidays
from datetime import datetime

def generate_colombia_config():
    """Generate Colombia holidays configuration for 2026"""
    
    print("Configuración de Festivos Colombia 2026")
    print("=" * 50)
    
    try:
        # Get Colombia holidays for 2026
        colombia_holidays = holidays.Colombia(years=2026)
        
        print(f"\nFestivos oficiales de Colombia en 2026:")
        print(f"Total de festivos: {len(colombia_holidays)}")
        
        # Show detailed list
        print(f"\nListado detallado:")
        for date, name in sorted(colombia_holidays.items()):
            weekday = date.strftime('%A')
            print(f"   {date} ({weekday}): {name}")
        
        # Generate manual configuration
        holiday_dates = [date.strftime('%Y-%m-%d') for date in sorted(colombia_holidays.keys())]
        manual_config = ','.join(holiday_dates)
        
        print(f"\n" + "=" * 50)
        print("CONFIGURACIÓN PARA DEPLOYMENT")
        print("=" * 50)
        
        print(f"\n1. Configuración Automática (Recomendada):")
        print(f"   BUSINESS_HOLIDAYS_COUNTRY=\"CO\"")
        print(f"   BUSINESS_HOLIDAYS_SUBDIVISION=\"\"")
        
        print(f"\n2. Configuración Manual:")
        print(f"   BUSINESS_HOLIDAYS=\"{manual_config}\"")
        
        print(f"\n3. Configuración Completa para Colombia:")
        print(f"""
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/Bogota"
- name: BUSINESS_START_HOUR
  value: "8"
- name: BUSINESS_END_HOUR
  value: "18"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "CO"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: ""  # Festivos adicionales de empresa si los hay
""")
        
        # Show by month
        print(f"\n" + "=" * 50)
        print("FESTIVOS POR MES")
        print("=" * 50)
        
        by_month = {}
        for date, name in colombia_holidays.items():
            month = date.strftime('%B %Y')
            if month not in by_month:
                by_month[month] = []
            by_month[month].append((date, name))
        
        for month, holidays_list in sorted(by_month.items()):
            print(f"\n{month}:")
            for date, name in sorted(holidays_list):
                weekday = date.strftime('%A')
                print(f"   {date.strftime('%d')} ({weekday}): {name}")
        
        return True
        
    except Exception as e:
        print(f"Error generando configuración para Colombia: {e}")
        return False

if __name__ == "__main__":
    generate_colombia_config()