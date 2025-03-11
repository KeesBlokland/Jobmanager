#!/usr/bin/env python3
# db_init.py
# Enhanced database initialization with demo data

import os
import sqlite3
from datetime import datetime, timedelta
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('db_initializer')

def get_current_time():
    """Get current time as ISO format string."""
    return datetime.now().isoformat()

def create_tables(db_path):
    """Create all database tables if they don't exist."""
    logger.info(f"Creating database tables in {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read the schema SQL
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'schema.sql')
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Execute the schema SQL
    conn.executescript(schema_sql)
    conn.commit()
    logger.info("Database tables created successfully")
    
    return conn

def insert_demo_data(conn):
    """Insert demonstration data into the database."""
    logger.info("Inserting demonstration data")
    cursor = conn.cursor()
    
    # Get the current time for timestamps
    now = get_current_time()
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    last_week = (datetime.now() - timedelta(days=7)).isoformat()
    
    # Insert demo customers
    customers = [
        ('ABC Renovations', 'contact@abcrenovations.com', '+49 123 456789', 'Hauptstrasse 1', 'Berlin', '10115', 'DE', 'Net 14 days', 'Regular customer, prefers email contact'),
        ('Smith Family', 'jsmith@example.com', '+49 987 654321', 'Gartenweg 5', 'Munich', '80331', 'DE', 'Payment upon completion', 'Weekend appointments only')
    ]
    
    customer_ids = []
    for customer in customers:
        cursor.execute('''
            INSERT INTO customer (name, email, phone, street, city, postal_code, country, payment_terms, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', customer)
        customer_ids.append(cursor.lastrowid)
    
    # Insert demo jobs
    jobs = [
        (customer_ids[0], 'Bathroom renovation - Phase 1', 'Active', last_week, 45.00, 20.0),
        (customer_ids[0], 'Kitchen cabinet installation', 'Pending', now, 45.00, 8.0),
        (customer_ids[1], 'Garden shed construction', 'Completed', last_week, 40.00, 12.0)
    ]
    
    job_ids = []
    for job in jobs:
        cursor.execute('''
            INSERT INTO job (customer_id, description, status, creation_date, base_rate, estimated_hours)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', job)
        job_ids.append(cursor.lastrowid)
    
    # Update last_active for the active job
    cursor.execute('UPDATE job SET last_active = ? WHERE id = ?', (now, job_ids[0]))
    
    # Insert demo time entries for the active job
    time_entries = [
        (job_ids[0], last_week, (datetime.now() - timedelta(days=7, hours=3)).isoformat(), 'auto'),
        (job_ids[0], yesterday, (datetime.now() - timedelta(days=1, hours=4)).isoformat(), 'auto'),
        (job_ids[0], now, None, 'auto')  # Currently active timer
    ]
    
    for entry in time_entries:
        cursor.execute('''
            INSERT INTO time_entry (job_id, start_time, end_time, entry_type)
            VALUES (?, ?, ?, ?)
        ''', entry)
    
    # Insert demo materials
    materials = [
        (job_ids[0], 'Cement (25kg bag)', 2, 12.50, now),
        (job_ids[0], 'Ceramic tiles (1 sqm)', 10, 15.75, now),
        (job_ids[2], 'Wood panels (standard)', 15, 8.25, last_week)
    ]
    
    for material in materials:
        cursor.execute('''
            INSERT INTO job_material (job_id, material, quantity, price, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', material)
    
    # Insert demo job notes
    notes = [
        (job_ids[0], 'Customer prefers work to be done during morning hours.', last_week),
        (job_ids[0], 'Additional tiles needed, customer will provide them next week.', now),
        (job_ids[2], 'Project completed on schedule, customer very satisfied.', last_week)
    ]
    
    for note in notes:
        cursor.execute('''
            INSERT INTO job_note (job_id, note, timestamp)
            VALUES (?, ?, ?)
        ''', note)
    
    conn.commit()
    logger.info("Demonstration data inserted successfully")

def ensure_database_exists(db_path, with_demo_data=True):
    """Ensure the database exists and is initialized with tables and optionally demo data."""
    # Check if the database directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logger.info(f"Created database directory: {db_dir}")
    
    # Check if the database file exists
    db_exists = os.path.exists(db_path)
    if db_exists:
        # Check if the database has tables
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer'")
            tables_exist = cursor.fetchone() is not None
            conn.close()
            
            if tables_exist:
                logger.info("Database already exists and has tables")
                return False  # Database already initialized
            else:
                logger.info("Database exists but has no tables")
                conn = create_tables(db_path)
                if with_demo_data:
                    insert_demo_data(conn)
                conn.close()
                return True  # New tables initialized
        except sqlite3.Error as e:
            logger.error(f"Error checking database: {str(e)}")
            # If there's an error, try to recreate the database
            os.remove(db_path)
            logger.info("Removed corrupted database")
            db_exists = False
    
    if not db_exists:
        # Create new database
        conn = create_tables(db_path)
        if with_demo_data:
            insert_demo_data(conn)
        conn.close()
        logger.info("New database created and initialized")
        return True  # New database initialized
    
    return False

if __name__ == "__main__":
    # Path to the database
    db_path = os.path.join('instance', 'jobmanager.db')
    
    # Check if --no-demo flag is provided
    import sys
    with_demo = "--no-demo" not in sys.argv
    
    # Ensure database exists
    is_new = ensure_database_exists(db_path, with_demo_data=with_demo)
    
    if is_new:
        print("Database initialized successfully")
        if with_demo:
            print("Demonstration data has been added")
    else:
        print("Database already exists, no changes made")