# app/utils/timer_utils.py
from datetime import datetime
from ..db import get_active_timer, calculate_job_total_hours
from .error_utils import TimerError, handle_errors
import logging

class TimerManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('jobmanager')

    @handle_errors
    def start(self, job_id):
        self.logger.info(f"Starting timer for job {job_id}")
        
        # Get current time as ISO format string
        now_iso = datetime.now().isoformat()
        
        # Stop any running timers first
        self.stop_all_active()
        
        # Create new timer entry
        self.db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
            (job_id, now_iso, 'auto')
        )
        
        # Update job's status to Active if it was Pending, and update last_active timestamp
        self.db.execute('''
            UPDATE job 
            SET last_active = ?,
                status = CASE 
                    WHEN status = 'Pending' THEN 'Active'
                    ELSE status
                END
            WHERE id = ?
        ''', (now_iso, job_id))
        
        self.db.commit()

    @handle_errors
    def stop(self, job_id):
        self.logger.info(f"Stopping timer for job {job_id}")
        
        # Get current time as ISO format string
        now_iso = datetime.now().isoformat()
        
        active_timer = get_active_timer(self.db)
        if active_timer and active_timer['job_id'] == job_id:
            self.db.execute(
                'UPDATE time_entry SET end_time = ? WHERE id = ?',
                (now_iso, active_timer['id'])
            )
            self.db.commit()

    @handle_errors
    def stop_all_active(self):
        self.logger.info("Stopping all active timers")
        
        # Get current time as ISO format string
        now_iso = datetime.now().isoformat()
        
        self.db.execute(
            'UPDATE time_entry SET end_time = ? WHERE end_time IS NULL',
            (now_iso,)
        )
        self.db.commit()

    @handle_errors
    def calculate_total_hours(self, job_id):
        """Calculate the total hours for a job."""
        result = self.db.execute('''
            SELECT SUM((julianday(COALESCE(end_time, datetime('now'))) - 
                       julianday(start_time)) * 24) as total_hours
            FROM time_entry
            WHERE job_id = ? AND 
                  ROUND((julianday(COALESCE(end_time, datetime('now'))) - 
                        julianday(start_time)) * 24, 2) > 0.03
        ''', (job_id,)).fetchone()
        
        total_hours = result['total_hours'] if result['total_hours'] else 0
        # Round to nearest 5 minutes (1/12 of an hour)
        return round(total_hours * 12) / 12