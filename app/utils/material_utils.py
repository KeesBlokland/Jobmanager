# app/utils/material_utils.py
from .time_utils import get_current_time

class MaterialManager:
    def __init__(self, db):
        self.db = db

    def add_material(self, job_id, material_data):
        now = get_current_time()  # Use centralized time function
        self.db.execute(
            'INSERT INTO job_material (job_id, material, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?)',
            (job_id, material_data['material'], 
             float(material_data['quantity']), 
             float(material_data['price']), now)
        )
        self.db.commit()

    def get_materials(self, job_id):
        return self.db.execute('''
            SELECT * FROM job_material
            WHERE job_id = ?
            ORDER BY timestamp DESC
        ''', (job_id,)).fetchall()

    def delete_material(self, material_id, job_id):
        self.db.execute('DELETE FROM job_material WHERE id = ? AND job_id = ?', 
                       (material_id, job_id))
        self.db.commit()