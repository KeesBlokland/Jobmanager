#!/usr/bin/env python3
# tests/standalone_test_db.py

import unittest
import sqlite3
from datetime import datetime, timedelta, timezone

class TestDatabaseTimeCalculations(unittest.TestCase):
    """Tests for database time calculations in SQLite"""
    
    def setUp(self):
        """Set up a test database in memory"""
        # Create in-memory database
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        
        # Create test tables
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
        
        # Register custom SQL functions that mimic our app's functionality
        
        # Current time as ISO format
        self.db.create_function("current_iso_time", 0, 
                               lambda: datetime.now(timezone.utc).isoformat())
        
        # Time difference in hours
        def time_diff_hours(start_time, end_time=None):
            """Calculate time difference in hours between two timestamps."""
            try:
                # Parse start time
                if isinstance(start_time, str):
                    if 'Z' in start_time:
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    elif '+' in start_time and 'T' in start_time:
                        start_time = datetime.fromisoformat(start_time)
                    else:
                        start_time = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
                
                # Parse end time or use current time
                if end_time:
                    if isinstance(end_time, str):
                        if 'Z' in end_time:
                            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        elif '+' in end_time and 'T' in end_time:
                            end_time = datetime.fromisoformat(end_time)
                        else:
                            end_time = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.now(timezone.utc)
                
                # Calculate difference in seconds and convert to hours
                diff_seconds = (end_time - start_time).total_seconds()
                return diff_seconds / 3600
            except Exception as e:
                print(f"Error calculating time difference: {str(e)}")
                return 0
        
        self.db.create_function("time_diff_hours", 2, time_diff_hours)
        
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
        self.db.close()
    
    def test_time_entry_exact_hours(self):
        """Test calculating hours from fixed time entries"""
        # Insert a time entry with exactly 1 hour of work
        start_time = "2025-03-14T12:00:00+00:00"
        end_time = "2025-03-14T13:00:00+00:00"
        
        self.db.execute(
            'INSERT INTO time_entry (job_id, start_time, end_time, entry_type) VALUES (1, ?, ?, "auto")',
            (start_time, end_time)
        )
        self.db.commit()
        
        # Query using our custom function
        result = self.db.execute('''
            SELECT 
                time_diff_hours(start_time, end_time) as hours
            FROM time_entry WHERE job_id = 1
        ''').fetchone()
        
        # Should be exactly 1 hour
        self.assertEqual(result['hours'], 1.0)
    
    def test_time_entry_with_timezone(self):
        """Test with time entries using different timezone formats"""
        # Insert time entries with different timezone formats
        entries = [
            # Standard +00:00 format, 2 hours difference
            ("2025-03-14T12:00:00+00:00", "2025-03-14T14:00:00+00:00"),
            # Z format, 1 hour difference
            ("2025-03-14T12:00:00Z", "2025-03-14T13:00:00Z"),
            # Different timezones, 1 hour difference
            ("2025-03-14T12:00:00+00:00", "2025-03-14T14:00:00+01:00")
        ]
        
        for i, (start, end) in enumerate(entries):
            self.db.execute(
                'INSERT INTO time_entry (id, job_id, start_time, end_time, entry_type) VALUES (?, 1, ?, ?, "auto")',
                (i+2, start, end)
            )
        
        self.db.commit()
        
        # Query all entries
        results = self.db.execute('''
            SELECT 
                id, time_diff_hours(start_time, end_time) as hours
            FROM time_entry WHERE id > 1
            ORDER BY id
        ''').fetchall()
        
        # Check each result matches expected hours
        expected_hours = [2.0, 1.0, 1.0]
        for result, expected in zip(results, expected_hours):
            self.assertAlmostEqual(result['hours'], expected, delta=0.001)
    
    def test_calculate_job_total_hours(self):
        """Test calculating total hours for a job"""
        # Insert multiple time entries
        entries = [
            # 1 hour
            ("2025-03-14T12:00:00+00:00", "2025-03-14T13:00:00+00:00"),
            # 30 minutes
            ("2025-03-14T14:00:00+00:00", "2025-03-14T14:30:00+00:00"),
            # 45 minutes
            ("2025-03-14T16:00:00+00:00", "2025-03-14T16:45:00+00:00")
        ]
        
        for i, (start, end) in enumerate(entries):
            self.db.execute(
                'INSERT INTO time_entry (job_id, start_time, end_time, entry_type) VALUES (1, ?, ?, "auto")',
                (start, end)
            )
        
        self.db.commit()
        
        # Calculate total hours
        result = self.db.execute('''
            SELECT 
                SUM(time_diff_hours(start_time, end_time)) as total_hours
            FROM time_entry
            WHERE job_id = 1
        ''').fetchone()
        
        # Expected: 1 + 0.5 + 0.75 = 2.25 hours
        self.assertAlmostEqual(result['total_hours'], 2.25, delta=0.001)

if __name__ == "__main__":
    unittest.main()