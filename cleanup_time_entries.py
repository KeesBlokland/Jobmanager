#!/usr/bin/env python3
# cleanup_time_entries.py
# Cleans up time entries in the database to ensure consistent ISO format

import sqlite3
from datetime import datetime
import os
import sys
import argparse

def normalize_timestamp(timestamp):
    """Normalize a timestamp value to ISO format string"""
    if timestamp is None:
        return None
        
    # If it's already a string with dashes, assume it's ISO format
    if isinstance(timestamp, str) and '-' in timestamp:
        try:
            # Validate it's a proper ISO format
            dt = datetime.fromisoformat(timestamp)
            return dt.isoformat()
        except ValueError:
            pass  # Not a valid ISO format, continue with other methods
    
    # Try to interpret as Unix timestamp (seconds since epoch)
    try:
        if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
            ts = int(float(timestamp))
            # Only consider timestamps after year 2000 and before 2050
            if 946684800 <= ts <= 2524608000:  # 2000-01-01 to 2050-01-01
                dt = datetime.fromtimestamp(ts)
                return dt.isoformat()
    except (ValueError, OverflowError):
        pass
    
    # If all else fails, return current time
    print(f"  Warning: Could not interpret timestamp: {timestamp}, using current time")
    return datetime.now().isoformat()

def cleanup_database(db_path, dry_run=False):
    """Clean up all time entries in the database"""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if we have any non-ISO format dates (pure heuristic)
        cursor.execute('''
            SELECT COUNT(*) as count FROM time_entry 
            WHERE start_time IS NOT NULL AND 
                  (
                      CAST(start_time AS TEXT) NOT LIKE '%-%' OR
                      CAST(start_time AS TEXT) NOT LIKE '%T%:%'
                  )
        ''')
        non_iso_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM time_entry')
        total_count = cursor.fetchone()['count']
        
        print(f"Database has {total_count} time entries, approximately {non_iso_count} with potential format issues")
        
        # Get all time entries
        cursor.execute('SELECT id, job_id, start_time, end_time FROM time_entry')
        entries = cursor.fetchall()
        
        updated_count = 0
        for entry in entries:
            entry_id = entry['id']
            job_id = entry['job_id']
            old_start = entry['start_time']
            old_end = entry['end_time']
            
            # Normalize timestamps
            new_start = normalize_timestamp(old_start)
            new_end = normalize_timestamp(old_end) if old_end is not None else None
            
            # Check if anything changed
            if new_start != old_start or new_end != old_end:
                updated_count += 1
                print(f"Entry {entry_id} (Job {job_id}):")
                print(f"  Old: {old_start} -> {old_end}")
                print(f"  New: {new_start} -> {new_end}")
                
                # Update the database if not in dry run mode
                if not dry_run:
                    cursor.execute(
                        'UPDATE time_entry SET start_time = ?, end_time = ? WHERE id = ?',
                        (new_start, new_end, entry_id)
                    )
        
        if updated_count == 0:
            print("No time entries needed normalization!")
        else:
            print(f"Updated {updated_count} time entries")
            
            if dry_run:
                print("DRY RUN - No changes were saved to the database")
            else:
                conn.commit()
                print("Changes committed to the database")
                
        return True
    
    except Exception as e:
        print(f"Error cleaning up database: {str(e)}")
        if not dry_run:
            conn.rollback()
        return False
    
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Clean up time entries in the database')
    parser.add_argument('--db', default='instance/jobmanager.db', help='Path to the database file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()
    
    print("Time Entry Format Cleanup Tool")
    print("==============================")
    print(f"Database: {args.db}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made to the database")
    
    if cleanup_database(args.db, args.dry_run):
        print("Cleanup completed successfully")
        return 0
    else:
        print("Cleanup failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())