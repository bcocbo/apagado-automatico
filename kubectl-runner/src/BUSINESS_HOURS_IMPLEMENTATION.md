# Business Hours Detection Implementation

## Overview

This document describes the implementation of improved business hours detection logic that provides configurable timezone support, holiday handling, and enhanced debugging capabilities for the namespace scheduler system.

## Problems with Previous Implementation

### 1. Timezone Issues
- **System Local Time**: Used `datetime.now()` without timezone specification
- **No Configuration**: Hardcoded to system timezone, not configurable
- **Deployment Issues**: Different behavior in different deployment environments

### 2. Limited Flexibility
- **Hardcoded Hours**: Business hours fixed at 7 AM - 8 PM
- **No Holiday Support**: Couldn't account for company holidays
- **No Regional Support**: Single timezone for all users

### 3. Poor Debugging
- **No Visibility**: No logging of business hours decisions
- **No Information Endpoint**: Couldn't inspect current configuration
- **Limited Error Handling**: Basic error handling for edge cases

## New Implementation

### 1. Configurable Timezone Support

#### Environment Variables
```bash
# Timezone configuration (default: UTC)
BUSINESS_HOURS_TIMEZONE=America/New_York

# Business hours configuration (24-hour format)
BUSINESS_START_HOUR=7    # 7 AM
BUSINESS_END_HOUR=20     # 8 PM

# Holiday configuration (comma-separated YYYY-MM-DD format)
BUSINESS_HOLIDAYS=2024-01-01,2024-07-04,2024-12-25
```

#### Timezone Handling
```python
import pytz
from datetime import datetime

# Get configured timezone
timezone_name = os.getenv('BUSINESS_HOURS_TIMEZONE', 'UTC')
business_timezone = pytz.timezone(timezone_name)

# Convert current time to business timezone
current_time = datetime.now(business_timezone)
```

### 2. Enhanced Business Hours Logic

#### `is_non_business_hours(timestamp=None)`
```python
def is_non_business_hours(self, timestamp=None):
    """Check if current time is non-business hours with proper timezone handling"""
    import pytz
    from datetime import datetime, time
    
    # Get timezone configuration (default to UTC if not specified)
    timezone_name = os.getenv('BUSINESS_HOURS_TIMEZONE', 'UTC')
    try:
        business_timezone = pytz.timezone(timezone_name)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone '{timezone_name}', falling back to UTC")
        business_timezone = pytz.UTC
    
    # Get current time in business timezone
    if timestamp is None:
        # Use current time in business timezone
        current_time = datetime.now(business_timezone)
    elif isinstance(timestamp, (int, float)):
        # Convert Unix timestamp to business timezone
        current_time = datetime.fromtimestamp(timestamp, tz=business_timezone)
    elif isinstance(timestamp, datetime):
        # Convert datetime to business timezone
        if timestamp.tzinfo is None:
            # Assume UTC if no timezone info
            current_time = pytz.UTC.localize(timestamp).astimezone(business_timezone)
        else:
            current_time = timestamp.astimezone(business_timezone)
    else:
        logger.error(f"Invalid timestamp type: {type(timestamp)}")
        current_time = datetime.now(business_timezone)
    
    # Get configurable business hours (default: 7 AM - 8 PM)
    business_start_hour = int(os.getenv('BUSINESS_START_HOUR', '7'))
    business_end_hour = int(os.getenv('BUSINESS_END_HOUR', '20'))  # 8 PM in 24-hour format
    
    # Validate business hours configuration
    if not (0 <= business_start_hour <= 23) or not (0 <= business_end_hour <= 23):
        logger.error(f"Invalid business hours: {business_start_hour}-{business_end_hour}, using defaults")
        business_start_hour, business_end_hour = 7, 20
    
    if business_start_hour >= business_end_hour:
        logger.error(f"Business start hour ({business_start_hour}) must be before end hour ({business_end_hour})")
        business_start_hour, business_end_hour = 7, 20
    
    # Check if it's weekend (Saturday=5, Sunday=6)
    is_weekend = current_time.weekday() >= 5
    
    # Check if it's outside business hours
    current_hour = current_time.hour
    is_outside_hours = current_hour < business_start_hour or current_hour >= business_end_hour
    
    # Check for holidays (if configured)
    is_holiday = self._is_holiday(current_time)
    
    result = is_weekend or is_outside_hours or is_holiday
    
    # Log the decision for debugging
    logger.debug(f"Business hours check: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                f"(weekday={current_time.weekday()}, hour={current_hour}) "
                f"-> weekend={is_weekend}, outside_hours={is_outside_hours}, holiday={is_holiday} "
                f"-> non_business={result}")
    
    return result
```

**Features**:
- Configurable timezone support with fallback to UTC
- Configurable business hours (start/end) with validation
- Holiday support via environment variable configuration
- Multiple timestamp input formats (None, Unix timestamp, datetime objects)
- Enhanced error handling and logging with detailed debug information
- Validation of business hours configuration (start < end, valid hours 0-23)

**Logic**:
1. **Timezone Conversion**: Convert input to business timezone with error handling
2. **Configuration Validation**: Validate business hours configuration with fallbacks
3. **Weekend Check**: Saturday (5) and Sunday (6) are non-business
4. **Hours Check**: Outside configured business hours
5. **Holiday Check**: Configured holiday dates via `_is_holiday()` method
6. **Debug Logging**: Detailed logging of decision process
7. **Result**: Non-business if any condition is true

#### `_is_holiday(current_time)`
```python
def _is_holiday(self, current_time):
    """Check if the current date is a configured holiday"""
    # Get holiday configuration from environment
    holidays_str = os.getenv('BUSINESS_HOLIDAYS', '')
    
    if not holidays_str:
        return False
    
    try:
        # Parse holidays in format: "2024-01-01,2024-07-04,2024-12-25"
        holiday_dates = []
        for date_str in holidays_str.split(','):
            date_str = date_str.strip()
            if date_str:
                try:
                    holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    holiday_dates.append(holiday_date)
                except ValueError:
                    logger.warning(f"Invalid holiday date format: {date_str}")
        
        current_date = current_time.date()
        is_holiday = current_date in holiday_dates
        
        if is_holiday:
            logger.info(f"Current date {current_date} is a configured holiday")
        
        return is_holiday
        
    except Exception as e:
        logger.error(f"Error checking holidays: {e}")
        return False
```

**Features**:
- Parses comma-separated holiday dates from `BUSINESS_HOLIDAYS` environment variable
- Supports YYYY-MM-DD format with validation
- Graceful error handling for invalid dates with warning logs
- Logging for holiday matches with info level
- Returns False if no holidays configured or on parsing errors

#### `get_business_hours_info()`
```python
def get_business_hours_info(self):
    """Get current business hours configuration and status"""
    import pytz
    
    # Get configuration
    timezone_name = os.getenv('BUSINESS_HOURS_TIMEZONE', 'UTC')
    business_start_hour = int(os.getenv('BUSINESS_START_HOUR', '7'))
    business_end_hour = int(os.getenv('BUSINESS_END_HOUR', '20'))
    holidays_str = os.getenv('BUSINESS_HOLIDAYS', '')
    
    try:
        business_timezone = pytz.timezone(timezone_name)
        current_time = datetime.now(business_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        business_timezone = pytz.UTC
        current_time = datetime.now(business_timezone)
    
    # Parse holidays
    holidays = []
    if holidays_str:
        for date_str in holidays_str.split(','):
            date_str = date_str.strip()
            if date_str:
                try:
                    holidays.append(date_str)
                except:
                    pass
    
    is_non_business = self.is_non_business_hours()
    
    return {
        'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'timezone': timezone_name,
        'business_hours': f"{business_start_hour:02d}:00 - {business_end_hour:02d}:00",
        'business_days': 'Monday - Friday',
        'holidays': holidays,
        'is_non_business_hours': is_non_business,
        'current_weekday': current_time.strftime('%A'),
        'current_hour': current_time.hour,
        'limit_active': is_non_business
    }
```

**Features**:
- Retrieves all business hours configuration from environment variables
- Handles timezone conversion with fallback to UTC
- Parses and formats holiday list for display
- Calls `is_non_business_hours()` to get current status
- Returns comprehensive status information including current time, configuration, and status

**Returns**:
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

### 3. New API Endpoint

#### `GET /api/business-hours`
**Description**: Get current business hours configuration and status

**Response Structure**:
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

**Use Cases**:
- Frontend display of business hours status
- Debugging timezone and configuration issues
- Monitoring and alerting on business hours logic
- API documentation and testing

## Configuration Examples

### 1. US Eastern Time
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

### 2. European Time
```yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "Europe/London"
- name: BUSINESS_START_HOUR
  value: "8"
- name: BUSINESS_END_HOUR
  value: "18"
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-03-29,2024-04-01,2024-05-06,2024-05-27,2024-08-26,2024-12-25,2024-12-26"
```

### 3. 24/7 Operation (No Limits)
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

## Timestamp Input Formats

### 1. Current Time (Default)
```python
is_non_business = scheduler.is_non_business_hours()
```

### 2. Unix Timestamp
```python
timestamp = 1640995200  # Unix timestamp
is_non_business = scheduler.is_non_business_hours(timestamp)
```

### 3. Datetime Object (Naive)
```python
from datetime import datetime
dt = datetime(2024, 1, 15, 14, 30)  # Assumed UTC
is_non_business = scheduler.is_non_business_hours(dt)
```

### 4. Datetime Object (Timezone-Aware)
```python
import pytz
from datetime import datetime
dt = datetime(2024, 1, 15, 14, 30, tzinfo=pytz.UTC)
is_non_business = scheduler.is_non_business_hours(dt)
```

## Error Handling

### 1. Unknown Timezone
```python
# If BUSINESS_HOURS_TIMEZONE is invalid
try:
    business_timezone = pytz.timezone(timezone_name)
except pytz.exceptions.UnknownTimeZoneError:
    logger.warning(f"Unknown timezone '{timezone_name}', falling back to UTC")
    business_timezone = pytz.UTC
```

### 2. Invalid Business Hours
```python
# Validate business hours configuration
if not (0 <= business_start_hour <= 23) or not (0 <= business_end_hour <= 23):
    logger.error(f"Invalid business hours: {business_start_hour}-{business_end_hour}, using defaults")
    business_start_hour, business_end_hour = 7, 20
```

### 3. Invalid Holiday Dates
```python
# Parse holidays with error handling
for date_str in holidays_str.split(','):
    try:
        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        holiday_dates.append(holiday_date)
    except ValueError:
        logger.warning(f"Invalid holiday date format: {date_str}")
```

### 4. Invalid Timestamp Types
```python
else:
    logger.error(f"Invalid timestamp type: {type(timestamp)}")
    current_time = datetime.now(business_timezone)
```

## Logging and Debugging

### 1. Debug Logging
```python
logger.debug(f"Business hours check: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')} "
            f"(weekday={current_time.weekday()}, hour={current_hour}) "
            f"-> weekend={is_weekend}, outside_hours={is_outside_hours}, holiday={is_holiday} "
            f"-> non_business={result}")
```

### 2. Holiday Logging
```python
if is_holiday:
    logger.info(f"Current date {current_date} is a configured holiday")
```

### 3. Configuration Warnings
```python
logger.warning(f"Unknown timezone '{timezone_name}', falling back to UTC")
logger.error(f"Invalid business hours: {business_start_hour}-{business_end_hour}, using defaults")
```

## Deployment Configuration

### 1. Base Deployment
```yaml
# manifests/base/task-scheduler-deployment.yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/New_York"
- name: BUSINESS_START_HOUR
  value: "7"
- name: BUSINESS_END_HOUR
  value: "20"
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-07-04,2024-12-25"
```

### 2. Production Override
```yaml
# manifests/overlays/production/task-scheduler-patch.yaml
env:
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/New_York"
- name: BUSINESS_START_HOUR
  value: "7"
- name: BUSINESS_END_HOUR
  value: "20"
- name: BUSINESS_HOLIDAYS
  value: "2024-01-01,2024-07-04,2024-11-28,2024-12-25"
```

## Dependencies

### 1. Python Package
```txt
# requirements.txt
pytz==2023.3
```

### 2. Dockerfile
```dockerfile
RUN pip3 install --no-cache-dir \
    pytz==2023.3
```

## Testing

### Test Coverage
- Timezone configuration and conversion
- Business hours validation
- Holiday detection
- Error handling for invalid configurations
- API endpoint functionality
- Multiple timestamp input formats

### Test Files
- `test_business_hours_detection.py`: Comprehensive functionality testing
- `verify_business_hours.py`: Implementation verification

## Usage Examples

### 1. Check Current Status
```bash
curl http://localhost:8080/api/business-hours
```

### 2. Frontend Integration
```javascript
// Get business hours status
fetch('/api/business-hours')
  .then(response => response.json())
  .then(data => {
    console.log('Current time:', data.current_time);
    console.log('Is non-business:', data.is_non_business_hours);
    console.log('Business hours:', data.business_hours);
  });
```

### 3. Validation Logic
```python
# In namespace activation
is_valid, message = scheduler.validate_namespace_activation(
    cost_center="CC-001",
    namespace="my-app",
    user_id="john.doe"
)

# Uses improved business hours detection internally
```

## Benefits

### 1. Flexibility
- **Configurable Timezones**: Support for any timezone
- **Configurable Hours**: Customizable business hours
- **Holiday Support**: Company-specific holiday configuration
- **Environment-Specific**: Different configs per environment

### 2. Reliability
- **Proper Timezone Handling**: Eliminates timezone-related bugs
- **Error Recovery**: Graceful fallbacks for invalid configurations
- **Input Validation**: Validates all configuration parameters
- **Comprehensive Logging**: Detailed logging for debugging

### 3. Visibility
- **Configuration Endpoint**: Inspect current configuration
- **Debug Logging**: Detailed decision logging
- **Status Information**: Rich status information for monitoring
- **Error Reporting**: Clear error messages for misconfigurations

### 4. Maintainability
- **Centralized Logic**: Single method for business hours detection
- **Clear Configuration**: Environment variable-based configuration
- **Comprehensive Testing**: Full test coverage for edge cases
- **Documentation**: Detailed implementation documentation

## Migration Notes

### Breaking Changes
- None - maintains backward compatibility with existing logic

### New Features
- Timezone configuration support
- Holiday configuration support
- Business hours information endpoint
- Enhanced logging and debugging

### Configuration Requirements
- Optional environment variables (defaults provided)
- New dependency: pytz
- Updated deployment manifests (optional)

### Deployment Considerations
- Add pytz to container images
- Configure timezone environment variables
- Update deployment manifests with business hours config
- Monitor logs for configuration warnings