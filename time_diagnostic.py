# time_diagnostic.py - Place in project root directory
#!/usr/bin/env python3

import sqlite3
from datetime import datetime, timezone, timedelta
import os
import sys
import json

def diagnose_time_issues():
    """Diagnose time-related issues in the database and user profile."""
    print("\n======= TIME DIAGNOSTIC TOOL =======\n")
    
    # Check system time
    print("=== System Time Information ===")
    now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    
    print(f"Local time:      {now}")
    print(f"UTC time:        {utc_now}")
    print(f"Time difference: {(now.replace(tzinfo=None) - utc_now.replace(tzinfo=None)).total_seconds() / 3600} hours")
    
    # Check user profile
    try:
        print("\n=== User Profile Time Settings ===")
        profile_path = os.path.join('instance', 'user_profile.json')
        
        if not os.path.exists(profile_path):
            print(f"User profile not found at {profile_path}")
        else:
            with open(profile_path, 'r') as f:
                profile = json.load(f)
                
            # Check for time offset setting
            offset_minutes = profile.get('preferences', {}).get('time_offset_minutes', 0)
            offset_hours = offset_minutes / 60
            
            print(f"Time offset: {offset_minutes} minutes ({offset_hours:.2f} hours)")
            
            # Calculate adjusted time
            adjusted_time = utc_now + timedelta(minutes=offset_minutes)
            print(f"Adjusted time: {adjusted_time}")
            
            # Show difference from local time
            diff_from_local = (adjusted_time - now.replace(tzinfo=timezone.utc)).total_seconds() / 60
            print(f"Difference from local: {diff_from_local:.2f} minutes")
    except Exception as e:
        print(f"Error reading user profile: {str(e)}")
    
    # Connect to database
    try:
        print("\n=== Database Time Information ===")
        db_path = 'instance/jobmanager.db'
        
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check recent time entries
        print("\n=== Recent Time Entries ===")
        cursor.execute("""
            SELECT time_entry.id, time_entry.start_time, time_entry.end_time,
                   job.description as job_description
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
                
                print(f"ID: {entry['id']} - {entry['job_description']}")
                print(f"  Start: {start_time}")
                print(f"  End:   {end_time}")
                
                # Try to parse the timestamps
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    if start_dt.tzinfo is None:
                        print("  WARNING: Start time has no timezone information")
                    else:
                        print(f"  Start time timezone: {start_dt.tzinfo}")
                        
                    if entry['end_time']:
                        end_dt = datetime.fromisoformat(end_time)
                        if end_dt.tzinfo is None:
                            print("  WARNING: End time has no timezone information")
                        
                        # Calculate hours
                        hours = (end_dt - start_dt).total_seconds() / 3600
                        print(f"  Hours: {hours:.2f}")
                except Exception as e:
                    print(f"  Error parsing timestamps: {str(e)}")
                
                print()
        
        # Check active timer
        print("\n=== Active Timer Check ===")
        cursor.execute("""
            SELECT time_entry.*, job.description
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
                    now_dt = datetime.now(timezone.utc)
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                        
                    elapsed_seconds = (now_dt - start_dt).total_seconds()
                    hours = int(elapsed_seconds // 3600)
                    minutes = int((elapsed_seconds % 3600) // 60)
                    seconds = int(elapsed_seconds % 60)
                    
                    print(f"  Job: {timer['description']}")
                    print(f"  Start time: {start_time}")
                    print(f"  Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    
                    # Apply user offset
                    try:
                        with open(profile_path, 'r') as f:
                            profile = json.load(f)
                        offset_minutes = profile.get('preferences', {}).get('time_offset_minutes', 0)
                        
                        adjusted_start = start_dt + timedelta(minutes=offset_minutes)
                        adjusted_now = now_dt + timedelta(minutes=offset_minutes)
                        
                        adjusted_elapsed = (adjusted_now - adjusted_start).total_seconds()
                        adj_hours = int(adjusted_elapsed // 3600)
                        adj_minutes = int((adjusted_elapsed % 3600) // 60)
                        adj_seconds = int(adjusted_elapsed % 60)
                        
                        print(f"  Adjusted start: {adjusted_start}")
                        print(f"  Adjusted elapsed: {adj_hours:02d}:{adj_minutes:02d}:{adj_seconds:02d}")
                    except Exception as e:
                        print(f"  Error calculating adjusted time: {str(e)}")
                except Exception as e:
                    print(f"  Error processing timer: {str(e)}")
                print()
            
    except Exception as e:
        print(f"Error accessing database: {str(e)}")
    
    print("\n======= DIAGNOSTIC COMPLETE =======\n")

if __name__ == "__main__":
    diagnose_time_issues()