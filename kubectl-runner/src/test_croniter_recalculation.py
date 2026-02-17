#!/usr/bin/env python3
"""
Test script for croniter next_run recalculation after task execution
Tests that next_run is recalculated correctly based on the original scheduled time
"""

import pytest
from datetime import datetime, timedelta
from croniter import croniter


class TestCroniterRecalculation:
    """Test croniter recalculation logic for scheduled tasks"""
    
    def calculate_next_run(self, cron_expression, base_time=None):
        """
        Calculate next run time from cron expression
        This mimics the improved implementation in app.py
        """
        try:
            if not cron_expression:
                return None
            
            if base_time is None:
                base_time = datetime.now()
            
            cron = croniter(cron_expression, base_time)
            next_run = cron.get_next(datetime)
            
            return next_run.isoformat()
        except Exception as e:
            print(f"Error calculating next run: {e}")
            return None
    
    def test_recalculation_from_original_scheduled_time(self):
        """Test that next_run is calculated from original scheduled time, not current time"""
        cron_expression = "0 9 * * *"  # Every day at 9 AM
        
        # Original scheduled time: Jan 15 at 9 AM
        original_scheduled = datetime(2024, 1, 15, 9, 0, 0)
        
        # Task executed late at 9:05 AM
        execution_time = datetime(2024, 1, 15, 9, 5, 0)
        
        # Calculate next run from original scheduled time (correct approach)
        next_run_from_scheduled = self.calculate_next_run(cron_expression, original_scheduled)
        parsed_scheduled = datetime.fromisoformat(next_run_from_scheduled)
        
        # Calculate next run from execution time (incorrect approach)
        next_run_from_execution = self.calculate_next_run(cron_expression, execution_time)
        parsed_execution = datetime.fromisoformat(next_run_from_execution)
        
        # Both should give the same result: Jan 16 at 9 AM
        assert parsed_scheduled.day == 16
        assert parsed_scheduled.hour == 9
        assert parsed_execution.day == 16
        assert parsed_execution.hour == 9
        
    def test_recalculation_with_significant_delay(self):
        """Test recalculation when task execution is significantly delayed"""
        cron_expression = "0 9 * * *"  # Every day at 9 AM
        
        # Original scheduled time: Jan 15 at 9 AM
        original_scheduled = datetime(2024, 1, 15, 9, 0, 0)
        
        # Task executed very late at 11 AM (2 hours delay)
        execution_time = datetime(2024, 1, 15, 11, 0, 0)
        
        # Calculate from original scheduled time
        next_run = self.calculate_next_run(cron_expression, original_scheduled)
        parsed = datetime.fromisoformat(next_run)
        
        # Should still be Jan 16 at 9 AM
        assert parsed.day == 16
        assert parsed.hour == 9
        
    def test_recalculation_frequent_tasks(self):
        """Test recalculation for frequently scheduled tasks"""
        cron_expression = "*/5 * * * *"  # Every 5 minutes
        
        # Original scheduled: 9:00 AM
        original_scheduled = datetime(2024, 1, 15, 9, 0, 0)
        
        # Executed at 9:01 AM (1 minute delay)
        execution_time = datetime(2024, 1, 15, 9, 1, 0)
        
        # Calculate from original scheduled time
        next_run = self.calculate_next_run(cron_expression, original_scheduled)
        parsed = datetime.fromisoformat(next_run)
        
        # Should be 9:05 AM (next scheduled slot)
        assert parsed.hour == 9
        assert parsed.minute == 5
        
    def test_recalculation_missed_slot(self):
        """Test recalculation when a scheduled slot was missed"""
        cron_expression = "0 */2 * * *"  # Every 2 hours
        
        # Original scheduled: 8:00 AM
        original_scheduled = datetime(2024, 1, 15, 8, 0, 0)
        
        # Executed at 9:30 AM (missed the 8 AM slot)
        execution_time = datetime(2024, 1, 15, 9, 30, 0)
        
        # Calculate from original scheduled time
        next_run = self.calculate_next_run(cron_expression, original_scheduled)
        parsed = datetime.fromisoformat(next_run)
        
        # Should be 10:00 AM (next scheduled slot after 8 AM)
        assert parsed.hour == 10
        assert parsed.minute == 0
        
    def test_recalculation_weekday_task(self):
        """Test recalculation for weekday-only tasks"""
        cron_expression = "0 9 * * 1-5"  # Weekdays at 9 AM
        
        # Original scheduled: Friday 9 AM
        original_scheduled = datetime(2024, 1, 19, 9, 0, 0)  # Friday
        
        # Executed at 9:10 AM
        execution_time = datetime(2024, 1, 19, 9, 10, 0)
        
        # Calculate from original scheduled time
        next_run = self.calculate_next_run(cron_expression, original_scheduled)
        parsed = datetime.fromisoformat(next_run)
        
        # Should be Monday at 9 AM (skipping weekend)
        assert parsed.weekday() == 0  # Monday
        assert parsed.day == 22
        assert parsed.hour == 9
        
    def test_recalculation_preserves_consistency(self):
        """Test that recalculation maintains scheduling consistency"""
        cron_expression = "0 9 * * *"  # Daily at 9 AM
        
        # Simulate multiple executions with delays
        scheduled_times = []
        current_scheduled = datetime(2024, 1, 15, 9, 0, 0)
        
        for i in range(5):
            # Calculate next run from current scheduled time
            next_run = self.calculate_next_run(cron_expression, current_scheduled)
            parsed = datetime.fromisoformat(next_run)
            scheduled_times.append(parsed)
            
            # Move to next scheduled time
            current_scheduled = parsed
        
        # Verify all scheduled times are at 9 AM
        for scheduled in scheduled_times:
            assert scheduled.hour == 9
            assert scheduled.minute == 0
        
        # Verify they are consecutive days
        for i in range(len(scheduled_times) - 1):
            delta = scheduled_times[i + 1] - scheduled_times[i]
            assert delta.days == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
