# tests/test_timer_utils.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime, timedelta, timezone
from flask import Flask

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to create mocks before importing the module
# Create a mock function that will replace the handle_errors decorator
def mock_handle_errors(f):
    return f

# Create a mock for get_active_timer function
def mock_get_active_timer(db):
    return {"id": 5, "job_id": 1, "start_time": "2025-03-14T12:00:00+00:00"}

# Create a mock for get_current_time
def mock_get_current_time():
    return "2025-03-14T13:00:00+00:00"

# Create a mock datetime class
class MockDateTime:
    @staticmethod
    def now(tz=None):
        mock_time = datetime(2025, 3, 14, 13, 0, 0)
        if tz is not None:
            mock_time = mock_time.replace(tzinfo=tz)
        return mock_time

    @staticmethod
    def fromisoformat(date_str):
        return datetime.fromisoformat(date_str)

# Now import and patch the modules
with patch('app.utils.error_utils.handle_errors', mock_handle_errors):
    with patch('app.utils.timer_utils.datetime', MockDateTime):
        with patch('app.utils.timer_utils.get_current_time', mock_get_current_time):
            with patch('app.utils.timer_utils.get_active_timer', mock_get_active_timer):
                from app.utils.timer_utils import TimerManager

class TestTimerManager(unittest.TestCase):
    """Tests for the TimerManager class in timer_utils.py"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a Flask app and push a context
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create a mock database connection
        self.mock_db = MagicMock()
        # Mock the logger
        self.mock_logger = MagicMock()
        
        # Create the TimerManager with mocked dependencies
        self.timer_manager = TimerManager(self.mock_db)
        self.timer_manager.logger = self.mock_logger
    
    def tearDown(self):
        """Clean up test environment after each test"""
        self.app_context.pop()
    
    @patch('app.utils.timer_utils.get_current_time')
    def test_start_timer(self, mock_get_time):
        """Test starting a timer"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T13:00:00+00:00"
        mock_get_time.return_value = fixed_time
        
        # Mock the database query results
        self.mock_db.execute.return_value.fetchone.return_value = {"status": "Pending"}
        
        # Call the function we're testing
        self.timer_manager.start(1)
        
        # Check that our mock was actually called
        mock_get_time.assert_called()
        
        # Verify commit was called
        self.mock_db.commit.assert_called()
    
    @patch('app.utils.timer_utils.get_current_time')
    @patch('app.utils.timer_utils.get_active_timer')
    def test_stop_timer(self, mock_get_active_timer, mock_get_time):
        """Test stopping a timer"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T13:00:00+00:00"
        mock_get_time.return_value = fixed_time
        
        # Mock get_active_timer to return an active timer with all required fields
        mock_get_active_timer.return_value = {"id": 5, "job_id": 1, "start_time": "2025-03-14T12:00:00+00:00"}
        
        # Call the function we're testing
        self.timer_manager.stop(1)
        
        # Just verify commit was called
        self.mock_db.commit.assert_called()
    
    @patch('app.utils.timer_utils.get_current_time')
    def test_stop_all_active(self, mock_get_time):
        """Test stopping all active timers"""
        # Set a fixed return value for get_current_time
        fixed_time = "2025-03-14T13:00:00+00:00"
        mock_get_time.return_value = fixed_time
        
        # Call the function we're testing
        self.timer_manager.stop_all_active()
        
        # Just verify commit was called
        self.mock_db.commit.assert_called()

if __name__ == "__main__":
    unittest.main()