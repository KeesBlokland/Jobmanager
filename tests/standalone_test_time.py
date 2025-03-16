#!/usr/bin/env python3
# tests/standalone_test_time.py

import unittest
from datetime import datetime, timedelta, timezone
import os
import sys

class TestTimeUtils(unittest.TestCase):
    """Simple standalone tests for time utility functions"""
    
    def test_iso_format_conversion(self):
        """Test converting between ISO format and datetime"""
        # Get current time
        now = datetime.now(timezone.utc)
        
        # Convert to ISO format
        iso_string = now.isoformat()
        
        # Convert back to datetime
        parsed_datetime = datetime.fromisoformat(iso_string)
        
        # They should be equal
        self.assertEqual(now, parsed_datetime)
    
    def test_time_difference_calculation(self):
        """Test calculating time differences"""
        # Create two times 1 hour apart
        start_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 3, 14, 13, 0, 0, tzinfo=timezone.utc)
        
        # Calculate difference in seconds
        diff_seconds = (end_time - start_time).total_seconds()
        
        # Should be 3600 seconds (1 hour)
        self.assertEqual(diff_seconds, 3600)
        
        # Calculate difference in hours
        diff_hours = diff_seconds / 3600
        
        # Should be 1.0 hour
        self.assertEqual(diff_hours, 1.0)
    
    def test_timezone_handling(self):
        """Test handling of different timezones"""
        # Create a UTC timestamp
        utc_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        
        # Create a timestamp in a different timezone (UTC+2)
        tz_offset = timezone(timedelta(hours=2))
        local_time = datetime(2025, 3, 14, 14, 0, 0, tzinfo=tz_offset)
        
        # When converted to the same timezone, they should be equal
        self.assertEqual(utc_time.astimezone(tz_offset), local_time)
        self.assertEqual(local_time.astimezone(timezone.utc), utc_time)
    
    def test_iso_format_timezone(self):
        """Test ISO format with different timezone representations"""
        # Create a UTC timestamp
        utc_time = datetime(2025, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        
        # Different ways to represent the same UTC time in ISO format
        iso_formats = [
            "2025-03-14T12:00:00+00:00",  # Explicit +00:00
            "2025-03-14T12:00:00Z",       # Z suffix
            "2025-03-14T13:00:00+01:00"   # Different timezone
        ]
        
        for iso_str in iso_formats:
            # Parse the ISO string
            parsed_time = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            
            # Convert to UTC for comparison
            if parsed_time.tzinfo is not None:
                parsed_time = parsed_time.astimezone(timezone.utc)
                
            # Should be equal to our reference UTC time
            self.assertEqual(parsed_time, utc_time)

if __name__ == "__main__":
    unittest.main()