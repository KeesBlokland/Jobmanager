# time_diagnostic.py - Save this in the root directory

import sqlite3
from datetime import datetime, timezone
import os
import sys
import pytz

def diagnose_time_issues():
    """Diagnose time-related issues in the database.
    
    This script checks:
    1. Server system time and timezone
    2. Database time entries for potential issues
    3. Active timer status
    """
    print("\n======= TIME DIAGNOSTIC TOOL =======\n")
    
    # Check system time
    print("=== System Time Information ===")
    now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    
    print(f"Local time: {now}")
    print(f"UTC time:   {utc_now}")
    print(f"Time difference: {(now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)).total_seconds() / 3600} hours")
    
    # Try to get system timezone
    try:
        with open('/etc/timezone', 'r') as f:
            system_tz = f.read().strip()
        print(f"System timezone: {system_tz}")
    except Exception as e:
        print(f"Could not read system timezone: {e}")
    
    # Check Python timezone
    local_tz = datetime.now().astimezone().tzinfo
    print(f"Python local timezone: {local_tz}")
    
    # Connect to database
    try:
        print("\n=== Database Time Information ===")
        db_path = 'instance/jobmanager.db'
        
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            sys.exit(1)
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check SQLite time
        cursor.execute("SELECT datetime('now') as sqlite_time, datetime('now', 'localtime') as sqlite_local_time")
        times = cursor.fetchone()
        print(f"SQLite UTC time:        {times['sqlite_time']}")
        print(f"SQLite 'localtime':     {times['sqlite_local_time']}")
        
        # Check for active timers
        print("\n=== Active Timer Check ===")
        cursor.execute("""
            SELECT time_entry.*, job.id as job_id, job.description
            FROM time_entry 
            JOIN job ON time_entry.job_id = job.id
            WHERE time_entry.end_time IS NULL
        """)
        active_timers = cursor.fetchall()
        
        if not active_timers:
            print("No active timers found.")
        else:
            print(f"Found {len(active_timers)} active timer(s):")
            for timer in active_timers:
                start_time = timer['start_time']
                
                # Parse the ISO timestamp
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    
                    # Calculate elapsed time
                    elapsed_seconds = (now.replace(tzinfo=None) - start_dt.replace(tzinfo=None)).total_seconds()
                    hours = int(elapsed_seconds // 3600)
                    minutes = int((elapsed_seconds % 3600) // 60)
                    seconds = int(elapsed_seconds % 60)
                    
                    print(f"  Job ID: {timer['job_id']} - {timer['description']}")
                    print(f"  Start time: {start_time}")
                    print(f"  Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    
                    # Check for negative time or other issues
                    if elapsed_seconds < 0:
                        print(f"  WARNING: Negative elapsed time! Timer starts in the future.")
                        
                        # Check for timezone issues
                        for tz_name in ['UTC', 'Europe/Berlin', 'Europe/London', 'America/New_York']:
                            tz = pytz.timezone(tz_name)
                            tz_now = datetime.now(tz)
                            tz_elapsed = (tz_now.replace(tzinfo=None) - start_dt.replace(tzinfo=None)).total_seconds()
                            print(f"  - Compared to {tz_name}: {int(tz_elapsed // 3600):02d}:{int((tz_elapsed % 3600) // 60):02d}:{int(tz_elapsed % 60):02d}")
                            
                except ValueError as e:
                    print(f"  Error parsing start time '{start_time}': {e}")
                except Exception as e:
                    print(f"  Error processing timer: {e}")
                print()
        
        # Check recent time entries
        print("\n=== Recent Time Entries ===")
        cursor.execute("""
            SELECT time_entry.*, job.description,
                (julianday(COALESCE(end_time, datetime('now', 'localtime'))) - julianday(start_time)) * 24 as hours
            FROM time_entry
            JOIN job ON time_entry.job_id = job.id
            ORDER BY time_entry.start_time DESC
            LIMIT 5
        """)
        entries = cursor.fetchall()
        
        if not entries:
            print("No time entries found.")
        else:
            print(f"Last {len(entries)} time entries:")
            for entry in entries:
                start_time = entry['start_time']
                end_time = entry['end_time'] or "ongoing"
                hours = entry['hours']
                
                print(f"  ID: {entry['id']} - {entry['description']}")
                print(f"  Start: {start_time}")
                print(f"  End: {end_time}")
                print(f"  Hours: {hours}")
                
                # Try to recalculate hours
                try:
                    if entry['end_time']:
                        start_dt = datetime.fromisoformat(start_time)
                        end_dt = datetime.fromisoformat(end_time)
                        calc_hours = (end_dt - start_dt).total_seconds() / 3600
                        print(f"  Recalculated hours: {calc_hours}")
                        
                        if abs(calc_hours - hours) > 0.01:
                            print(f"  WARNING: Hour calculation discrepancy: DB={hours}, Calc={calc_hours}")
                except Exception as e:
                    print(f"  Error recalculating hours: {e}")
                print()
                
    except Exception as e:
        print(f"Error accessing database: {e}")
    
    print("\n======= DIAGNOSTIC COMPLETE =======\n")

if __name__ == "__main__":
    diagnose_time_issues()