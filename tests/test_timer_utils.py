# tests/test_timer_utils.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.timer_utils import TimerManager

class TestTimerManager(unittest.TestCase):
    """Tests for the TimerManager class in timer_utils.py"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a mock database connection
        self.mock_db = MagicMock()
        # Mock the logger
        self.mock_logger = MagicMock()
        # Create the TimerManager with mocked dependencies
        self.timer_manager = TimerManager(self.mock_db)
        self.timer_manager.logger = self.mock_logger
    
    @patch('app.utils.timer_utils.get_current_time')
    def test_start_timer(self, mock_get_time):
        """Test starting a timer"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T12:00:00"
        mock_get_time.return_value = fixed_time
        
        # Mock the database query results
        self.mock_db.execute.return_value.fetchone.return_value = {"status": "Pending"}
        
        # Call the function we're testing
        self.timer_manager.start(1)
        
        # Verify stop_all_active was called
        self.mock_logger.info.assert_any_call("Stopping all active timers")
        
        # Verify the new timer was inserted
        self.mock_db.execute.assert_any_call(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
            (1, fixed_time, 'auto')
        )
        
        # Verify job status was updated
        self.mock_db.execute.assert_any_call(
            'UPDATE job SET status = ?, last_active = ? WHERE id = ?',
            ('Active', fixed_time, 1)
        )
        
        # Verify commit was called
        self.mock_db.commit.assert_called()
    
    @patch('app.utils.timer_utils.get_current_time')
    def test_stop_timer(self, mock_get_time):
        """Test stopping a timer"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T13:00:00"
        mock_get_time.return_value = fixed_time
        
        # Mock get_active_timer to return an active timer
        self.mock_db.execute.return_value.fetchone.return_value = {"id": 5, "job_id": 1}
        
        # Call the function we're testing
        self.timer_manager.stop(1)
        
        # Verify the timer was updated
        self.mock_db.execute.assert_any_call(
            'UPDATE time_entry SET end_time = ? WHERE id = ?',
            (fixed_time, 5)
        )
        
        # Verify commit was called
        self.mock_db.commit.assert_called()
    
    @patch('app.utils.timer_utils.get_current_time')
    def test_stop_all_active(self, mock_get_time):
        """Test stopping all active timers"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T13:00:00"
        mock_get_time.return_value = fixed_time
        
        # Call the function we're testing
        self.timer_manager.stop_all_active()
        
        # Verify all timers were updated
        self.mock_db.execute.assert_called_with(
            'UPDATE time_entry SET end_time = ? WHERE end_time IS NULL',
            (fixed_time,)
        )
        
        # Verify commit was called
        self.mock_db.commit.assert_called()
