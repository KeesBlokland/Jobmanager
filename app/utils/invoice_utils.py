# app/utils/invoice_utils.py
from datetime import datetime
import logging

class InvoiceManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('jobmanager')

    def generate_invoice_number(self, job_id):
        """Generate a unique invoice number"""
        year = datetime.now().strftime('%Y')
        count = self.db.execute(
            'SELECT COUNT(*) as count FROM job WHERE invoice_number IS NOT NULL AND invoice_number LIKE ?',
            (f'{year}%',)
        ).fetchone()['count']
        
        return f"{year}-{str(count + 1).zfill(4)}"

    def create_invoice(self, job_id):
        """Create an invoice for a job"""
        self.logger.info(f"Creating invoice for job {job_id}")
        
        # Check if job exists and doesn't have an invoice
        job = self.db.execute(
            'SELECT id, invoice_number FROM job WHERE id = ?',
            (job_id,)
        ).fetchone()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job['invoice_number']:
            return job['invoice_number']
        
        # Generate and save new invoice number
        invoice_number = self.generate_invoice_number(job_id)
        
        self.db.execute(
            'UPDATE job SET invoice_number = ? WHERE id = ?',
            (invoice_number, job_id)
        )
        self.db.commit()
        
        self.logger.info(f"Created invoice {invoice_number} for job {job_id}")
        return invoice_number

    def get_invoice_data(self, job_id):
        """Get all data needed for an invoice"""
        job_data = self.db.execute('''
            SELECT job.*, customer.*
            FROM job
            JOIN customer ON job.customer_id = customer.id
            WHERE job.id = ?
        ''', (job_id,)).fetchone()
        
        time_entries = self.db.execute('''
            SELECT *,
            ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - 
                   julianday(start_time)) * 24, 2) as hours
            FROM time_entry
            WHERE job_id = ? AND 
            ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - 
                   julianday(start_time)) * 24, 2) > 0.03
            ORDER BY start_time
        ''', (job_id,)).fetchall()
        
        materials = self.db.execute('''
            SELECT *
            FROM job_material
            WHERE job_id = ?
            ORDER BY timestamp
        ''', (job_id,)).fetchall()
        
        return {
            'job': job_data,
            'time_entries': time_entries,
            'materials': materials
        }