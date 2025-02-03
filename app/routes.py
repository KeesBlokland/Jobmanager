# app/routes.py
from flask import Blueprint, render_template, current_app, g
import sqlite3

bp = Blueprint('main', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@bp.teardown_app_request
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@bp.route('/')
def index():
    return render_template('base.html')

# app/schema.sql
CREATE TABLE IF NOT EXISTS customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    street TEXT,
    city TEXT,
    postal_code TEXT,
    country TEXT,
    vat_number TEXT,
    payment_terms TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    creation_date TEXT NOT NULL,
    deadline TEXT,
    base_rate REAL,
    custom_rate REAL,
    estimated_hours REAL,
    total_hours REAL DEFAULT 0,
    last_active TEXT,
    FOREIGN KEY (customer_id) REFERENCES customer (id)
);

CREATE TABLE IF NOT EXISTS time_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    entry_type TEXT NOT NULL,
    notes TEXT,
    materials_used TEXT,
    adjusted_by TEXT,
    adjustment_reason TEXT,
    location TEXT,
    break_duration INTEGER DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES job (id)
);