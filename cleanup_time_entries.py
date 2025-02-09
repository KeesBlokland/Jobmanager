# cleanup_time_entries.py
import sqlite3
from datetime import datetime

# Set minimum duration in minutes - entries shorter than this will be deleted
MIN_DURATION_MINUTES = 4

def cleanup_time_entries():
    # Convert minutes to hours for SQL comparison
    min_hours = MIN_DURATION_MINUTES / 60.0
    
    conn = sqlite3.connect('instance/jobmanager.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()
    
    zero_entries = db.execute('''
        SELECT id, job_id, start_time, end_time,
               (julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 as hours
        FROM time_entry
        WHERE ROUND((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24, 3) < ?
    ''', [min_hours]).fetchall()
    
    if not zero_entries:
        print(f"No entries shorter than {MIN_DURATION_MINUTES} minutes found.")
        return
    
    print(f"\nFound {len(zero_entries)} entries shorter than {MIN_DURATION_MINUTES} minutes:")
    for entry in zero_entries:
        mins = round(entry['hours'] * 60, 1)
        print(f"ID: {entry['id']}, Job: {entry['job_id']}, Duration: {mins} mins, Start: {entry['start_time']}, End: {entry['end_time']}")
    
    confirm = input("\nDelete these entries? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    db.execute('''
        DELETE FROM time_entry 
        WHERE ROUND((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24, 3) < ?
    ''', [min_hours])
    conn.commit()
    
    print(f"\nDeleted {len(zero_entries)} entries.")
    conn.close()

if __name__ == '__main__':
    cleanup_time_entries()