# Business Hours Configuration Guide

## Overview

The namespace scheduler includes configurable business hours detection that determines when namespace limits should be enforced. This guide covers configuration, deployment, and usage of the business hours system.

## Dependencies

The business hours system requires the following Python packages:
- `pytz` - Timezone support
- `python-dateutil` - Date parsing utilities  
- `holidays==0.34` - Automatic holiday detection for 100+ countries

These dependencies are automatically installed with the kubectl-runner container.

## Configuration

### Environment Variables

The business hours system is configured through environment variables:

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `BUSINESS_HOURS_TIMEZONE` | `UTC` | Timezone for business hours calculation | `America/New_York` |
| `BUSINESS_START_HOUR` | `7` | Business day start hour (24-hour format) | `9` |
| `BUSINESS_END_HOUR` | `20` | Business day end hour (24-hour format) | `17` |
| `BUSINESS_HOLIDAYS` | `` | Comma-separated holiday dates (YYYY-MM-DD) | `2024-01-01,2024-07-04,2024-12-25` |
| `BUSINESS_HOLIDAYS_COUNTRY` | `` | Country code for automatic holiday detection | `US`, `CA`, `GB` |
| `BUSINESS_HOLIDAYS_SUBDIVISION` | `` | State/province for regional holidays | `NY`, `ON`, `England` |

### Configuration Examples

#### Standard US Business Hours (Automatic Holidays)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/New_York"
- name: BUSINESS_START_HOUR
  value: "9"
- name: BUSINESS_END_HOUR
  value: "17"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: "2024-12-24,2024-12-31"  # Additional company holidays
```

#### Standard US Business Hours (Manual Holidays)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/New_York"
- name: BUSINESS_START_HOUR
  value: "9"
- name: BUSINESS_END_HOUR
  value: "17"
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-01-15,2024-02-19,2024-05-27,2024-07-04,2024-09-02,2024-10-14,2024-11-11,2024-11-28,2024-12-25"
```

#### European Business Hours (UK)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "Europe/London"
- name: BUSINESS_START_HOUR
  value: "8"
- name: BUSINESS_END_HOUR
  value: "18"
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "GB"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: "England"
```

#### Colombia Business Hours
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

#### 24/7 Operation (No Limits)
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "UTC"
- name: BUSINESS_START_HOUR
  value: "0"
- name: BUSINESS_END_HOUR
  value: "24"
- name: BUSINESS_HOLIDAYS
  value: ""
```

## Business Hours Logic

### Non-Business Hours Definition

A time is considered "non-business hours" if ANY of the following conditions are true:

1. **Weekend**: Saturday or Sunday
2. **Outside Business Hours**: Before start hour or at/after end hour
3. **Holiday**: Date matches configured holiday list

### Namespace Limits

During non-business hours, the system enforces a limit of **5 active namespaces** per cost center to prevent resource waste.

## API Endpoints

### Get Business Hours Status

**GET** `/api/business-hours`

Returns current business hours configuration and status.

#### Response Example (with Automatic Holidays)
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
      {"date": "2024-07-04", "name": "Independence Day"},
      {"date": "2024-12-25", "name": "Christmas Day"}
    ]
  },
  "is_non_business_hours": false,
  "current_weekday": "Monday",
  "current_hour": 14,
  "limit_active": false
}
```

#### Response Example (Manual Holidays Only)
```json
{
  "current_time": "2024-01-15 14:30:00 EST",
  "timezone": "America/New_York",
  "business_hours": "07:00 - 20:00",
  "business_days": "Monday - Friday",
  "holidays": ["2024-01-01", "2024-07-04", "2024-12-25"],
  "is_non_business_hours": false,
  "current_weekday": "Monday",
  "current_hour": 14,
  "limit_active": false
}
```

#### Response Fields

- `current_time`: Current time in business timezone
- `timezone`: Configured timezone name
- `business_hours`: Formatted business hours range
- `business_days`: Always "Monday - Friday"
- `holidays`: List of configured manual holiday dates (legacy format)
- `manual_holidays`: List of manually configured holiday dates
- `automatic_holidays`: Object containing automatic holiday configuration and list
- `is_non_business_hours`: Whether current time is non-business
- `current_weekday`: Current day name
- `current_hour`: Current hour (0-23)
- `limit_active`: Whether namespace limits are active (same as `is_non_business_hours`)

## Deployment Configuration

### Kubernetes Manifests

#### Base Configuration
```yaml
# manifests/base/task-scheduler-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-scheduler
spec:
  template:
    spec:
      containers:
      - name: kubectl-runner
        env:
        - name: BUSINESS_HOURS_TIMEZONE
          value: "America/New_York"
        - name: BUSINESS_START_HOUR
          value: "7"
        - name: BUSINESS_END_HOUR
          value: "20"
        - name: BUSINESS_HOLIDAYS_COUNTRY
          value: "US"
        - name: BUSINESS_HOLIDAYS_SUBDIVISION
          value: ""
        - name: BUSINESS_HOLIDAYS
          value: "2024-12-24,2024-12-31"
```

#### Production Override
```yaml
# manifests/overlays/production/task-scheduler-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: task-scheduler
spec:
  template:
    spec:
      containers:
      - name: kubectl-runner
        env:
        - name: BUSINESS_HOURS_TIMEZONE
          value: "America/New_York"
        - name: BUSINESS_START_HOUR
          value: "7"
        - name: BUSINESS_END_HOUR
          value: "20"
        - name: BUSINESS_HOLIDAYS_COUNTRY
          value: "US"
        - name: BUSINESS_HOLIDAYS_SUBDIVISION
          value: ""
        - name: BUSINESS_HOLIDAYS
          value: "2024-12-24,2024-12-31"
```

### Docker Configuration

#### Environment File
```bash
# .env
BUSINESS_HOURS_TIMEZONE=America/New_York
BUSINESS_START_HOUR=7
BUSINESS_END_HOUR=20
BUSINESS_HOLIDAYS=2024-01-01,2024-07-04,2024-12-25
```

#### Docker Compose
```yaml
version: '3.8'
services:
  task-scheduler:
    image: task-scheduler-backend:latest
    environment:
      - BUSINESS_HOURS_TIMEZONE=America/New_York
      - BUSINESS_START_HOUR=7
      - BUSINESS_END_HOUR=20
      - BUSINESS_HOLIDAYS_COUNTRY=US
      - BUSINESS_HOLIDAYS_SUBDIVISION=
      - BUSINESS_HOLIDAYS=2024-12-24,2024-12-31
```

## Timezone Support

### Supported Timezones

The system supports all timezones available in the `pytz` library. Common examples:

- **US Timezones**: `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`
- **European Timezones**: `Europe/London`, `Europe/Paris`, `Europe/Berlin`, `Europe/Madrid`
- **Asian Timezones**: `Asia/Tokyo`, `Asia/Shanghai`, `Asia/Kolkata`, `Asia/Dubai`
- **UTC**: `UTC`

### Timezone Validation

If an invalid timezone is configured, the system will:
1. Log a warning message
2. Fall back to UTC timezone
3. Continue operating normally

## Holiday Configuration

### Automatic Holiday Detection (Recommended)

The system now supports automatic holiday detection using the `holidays` Python library. This provides official holidays for 100+ countries and their subdivisions.

#### Configuration Options

1. **Country-wide holidays**:
```yaml
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"  # United States federal holidays
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
```

2. **State/Province-specific holidays**:
```yaml
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: "NY"  # New York State holidays
```

3. **Hybrid configuration** (recommended for companies):
```yaml
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "US"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
- name: BUSINESS_HOLIDAYS
  value: "2024-12-24,2024-12-31"  # Additional company holidays
```

#### Supported Countries

Common country codes:
- `US` - United States (with state subdivisions: NY, CA, TX, etc.)
- `CA` - Canada (with province subdivisions: ON, BC, QC, etc.)
- `GB` - United Kingdom (with subdivisions: England, Scotland, Wales, Northern Ireland)
- `DE` - Germany (with state subdivisions)
- `FR` - France
- `AU` - Australia (with state/territory subdivisions)
- `JP` - Japan
- `MX` - Mexico
- `CO` - Colombia

For a complete list, see the [Holiday Configuration Guide](../kubectl-runner/src/HOLIDAY_CONFIGURATION_GUIDE.md).

### Colombia Holidays Configuration Tool

A dedicated configuration tool is available for Colombia holidays at `kubectl-runner/src/colombia_holidays_2026.py`. This tool generates complete holiday configurations for Colombia and provides deployment-ready environment variable configurations.

#### Usage

```bash
# Generate Colombia holidays configuration for 2026
cd kubectl-runner/src
python colombia_holidays_2026.py
```

#### Output

The tool provides:
1. **Complete list** of Colombia official holidays for 2026
2. **Automatic configuration** (recommended approach using country code)
3. **Manual configuration** (comma-separated dates for manual override)
4. **Complete deployment configuration** with timezone and business hours
5. **Monthly breakdown** of holidays for planning purposes

#### Example Output

```
Configuración de Festivos Colombia 2026
==================================================

Festivos oficiales de Colombia en 2026:
Total de festivos: 18

Listado detallado:
   2026-01-01 (Thursday): New Year's Day
   2026-01-12 (Monday): Epiphany
   2026-03-23 (Monday): Saint Joseph's Day
   ...

==================================================
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

### Manual Holiday Configuration

### Format

Holidays must be specified in `YYYY-MM-DD` format, comma-separated:

```bash
BUSINESS_HOLIDAYS=2024-01-01,2024-07-04,2024-12-25
```

### Common Holiday Sets

#### US Federal Holidays 2024
```bash
BUSINESS_HOLIDAYS=2024-01-01,2024-01-15,2024-02-19,2024-05-27,2024-06-19,2024-07-04,2024-09-02,2024-10-14,2024-11-11,2024-11-28,2024-12-25
```

#### UK Bank Holidays 2024
```bash
BUSINESS_HOLIDAYS=2024-01-01,2024-03-29,2024-04-01,2024-05-06,2024-05-27,2024-08-26,2024-12-25,2024-12-26
```

### Holiday Validation

Invalid holiday dates will:
1. Log a warning message
2. Be skipped (not included in holiday list)
3. Not affect other valid holidays

## Error Handling

### Configuration Errors

The system handles various configuration errors gracefully:

#### Invalid Timezone
```
WARNING: Unknown timezone 'Invalid/Timezone', falling back to UTC
```

#### Invalid Business Hours
```
ERROR: Invalid business hours: 25-30, using defaults
ERROR: Business start hour (20) must be before end hour (7)
```

#### Invalid Holiday Dates
```
WARNING: Invalid holiday date format: 2024-13-45
```

### Runtime Errors

All business hours operations include error handling:
- Invalid timestamp types default to current time
- Configuration parsing errors use safe defaults
- API endpoints return proper error responses

## Monitoring and Debugging

### Debug Logging

Enable debug logging to see detailed business hours decisions:

```python
logger.debug("Business hours check: 2024-01-15 14:30:00 EST (weekday=0, hour=14) -> weekend=False, outside_hours=False, holiday=False -> non_business=False")
```

### Health Checks

Use the business hours API endpoint for monitoring:

```bash
# Check if system is working
curl http://localhost:8080/api/business-hours

# Monitor for configuration issues
curl -s http://localhost:8080/api/business-hours | jq '.timezone'
```

### Common Issues

#### Wrong Timezone
**Symptom**: Business hours seem off by several hours
**Solution**: Check `BUSINESS_HOURS_TIMEZONE` configuration

#### Limits Not Enforced
**Symptom**: More than 5 namespaces active during non-business hours
**Solution**: Check business hours configuration and current status via API

#### Holidays Not Working
**Symptom**: Limits not enforced on configured holidays
**Solution**: Verify holiday date format (YYYY-MM-DD) and check logs for parsing errors

## Testing

### Manual Testing

```bash
# Test current status
curl http://localhost:8080/api/business-hours

# Test namespace activation during non-business hours
curl -X POST http://localhost:8080/api/namespaces/test-ns/activate \
  -H "Content-Type: application/json" \
  -d '{"cost_center": "CC-001", "requested_by": "test-user"}'
```

### Automated Testing

The system includes comprehensive tests:
- `test_business_hours_detection.py`: Core functionality testing
- `verify_business_hours.py`: Implementation verification

## Migration from Previous Version

### Breaking Changes
- None - maintains backward compatibility

### New Features
- Configurable timezone support
- Configurable business hours
- Manual holiday support
- **Automatic holiday detection** for 100+ countries using the `holidays` library
- State/province-specific holiday support
- Hybrid manual + automatic holiday configuration
- Enhanced logging and debugging
- Business hours status API endpoint with detailed holiday information

### Upgrade Steps
1. Update container image with new implementation
2. Add environment variables to deployment configuration
3. Restart application
4. Verify configuration via `/api/business-hours` endpoint

## Best Practices

### Configuration Management
- Use environment-specific configurations
- Document timezone choices for your organization
- Maintain holiday lists annually
- Test configuration changes in staging first

### Monitoring
- Monitor the business hours API endpoint
- Set up alerts for configuration warnings
- Review logs for parsing errors
- Validate business hours logic during deployment

### Security
- Limit access to configuration endpoints
- Use read-only access for monitoring
- Audit configuration changes
- Validate input formats

## Support

For issues or questions:
1. Check the business hours API endpoint for current status
2. Review application logs for configuration warnings
3. Verify environment variable configuration
4. Test with different timestamp formats
5. Consult the implementation documentation in `kubectl-runner/src/BUSINESS_HOURS_IMPLEMENTATION.md`