# app/utils/db_utils.py
from functools import wraps
from flask import g, current_app
import sqlite3

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def with_db(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db = get_db()
        return f(db, *args, **kwargs)
    return decorated_function

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_job_with_customer(db, job_id):
    return db.execute('''
        SELECT job.*, customer.name as customer_name
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [job_id]).fetchone()

def get_active_timer(db):
    return db.execute('''
        SELECT time_entry.*, job.id as job_id
        FROM time_entry 
        JOIN job ON time_entry.job_id = job.id
        WHERE time_entry.end_time IS NULL
    ''').fetchone()