# debug_jobs.py
from app import create_app
from app.utils.db_utils import get_db

app = create_app()

with app.app_context():
    db = get_db()
    jobs = db.execute('''
        SELECT job.*, customer.name as customer_name
        FROM job 
        JOIN customer ON job.customer_id = customer.id
    ''').fetchall()
    
    print("\nJobs in database:")
    for job in jobs:
        print(f"ID: {job['id']}, Customer: {job['customer_name']}, Description: {job['description']}")