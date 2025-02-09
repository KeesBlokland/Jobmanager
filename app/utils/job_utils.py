# app/utils/job_utils.py
from datetime import datetime

class JobManager:
    def __init__(self, db):
        self.db = db

    def get_all_jobs(self):
        return self.db.execute('''
            WITH job_hours AS (
                SELECT 
                    job_id,
                    SUM((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24) as hours
                FROM time_entry
                GROUP BY job_id
            )
            SELECT 
                job.*,
                customer.name as customer_name,
                te_active.id as active_timer_id,
                te_active.start_time as timer_start,
                COALESCE(job_hours.hours, 0) as accumulated_hours
            FROM job 
            JOIN customer ON job.customer_id = customer.id 
            LEFT JOIN time_entry te_active ON job.id = te_active.job_id 
                AND te_active.end_time IS NULL
            LEFT JOIN job_hours ON job_hours.job_id = job.id
            ORDER BY 
                te_active.id IS NOT NULL DESC,
                CASE job.status
                    WHEN 'Active' THEN 1
                    WHEN 'Pending' THEN 2
                    WHEN 'Completed' THEN 3
                END,
                job.last_active DESC NULLS LAST,
                job.creation_date DESC
        ''').fetchall()

    def create_job(self, customer_id, data):
        self.db.execute(
            'INSERT INTO job (customer_id, description, status, creation_date, base_rate, estimated_hours)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (customer_id, data['description'], data['status'],
             datetime.now().isoformat(), 
             float(data['base_rate']) if data.get('base_rate') else None,
             float(data['estimated_hours']) if data.get('estimated_hours') else None)
        )
        self.db.commit()

    def update_job(self, job_id, data):
        self.db.execute(
            'UPDATE job SET description=?, status=?, base_rate=?, estimated_hours=? WHERE id=?',
            (data['description'], data['status'],
             float(data.get('base_rate')) if data.get('base_rate') else None,
             float(data.get('estimated_hours')) if data.get('estimated_hours') else None,
             job_id)
        )
        self.db.commit()

    def delete_job(self, job_id):
        self.db.execute('DELETE FROM job WHERE id = ?', (job_id,))
        self.db.commit()