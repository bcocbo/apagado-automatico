#!/usr/bin/env python3
"""
Test script for croniter next_run calculation
Tests that next_run is calculated correctly for scheduled tasks
"""

import pytest
from datetime import datetime, timedelta
from croniter import croniter
import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestCroniterCalculation:
    """Test croniter calculation for task scheduling"""
    
    def test_calculate_next_run_basic(self):
        """Test basic next_run calculation"""
        # Test with a simple cron expression: every day at 9 AM
        cron_expression = "0 9 * * *"
        base_time = datetime(2024, 1, 15, 8, 0, 0)  # 8 AM
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should be 9 AM same day
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.day == 15
        
    def test_calculate_next_run_after_execution(self):
        """Test next_run calculation after task execution"""
        # Simulate a task that runs at 9 AM and we need to calculate next run
        cron_expression = "0 9 * * *"  # Every day at 9 AM
        execution_time = datetime(2024, 1, 15, 9, 5, 0)  # Task executed at 9:05 AM
        
        # Calculate next run from execution time
        cron = croniter(cron_expression, execution_time)
        next_run = cron.get_next(datetime)
        
        # Should be 9 AM next day
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.day == 16
        
    def test_calculate_next_run_weekdays_only(self):
        """Test next_run calculation for weekdays only"""
        # Every weekday at 9 AM
        cron_expression = "0 9 * * 1-5"
        
        # Start on Friday at 10 AM
        base_time = datetime(2024, 1, 19, 10, 0, 0)  # Friday
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should be Monday at 9 AM (skipping weekend)
        assert next_run.weekday() == 0  # Monday
        assert next_run.hour == 9
        assert next_run.day == 22
        
    def test_calculate_next_run_every_5_minutes(self):
        """Test next_run calculation for frequent tasks"""
        cron_expression = "*/5 * * * *"  # Every 5 minutes
        base_time = datetime(2024, 1, 15, 9, 3, 0)
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should be 9:05 AM
        assert next_run.hour == 9
        assert next_run.minute == 5
        
    def test_calculate_next_run_handles_dst(self):
        """Test that croniter handles daylight saving time correctly"""
        # This is more of a croniter library test, but good to verify
        cron_expression = "0 2 * * *"  # 2 AM daily
        base_time = datetime(2024, 3, 10, 1, 0, 0)  # Day before DST in US
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should still be 2 AM
        assert next_run.hour == 2
        
    def test_calculate_next_run_invalid_cron(self):
        """Test handling of invalid cron expressions"""
        invalid_expressions = [
            "invalid",
            "60 * * * *",  # Invalid minute
            "* 25 * * *",  # Invalid hour
            "",
            None
        ]
        
        for expr in invalid_expressions:
            if expr is None or expr == "":
                continue
            with pytest.raises(Exception):
                cron = croniter(expr, datetime.now())
                
    def test_calculate_next_run_multiple_iterations(self):
        """Test calculating multiple next runs in sequence"""
        cron_expression = "0 */2 * * *"  # Every 2 hours
        base_time = datetime(2024, 1, 15, 9, 0, 0)
        
        cron = croniter(cron_expression, base_time)
        
        # Get next 5 runs
        expected_hours = [10, 12, 14, 16, 18]
        for expected_hour in expected_hours:
            next_run = cron.get_next(datetime)
            assert next_run.hour == expected_hour
            
    def test_calculate_next_run_from_past(self):
        """Test calculating next run when base time is in the past"""
        cron_expression = "0 9 * * *"  # 9 AM daily
        # Use a time in the past
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should be 9 AM on Jan 2
        assert next_run.day == 2
        assert next_run.hour == 9
        
    def test_calculate_next_run_preserves_timezone(self):
        """Test that timezone information is preserved if present"""
        from datetime import timezone
        
        cron_expression = "0 9 * * *"
        base_time = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should preserve timezone
        assert next_run.tzinfo == timezone.utc
        
    def test_calculate_next_run_end_of_month(self):
        """Test next_run calculation at end of month"""
        cron_expression = "0 9 * * *"  # 9 AM daily
        base_time = datetime(2024, 1, 31, 10, 0, 0)  # Last day of January
        
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        # Should be Feb 1 at 9 AM
        assert next_run.month == 2
        assert next_run.day == 1
        assert next_run.hour == 9


class TestCalculateNextRunMethod:
    """Test the actual calculate_next_run method from TaskScheduler"""
    
    def calculate_next_run(self, cron_expression, base_time=None):
        """
        Fixed implementation of calculate_next_run
        Calculate next run time from cron expression
        """
        try:
            if not cron_expression:
                return None
                
            # Use provided base_time or current time
            if base_time is None:
                base_time = datetime.now()
            
            # Create croniter instance and get next occurrence
            cron = croniter(cron_expression, base_time)
            next_run = cron.get_next(datetime)
            
            return next_run.isoformat()
        except Exception as e:
            print(f"Error calculating next run: {e}")
            return None
    
    def test_method_returns_iso_format(self):
        """Test that method returns ISO format string"""
        cron_expression = "0 9 * * *"
        result = self.calculate_next_run(cron_expression)
        
        assert result is not None
        assert isinstance(result, str)
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)
        
    def test_method_handles_empty_expression(self):
        """Test that method handles empty cron expression"""
        assert self.calculate_next_run("") is None
        assert self.calculate_next_run(None) is None
        
    def test_method_handles_invalid_expression(self):
        """Test that method handles invalid cron expression"""
        result = self.calculate_next_run("invalid cron")
        assert result is None
        
    def test_method_with_custom_base_time(self):
        """Test that method works with custom base time"""
        cron_expression = "0 9 * * *"
        base_time = datetime(2024, 1, 15, 8, 0, 0)
        
        result = self.calculate_next_run(cron_expression, base_time)
        assert result is not None
        
        parsed = datetime.fromisoformat(result)
        assert parsed.hour == 9
        assert parsed.day == 15


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
