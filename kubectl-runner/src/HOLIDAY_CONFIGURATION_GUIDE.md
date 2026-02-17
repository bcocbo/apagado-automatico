# Holiday Configuration Guide

## Overview

El sistema de detección de horarios no laborales soporta múltiples formas de configurar holidays (días festivos) para diferentes países, regiones y necesidades empresariales.

## Métodos de Configuración

### 1. Holidays Manuales (Manual)

**Uso**: Para holidays específicos de la empresa o configuraciones personalizadas.

```yaml
env:
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-07-04,2024-11-28,2024-12-25"
```

**Ventajas**:
- Control total sobre qué días son holidays
- Puede incluir días específicos de la empresa
- No requiere librerías adicionales

**Desventajas**:
- Requiere actualización manual cada año
- No incluye automáticamente holidays oficiales

### 2. Holidays Automáticos por País (Recomendado)

**Uso**: Para holidays oficiales de un país completo.

```yaml
env:
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
```

**Ventajas**:
- Actualización automática de holidays oficiales
- Soporte para múltiples países
- No requiere mantenimiento anual

**Desventajas**:
- Puede incluir holidays que la empresa no observa
- Limitado a holidays oficiales del país

### 3. Holidays por Estado/Provincia

**Uso**: Para holidays específicos de un estado o provincia.

```yaml
env:
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: "NY"  # New York State
```

**Ventajas**:
- Incluye holidays locales específicos
- Más preciso para ubicaciones específicas
- Actualización automática

### 4. Configuración Híbrida (Recomendado para Empresas)

**Uso**: Combina holidays automáticos con holidays manuales específicos de la empresa.

```yaml
env:
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: "2024-12-24,2024-12-31"  # Company-specific holidays
```

**Ventajas**:
- Holidays oficiales automáticos + holidays de empresa
- Máxima flexibilidad
- Fácil mantenimiento

## Países Soportados

### Países Principales

| Código | País | Subdivisiones Disponibles |
|--------|------|---------------------------|
| `US` | Estados Unidos | Estados (NY, CA, TX, etc.) |
| `CA` | Canadá | Provincias (ON, BC, QC, etc.) |
| `GB` | Reino Unido | Países (England, Scotland, Wales, Northern Ireland) |
| `DE` | Alemania | Estados federales |
| `FR` | Francia | Regiones |
| `IT` | Italia | Regiones |
| `ES` | España | Comunidades autónomas |
| `AU` | Australia | Estados y territorios |
| `JP` | Japón | Prefecturas |
| `BR` | Brasil | Estados |
| `MX` | México | Estados |
| `CO` | Colombia | Departamentos |
| `IN` | India | Estados |

### Ejemplos por País

#### Estados Unidos
```yaml
# Federal holidays
BUSINESS_HOLIDAYS_COUNTRY: "US"
BUSINESS_HOLIDAYS_SUBDIVISION: ""

# New York State holidays
BUSINESS_HOLIDAYS_COUNTRY: "US"
BUSINESS_HOLIDAYS_SUBDIVISION: "NY"

# California holidays
BUSINESS_HOLIDAYS_COUNTRY: "US"
BUSINESS_HOLIDAYS_SUBDIVISION: "CA"
```

#### Canadá
```yaml
# Federal holidays
BUSINESS_HOLIDAYS_COUNTRY: "CA"
BUSINESS_HOLIDAYS_SUBDIVISION: ""

# Ontario holidays
BUSINESS_HOLIDAYS_COUNTRY: "CA"
BUSINESS_HOLIDAYS_SUBDIVISION: "ON"

# British Columbia holidays
BUSINESS_HOLIDAYS_COUNTRY: "CA"
BUSINESS_HOLIDAYS_SUBDIVISION: "BC"
```

#### Reino Unido
```yaml
# UK-wide holidays
BUSINESS_HOLIDAYS_COUNTRY: "GB"
BUSINESS_HOLIDAYS_SUBDIVISION: ""

# England holidays
BUSINESS_HOLIDAYS_COUNTRY: "GB"
BUSINESS_HOLIDAYS_SUBDIVISION: "England"

# Scotland holidays
BUSINESS_HOLIDAYS_COUNTRY: "GB"
BUSINESS_HOLIDAYS_SUBDIVISION: "Scotland"
```

#### Colombia
```yaml
# Colombia national holidays
BUSINESS_HOLIDAYS_COUNTRY: "CO"
BUSINESS_HOLIDAYS_SUBDIVISION: ""

# Specific department (if supported)
BUSINESS_HOLIDAYS_COUNTRY: "CO"
BUSINESS_HOLIDAYS_SUBDIVISION: "Bogotá"
```

## Configuraciones de Ejemplo

### 1. Empresa Estadounidense (Costa Este)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/New_York"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: "2024-12-24,2024-12-31"  # Christmas Eve, New Year's Eve
```

### 2. Empresa Canadiense (Toronto)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/Toronto"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "CA"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: "ON"  # Ontario
- name: BUSINESS_HOLIDAYS
  value: "2024-12-27"  # Boxing Day observed
```

### 3. Empresa Europea (Londres)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "Europe/London"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "GB"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: "England"
- name: BUSINESS_HOLIDAYS
  value: ""  # Only official holidays
```

### 4. Empresa Multinacional (Oficinas múltiples)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "UTC"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"  # Primary office
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-12-25,2024-12-26"  # Global company holidays
```

### 5. Empresa Colombiana (Bogotá)
```yaml
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
  value: ""  # Additional company holidays if needed
```

## Generación Masiva de Holidays

### Colombia Holidays Configuration Tool

Un script especializado está disponible para generar configuraciones de holidays de Colombia:

```bash
cd kubectl-runner/src
python3 colombia_holidays_2026.py
```

**Características**:
- Genera lista completa de festivos oficiales de Colombia para 2026
- Proporciona configuración automática y manual
- Incluye configuración completa de deployment
- Muestra desglose mensual para planificación
- Formato listo para usar en manifiestos de Kubernetes

**Ejemplo de salida**:
```
Configuración de Festivos Colombia 2026
==================================================

Festivos oficiales de Colombia en 2026:
Total de festivos: 18

CONFIGURACIÓN PARA DEPLOYMENT
==================================================

1. Configuración Automática (Recomendada):
   BUSINESS_HOLIDAYS_COUNTRY="CO"
   BUSINESS_HOLIDAYS_SUBDIVISION=""

2. Configuración Manual:
   BUSINESS_HOLIDAYS="2026-01-01,2026-01-12,2026-03-23,..."

3. Configuración Completa para Colombia:
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
  value: ""  # Additional company holidays if needed
```

### Script de Generación

Puedes usar el script `holiday_examples.py` para generar configuraciones:

```bash
cd kubectl-runner/src
python3 holiday_examples.py
```

### Generación Manual por Año

```python
import holidays

# US Federal holidays for 2024
us_holidays = holidays.US(years=2024)
holiday_list = [date.strftime('%Y-%m-%d') for date in sorted(us_holidays.keys())]
config_string = ','.join(holiday_list)
print(f"BUSINESS_HOLIDAYS=\"{config_string}\"")
```

### Generación para Múltiples Años

```python
import holidays

# US holidays for 2024-2026
us_holidays = holidays.US(years=[2024, 2025, 2026])
holiday_list = [date.strftime('%Y-%m-%d') for date in sorted(us_holidays.keys())]
config_string = ','.join(holiday_list)
print(f"BUSINESS_HOLIDAYS=\"{config_string}\"")
```

## API Response Examples

### Con Holidays Automáticos Habilitados

```json
{
  "current_time": "2024-01-15 14:30:00 EST",
  "timezone": "America/New_York",
  "business_hours": "07:00 - 20:00",
  "business_days": "Monday - Friday",
  "manual_holidays": ["2024-12-24", "2024-12-31"],
  "automatic_holidays": {
    "enabled": true,
    "country": "US",
    "subdivision": null,
    "holidays_count": 11,
    "holidays": [
      {"date": "2024-01-01", "name": "New Year's Day"},
      {"date": "2024-01-15", "name": "Martin Luther King Jr. Day"},
      {"date": "2024-02-19", "name": "Presidents Day"},
      {"date": "2024-05-27", "name": "Memorial Day"},
      {"date": "2024-07-04", "name": "Independence Day"},
      {"date": "2024-09-02", "name": "Labor Day"},
      {"date": "2024-10-14", "name": "Columbus Day"},
      {"date": "2024-11-11", "name": "Veterans Day"},
      {"date": "2024-11-28", "name": "Thanksgiving"},
      {"date": "2024-12-25", "name": "Christmas Day"}
    ]
  },
  "is_non_business_hours": false,
  "current_weekday": "Monday",
  "current_hour": 14,
  "limit_active": false
}
```

### Sin Holidays Automáticos

```json
{
  "current_time": "2024-01-15 14:30:00 EST",
  "timezone": "America/New_York",
  "business_hours": "07:00 - 20:00",
  "business_days": "Monday - Friday",
  "manual_holidays": ["2024-01-01", "2024-07-04", "2024-12-25"],
  "automatic_holidays": {
    "enabled": false,
    "country": null,
    "subdivision": null,
    "holidays_count": 0,
    "holidays": []
  },
  "is_non_business_hours": false,
  "current_weekday": "Monday",
  "current_hour": 14,
  "limit_active": false
}
```

## Mejores Prácticas

### 1. Para Empresas Pequeñas/Medianas
- Usar holidays automáticos por país
- Agregar holidays específicos de empresa manualmente
- Configurar timezone apropiado

### 2. Para Empresas Multinacionales
- Usar holidays del país de la oficina principal
- Considerar UTC como timezone base
- Documentar holidays específicos por región

### 3. Para Desarrollo/Testing
- Usar configuración mínima para testing
- Incluir holidays cercanos para pruebas
- Documentar configuraciones de test vs producción

### 4. Para Compliance/Auditoría
- Documentar fuente de holidays (oficial vs empresa)
- Mantener registro de cambios de configuración
- Validar holidays con departamento legal/HR

## Troubleshooting

### Problema: Holidays no se detectan
**Solución**: Verificar configuración con `/api/business-hours`

### Problema: Demasiados holidays
**Solución**: Usar subdivisión específica o holidays manuales

### Problema: Holidays incorrectos
**Solución**: Verificar código de país y subdivisión

### Problema: Error de librería
**Solución**: Verificar que `holidays==0.34` esté instalado

## Migración

### De Manual a Automático
1. Backup configuración actual
2. Configurar `BUSINESS_HOLIDAYS_COUNTRY`
3. Verificar holidays con API
4. Mantener holidays específicos en `BUSINESS_HOLIDAYS`

### Actualización Anual
1. Verificar nuevos holidays oficiales
2. Actualizar holidays específicos de empresa
3. Probar configuración antes de despliegue