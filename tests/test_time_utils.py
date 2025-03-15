# tests/test_time_utils.py
import unittest
from datetime import datetime, timedelta
import sys
import os
import sqlite3

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.time_utils import (
    get_current_time, 
    format_time, 
    format_duration, 
    parse_time, 
    iso_to_datetime,
    get_time_difference_seconds
)

class TestTimeUtils(unittest.TestCase):
    """Tests for the time_utils.py utility functions"""
    
    def test_get_current_time(self):
        """Test get_current_time returns a properly formatted ISO time string"""
        time_str = get_current_time()
        # Verify it's a string
        self.assertIsInstance(time_str, str)
        # Verify it can be parsed as a datetime
        try:
            dt = datetime.fromisoformat(time_str)
            # Verify no microseconds (as we specify in our function)
            self.assertEqual(dt.microsecond, 0)
        except ValueError:
            self.fail("get_current_time() did not return a valid ISO format string")
    
    def test_format_time(self):
        """Test format_time converts times correctly"""
        # Test with ISO string
        iso_time = "2025-03-14T12:30:45"
        formatted = format_time(iso_time, "%Y-%m-%d %H:%M:%S")
        self.assertEqual(formatted, "2025-03-14 12:30:45")
        
        # Test with None
        self.assertEqual(format_time(None), "")
        
        # Test with invalid string
        self.assertEqual(format_time("invalid"), "Invalid time")
    
    def test_format_duration(self):
        """Test format_duration formats time durations correctly"""
        # Test with zero seconds
        self.assertEqual(format_duration(0), "00:00:00")
        
        # Test with normal values
        self.assertEqual(format_duration(3661), "01:01:01")  # 1 hour, 1 minute, 1 second
        self.assertEqual(format_duration(86399), "23:59:59")  # 23 hours, 59 minutes, 59 seconds
        
        # Test with negative (should handle gracefully)
        self.assertEqual(format_duration(-10), "00:00:00")
        
        # Test with None
        self.assertEqual(format_duration(None), "00:00:00")
    
    def test_parse_time(self):
        """Test parse_time converts string times to ISO format"""
        # Test valid time string
        time_str = "2025-03-14 12:30:45"
        iso_time = parse_time(time_str)
        self.assertEqual(iso_time, "2025-03-14T12:30:45")
        
        # Test empty string
        self.assertIsNone(parse_time(""))
        
        # Test None
        self.assertIsNone(parse_time(None))
        
        # Test invalid format
        self.assertIsNone(parse_time("not a time"))
    
    def test_iso_to_datetime(self):
        """Test iso_to_datetime converts ISO strings to datetime objects"""
        # Test valid ISO string
        dt = iso_to_datetime("2025-03-14T12:30:45")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 14)
        self.assertEqual(dt.hour, 12)
        self.assertEqual(dt.minute, 30)
        self.assertEqual(dt.second, 45)
        
        # Test None
        self.assertIsNone(iso_to_datetime(None))
        
        # Test invalid string
        self.assertIsNone(iso_to_datetime("not a time"))
    
    def test_get_time_difference_seconds(self):
        """Test get_time_difference_seconds calculates time differences correctly"""
        # Test with two times
        start = "2025-03-14T12:00:00"
        end = "2025-03-14T13:30:45"
        diff = get_time_difference_seconds(start, end)
        # 1 hour, 30 minutes, 45 seconds = 5445 seconds
        self.assertEqual(diff, 5445)
        
        # Test with invalid start time
        self.assertEqual(get_time_difference_seconds(None, end), 0)
        
        # Test with start time in future (should give negative value)
        future = datetime.now() + timedelta(hours=1)
        future_iso = future.isoformat(timespec='seconds')
        diff = get_time_difference_seconds(future_iso)
        self.assertLess(diff, 0)
