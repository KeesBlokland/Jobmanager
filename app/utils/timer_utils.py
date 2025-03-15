# app/utils/timer_utils.py
from datetime import datetime, timezone
from ..db import get_active_timer, calculate_job_total_hours
from .error_utils import TimerError, handle_errors
from .time_utils import get_current_time
import logging

class TimerManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('jobmanager')

    def start(self, job_id):
        self.logger.info(f"Starting timer for job {job_id}")
        
        # Always use UTC time with timezone info for consistent calculations
        now_iso = get_current_time()
        
        # Log timestamp for debugging
        self.logger.info(f"Starting timer at: {now_iso}")
        
        # Stop any running timers first
        self.stop_all_active()
        
        # Create new timer entry
        self.db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
            (job_id, now_iso, 'auto')
        )
          
        # Get the current job status
        job = self.db.execute('SELECT status FROM job WHERE id = ?', (job_id,)).fetchone()
        
        # Update job's status to Active if it's not already Active
        if job and job['status'] != 'Active':
            self.logger.info(f"Updating job {job_id} status from '{job['status']}' to 'Active'")
            self.db.execute(
                'UPDATE job SET status = ?, last_active = ? WHERE id = ?',
                ('Active', now_iso, job_id)
            )
        else:
            # Just update the last_active timestamp
            self.db.execute(
                'UPDATE job SET last_active = ? WHERE id = ?',
                (now_iso, job_id)
            )
        
        self.db.commit()

    @handle_errors
    def stop(self, job_id):
        """Stop the timer for the specified job."""
        self.logger.info(f"Stopping timer for job {job_id}")
        
        # Always use UTC time with timezone info
        now_iso = get_current_time()
        
        # Log timestamp for debugging
        self.logger.info(f"Stopping timer at: {now_iso}")
        
        active_timer = get_active_timer(self.db)
        if active_timer and active_timer['job_id'] == job_id:
            # Log the timer details for debugging
            start_time = active_timer['start_time']
            self.logger.info(f"Active timer found: id={active_timer['id']}, start={start_time}")
            
            self.db.execute(
                'UPDATE time_entry SET end_time = ? WHERE id = ?',
                (now_iso, active_timer['id'])
            )
            self.db.commit()

    @handle_errors
    def stop_all_active(self):
        """Stop all active timers in the system."""
        self.logger.info("Stopping all active timers")
        
        # Always use UTC time with timezone info
        now_iso = get_current_time()
        
        self.db.execute(
            'UPDATE time_entry SET end_time = ? WHERE end_time IS NULL',
            (now_iso,)
        )
        self.db.commit()

    @handle_errors
    def calculate_total_hours(self, job_id):
        """Calculate the total hours for a job."""
        return calculate_job_total_hours(self.db, job_id)