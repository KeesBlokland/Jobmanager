#!/usr/bin/env python3
# debug_time_entries.py
# Script to check the format of time entries in the database

import sqlite3
import os
from datetime import datetime

# Configuration
DB_PATH = 'instance/jobmanager.db'

def inspect_time_entries():
    """Check the format of time entries in the database."""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a sample of time entries for inspection
    cursor.execute('''
        SELECT id, job_id, start_time, end_time, 
               typeof(start_time) as start_type,
               typeof(end_time) as end_type
        FROM time_entry
        ORDER BY id
        LIMIT 20
    ''')
    
    entries = cursor.fetchall()
    
    if not entries:
        print("No time entries found in the database.")
        return
    
    print("\nTime Entry Format Inspection:")
    print("=" * 80)
    print(f"{'ID':<5} {'Job ID':<7} {'Start Type':<10} {'End Type':<10} {'Start Time':<25} {'End Time':<25}")
    print("-" * 80)
    
    for entry in entries:
        start_time = entry['start_time']
        end_time = entry['end_time'] if entry['end_time'] else "NULL"
        
        print(f"{entry['id']:<5} {entry['job_id']:<7} {entry['start_type']:<10} {entry['end_type']:<10} {start_time:<25} {end_time:<25}")
    
    # Try calculating hours with different methods to debug
    print("\nTesting Hours Calculation:")
    print("=" * 80)
    
    for entry in entries:
        if entry['end_time'] is None:
            continue  # Skip entries with NULL end_time for simplicity
            
        # Method 1: Direct julianday
        cursor.execute('''
            SELECT (julianday(end_time) - julianday(start_time)) * 24 as hours_direct
            FROM time_entry
            WHERE id = ?
        ''', (entry['id'],))
        direct_result = cursor.fetchone()
        
        # Method 2: With unixepoch conversion
        cursor.execute('''
            SELECT (julianday(datetime(end_time, 'unixepoch')) - 
                    julianday(datetime(start_time, 'unixepoch'))) * 24 as hours_unixepoch
            FROM time_entry
            WHERE id = ?
        ''', (entry['id'],))
        unixepoch_result = cursor.fetchone()
        
        # Method 3: Hybrid approach
        cursor.execute('''
            SELECT (julianday(
                      CASE 
                          WHEN typeof(end_time) = 'integer' OR (typeof(end_time) = 'text' AND end_time GLOB '[0-9]*' AND NOT end_time GLOB '*-*') THEN
                              datetime(end_time, 'unixepoch')
                          ELSE
                              end_time 
                      END
                    ) - 
                    julianday(
                      CASE 
                          WHEN typeof(start_time) = 'integer' OR (typeof(start_time) = 'text' AND start_time GLOB '[0-9]*' AND NOT start_time GLOB '*-*') THEN
                              datetime(start_time, 'unixepoch')
                          ELSE
                              start_time 
                      END
                    )) * 24 as hours_hybrid
            FROM time_entry
            WHERE id = ?
        ''', (entry['id'],))
        hybrid_result = cursor.fetchone()
        
        print(f"Entry ID {entry['id']}:")
        print(f"  Direct method:    {direct_result['hours_direct'] if direct_result['hours_direct'] is not None else 'NULL'}")
        print(f"  Unixepoch method: {unixepoch_result['hours_unixepoch'] if unixepoch_result['hours_unixepoch'] is not None else 'NULL'}")
        print(f"  Hybrid method:    {hybrid_result['hours_hybrid'] if hybrid_result['hours_hybrid'] is not None else 'NULL'}")
        print()
    
    conn.close()

if __name__ == "__main__":
    print("Inspecting time entries in the database...")
    inspect_time_entries()