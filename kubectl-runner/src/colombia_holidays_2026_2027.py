#!/usr/bin/env python3
"""
Festivos de Colombia 2026-2027
Incluye festivos fijos y móviles según la legislación colombiana
"""

from datetime import datetime, date
import holidays

def get_colombia_holidays_2026_2027():
    """
    Retorna los festivos de Colombia para 2026 y 2027
    """
    # Crear objeto holidays para Colombia
    colombia_holidays = {}
    
    # Agregar festivos para 2026 y 2027
    for year in [2026, 2027]:
        year_holidays = holidays.Colombia(years=year)
        for date_obj, name in year_holidays.items():
            colombia_holidays[date_obj.strftime('%Y-%m-%d')] = name
    
    return colombia_holidays

def get_colombia_holidays_list():
    """
    Retorna lista de fechas de festivos en formato YYYY-MM-DD
    """
    holidays_dict = get_colombia_holidays_2026_2027()
    return list(holidays_dict.keys())

# Festivos específicos de Colombia 2026-2027 (backup manual si la librería falla)
COLOMBIA_HOLIDAYS_2026_2027 = {
    # 2026
    '2026-01-01': 'Año Nuevo',
    '2026-01-06': 'Día de los Reyes Magos',
    '2026-03-23': 'Día de San José',
    '2026-04-09': 'Jueves Santo',
    '2026-04-10': 'Viernes Santo',
    '2026-05-01': 'Día del Trabajo',
    '2026-05-25': 'Ascensión del Señor',
    '2026-06-15': 'Corpus Christi',
    '2026-06-22': 'Sagrado Corazón de Jesús',
    '2026-06-29': 'San Pedro y San Pablo',
    '2026-07-20': 'Día de la Independencia',
    '2026-08-07': 'Batalla de Boyacá',
    '2026-08-17': 'Asunción de la Virgen',
    '2026-10-12': 'Día de la Raza',
    '2026-11-02': 'Día de Todos los Santos',
    '2026-11-16': 'Independencia de Cartagena',
    '2026-12-08': 'Inmaculada Concepción',
    '2026-12-25': 'Navidad',
    
    # 2027
    '2027-01-01': 'Año Nuevo',
    '2027-01-11': 'Día de los Reyes Magos',
    '2027-03-22': 'Día de San José',
    '2027-03-25': 'Jueves Santo',
    '2027-03-26': 'Viernes Santo',
    '2027-05-01': 'Día del Trabajo',
    '2027-05-10': 'Ascensión del Señor',
    '2027-05-31': 'Corpus Christi',
    '2027-06-07': 'Sagrado Corazón de Jesús',
    '2027-06-28': 'San Pedro y San Pablo',
    '2027-07-20': 'Día de la Independencia',
    '2027-08-07': 'Batalla de Boyacá',
    '2027-08-16': 'Asunción de la Virgen',
    '2027-10-11': 'Día de la Raza',
    '2027-11-01': 'Día de Todos los Santos',
    '2027-11-15': 'Independencia de Cartagena',
    '2027-12-08': 'Inmaculada Concepción',
    '2027-12-25': 'Navidad'
}

def is_colombia_holiday(date_str):
    """
    Verifica si una fecha es festivo en Colombia
    Args:
        date_str: Fecha en formato 'YYYY-MM-DD'
    Returns:
        bool: True si es festivo
    """
    try:
        # Intentar usar la librería holidays primero
        holidays_dict = get_colombia_holidays_2026_2027()
        return date_str in holidays_dict
    except:
        # Fallback a la lista manual
        return date_str in COLOMBIA_HOLIDAYS_2026_2027

def get_holiday_name(date_str):
    """
    Obtiene el nombre del festivo para una fecha
    Args:
        date_str: Fecha en formato 'YYYY-MM-DD'
    Returns:
        str: Nombre del festivo o None si no es festivo
    """
    try:
        holidays_dict = get_colombia_holidays_2026_2027()
        return holidays_dict.get(date_str)
    except:
        return COLOMBIA_HOLIDAYS_2026_2027.get(date_str)

if __name__ == "__main__":
    # Mostrar todos los festivos
    print("Festivos de Colombia 2026-2027:")
    print("=" * 50)
    
    try:
        holidays_dict = get_colombia_holidays_2026_2027()
        for date_str in sorted(holidays_dict.keys()):
            print(f"{date_str}: {holidays_dict[date_str]}")
    except Exception as e:
        print(f"Error con librería holidays: {e}")
        print("Usando lista manual:")
        for date_str in sorted(COLOMBIA_HOLIDAYS_2026_2027.keys()):
            print(f"{date_str}: {COLOMBIA_HOLIDAYS_2026_2027[date_str]}")