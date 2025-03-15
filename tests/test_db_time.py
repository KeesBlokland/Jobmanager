# tests/test_db_time.py
import unittest
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from app import create_app

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
        # Insert a time entry that started 1 hour ago
        start_time = (datetime.now() - timedelta(hours=1)).isoformat()
        self.db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (1, ?, "auto")',
            (start_time,)
        )
        self.db.commit()
        
        # Query 1: Using datetime('now')
        result1 = self.db.execute('''
            SELECT (julianday(datetime('now')) - julianday(start_time)) * 24 as hours
            FROM time_entry WHERE job_id = 1
        ''').fetchone()
        
        # Query 2: Using datetime('now', 'localtime')
        result2 = self.db.execute('''
            SELECT (julianday(datetime('now', 'localtime')) - julianday(start_time)) * 24 as hours
            FROM time_entry WHERE job_id = 1
        ''').fetchone()
        
        # Get the actual difference without SQLite
        start_dt = datetime.fromisoformat(start_time)
        actual_diff = (datetime.now() - start_dt).total_seconds() / 3600
        
        # For debugging
        print(f"UTC calculation: {result1['hours']}")
        print(f"Localtime calculation: {result2['hours']}")
        print(f"Python calculation: {actual_diff}")
        
        # Assert that the localtime calculation is closer to the actual difference
        self.assertAlmostEqual(result2['hours'], actual_diff, delta=0.1)
        
        # Test time calculation with an active timer and get_job_with_hours query pattern
        query = '''
            WITH job_hours AS (
                SELECT job_id,
                    SUM((julianday(COALESCE(end_time, datetime('now', 'localtime'))) - 
                         julianday(start_time)) * 24) as hours
                FROM time_entry
                GROUP BY job_id
            )
            SELECT 
                job.*, 
                customer.name as customer_name,
                COALESCE(job_hours.hours, 0) as accumulated_hours
            FROM job 
            JOIN customer ON job.customer_id = customer.id 
            LEFT JOIN job_hours ON job_hours.job_id = job.id
            WHERE job.id = 1
        '''
        
        job_result = self.db.execute(query).fetchone()
        self.assertIsNotNone(job_result)
        self.assertAlmostEqual(job_result['accumulated_hours'], actual_diff, delta=0.1)
