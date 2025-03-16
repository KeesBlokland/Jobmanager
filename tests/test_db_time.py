# tests/test_db_time.py
import unittest
import sys
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create a mock for profile_manager to avoid circular imports
mock_profile_manager = MagicMock()
mock_profile_manager.get_time_offset_minutes.return_value = 0
mock_profile_manager.get_profile.return_value = {}
mock_profile_manager.init_app = lambda app: None

# Patch the profile_manager module before importing app
with patch.dict('sys.modules', {
    'app.utils.profile_utils': MagicMock(profile_manager=mock_profile_manager)
}):
    # Now we can import create_app
    from app import create_app

class TestDatabaseTimeCalculations(unittest.TestCase):
    """Tests for database time calculations"""
    
    def setUp(self):
        # Set up Flask app context
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Set up database
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        
        # Create the necessary tables
        self.db.executescript('''
            CREATE TABLE job (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                description TEXT,
                status TEXT,
                creation_date TEXT,
                last_active TEXT
            );
            
            CREATE TABLE time_entry (
                id INTEGER PRIMARY KEY,
                job_id INTEGER,
                start_time TEXT,
                end_time TEXT,
                entry_type TEXT
            );
            
            CREATE TABLE customer (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
        ''')
        
        # Add test data
        self.db.execute('INSERT INTO customer (id, name) VALUES (1, "Test Customer")')
        now = datetime.now().isoformat()
        self.db.execute(
            'INSERT INTO job (id, customer_id, description, status, creation_date) VALUES (1, 1, "Test Job", "Active", ?)',
            (now,)
        )
        self.db.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
        self.db.close()
    
    def test_time_calculation_consistency(self):
        """Test that time calculations are consistent between different query methods"""
        # Insert a time entry with a fixed start time (1 hour ago)
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        self.db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (1, ?, "auto")',
            (one_hour_ago,)
        )
        self.db.commit()
        
        # Add SQL functions we need for our tests
        self.db.create_function("current_iso_time", 0, lambda: datetime.now(timezone.utc).isoformat())
        
        def time_diff_hours(start_time, end_time=None):
            """Calculate time difference in hours between two timestamps."""
            try:
                # Parse start time with timezone handling
                if isinstance(start_time, str):
                    if 'Z' in start_time:
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    elif '+' in start_time or '-' in start_time and 'T' in start_time:
                        start_time = datetime.fromisoformat(start_time)
                    else:
                        start_time = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
                
                # Parse end time with timezone handling
                if end_time:
                    if isinstance(end_time, str):
                        if 'Z' in end_time:
                            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        elif '+' in end_time or '-' in end_time and 'T' in end_time:
                            end_time = datetime.fromisoformat(end_time)
                        else:
                            end_time = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.now(timezone.utc)
                
                # Direct time difference calculation
                diff_seconds = (end_time - start_time).total_seconds()
                return diff_seconds / 3600
            except Exception as e:
                print(f"Error calculating time difference: {str(e)}")
                return 0
        
        self.db.create_function("time_diff_hours", 2, time_diff_hours)
        
        # Test our custom SQL function
        result = self.db.execute('''
            SELECT 
                time_diff_hours(start_time, current_iso_time()) as hours
            FROM time_entry WHERE job_id = 1
        ''').fetchone()
        
        # Ensure the result is roughly 1 hour (with some tolerance for test execution time)
        hours = result['hours']
        self.assertGreater(hours, 0.9)  # Should be close to 1 hour
        self.assertLess(hours, 1.1)  # But not much more
        
        # Get the actual difference for comparison
        start_dt = datetime.fromisoformat(one_hour_ago)
        current_dt = datetime.now(timezone.utc if start_dt.tzinfo else None)
        actual_diff = (current_dt - start_dt).total_seconds() / 3600
        
        print(f"SQL calculation: {hours}")
        print(f"Python calculation: {actual_diff}")
        
        # The two calculations should be similar
        self.assertAlmostEqual(hours, actual_diff, delta=0.1)

if __name__ == "__main__":
    unittest.main()