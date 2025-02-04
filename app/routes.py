# app/routes.py
from flask import Blueprint, render_template, current_app, g, request, redirect, url_for, flash
from datetime import datetime, timezone
import json
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

# app/routes.py
@bp.route('/')
def index():
    db = get_db()
    customers = db.execute(
        'SELECT * FROM customer ORDER BY name'
    ).fetchall()
    return render_template('customer_list.html', customers=customers)

@bp.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            'INSERT INTO customer (name, email, phone, street, city, postal_code, country, vat_number, payment_terms, notes)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (request.form['name'], request.form['email'], request.form['phone'],
             request.form['street'], request.form['city'], request.form['postal_code'],
             request.form['country'], request.form['vat_number'], request.form['payment_terms'],
             request.form['notes'])
        )
        db.commit()
        return redirect(url_for('main.index'))
    return render_template('customer_form.html')

@bp.route('/customer/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    db = get_db()
    customer = db.execute('SELECT * FROM customer WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        db.execute(
            'UPDATE customer SET name=?, email=?, phone=?, street=?, city=?, postal_code=?, '
            'country=?, vat_number=?, payment_terms=?, notes=? WHERE id=?',
            (request.form['name'], request.form['email'], request.form['phone'],
             request.form['street'], request.form['city'], request.form['postal_code'],
             request.form['country'], request.form['vat_number'], request.form['payment_terms'],
             request.form['notes'], id)
        )
        db.commit()
        return redirect(url_for('main.index'))
    
    return render_template('customer_form.html', customer=customer)

@bp.route('/customer/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    db = get_db()
    db.execute('DELETE FROM customer WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('main.index'))

# In routes.py, update the job_list query:
# In routes.py
@bp.route('/jobs')
def job_list():
    db = get_db()
    jobs = db.execute('''
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
    return render_template('job_list.html', jobs=jobs)


@bp.route('/customer/<int:customer_id>/add_job', methods=['GET', 'POST'])
def add_job(customer_id):
    db = get_db()
    customer = db.execute('SELECT * FROM customer WHERE id = ?', (customer_id,)).fetchone()
    
    if request.method == 'POST':
        db.execute(
            'INSERT INTO job (customer_id, description, status, creation_date, base_rate, estimated_hours)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (customer_id, request.form['description'], request.form['status'],
             datetime.now().isoformat(), 
             float(request.form['base_rate']) if request.form['base_rate'] else None,
             float(request.form['estimated_hours']) if request.form['estimated_hours'] else None)
        )
        db.commit()
        return redirect(url_for('main.job_list'))
    
    return render_template('job_form.html', customer=customer)

@bp.route('/job/<int:id>/edit', methods=['GET', 'POST'])
def edit_job(id):
    db = get_db()
    job = db.execute('''
        SELECT job.*, customer.name as customer_name 
        FROM job 
        JOIN customer ON job.customer_id = customer.id 
        WHERE job.id = ?
    ''', (id,)).fetchone()
    
    if request.method == 'POST':
        db.execute(
            'UPDATE job SET description=?, status=?, base_rate=?, estimated_hours=? WHERE id=?',
            (request.form['description'], request.form['status'],
             float(request.form['base_rate']) if request.form['base_rate'] else None,
             float(request.form['estimated_hours']) if request.form['estimated_hours'] else None,
             id)
        )
        db.commit()
        return redirect(url_for('main.job_list'))
    
    return render_template('job_form.html', job=job)

@bp.route('/job/<int:id>/delete', methods=['POST'])
def delete_job(id):
    db = get_db()
    db.execute('DELETE FROM job WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('main.job_list'))

@bp.route('/job/<int:id>/start_timer', methods=['POST'])
def start_timer(id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Find any currently running timer and which job it belongs to
    active_timer = db.execute('''
        SELECT time_entry.*, job.id as job_id
        FROM time_entry 
        JOIN job ON time_entry.job_id = job.id
        WHERE time_entry.end_time IS NULL
    ''').fetchone()
    
    if active_timer:
        # Stop the timer for the specific job
        db.execute('''
            UPDATE time_entry 
            SET end_time = ?
            WHERE id = ? AND job_id = ?
        ''', (now, active_timer['id'], active_timer['job_id']))
        
        # Update the last_active time for that job
        db.execute('UPDATE job SET last_active = ? WHERE id = ?',
                  (now, active_timer['job_id']))
    
    # Check if the requested job already has accumulated time
    has_time = db.execute('''
        SELECT EXISTS (
            SELECT 1 FROM time_entry 
            WHERE job_id = ?
        ) as has_entries
    ''', (id,)).fetchone()['has_entries']
    
    if not has_time:
        # Only create a new time entry if this is the first time
        db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
            (id, now, 'auto')
        )
    else:
        # Otherwise, just resume the last entry
        db.execute(
            'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
            (id, now, 'resume')
        )
    
    # Update the requested job's last_active time
    db.execute('UPDATE job SET last_active = ? WHERE id = ?', 
               (now, id))
    
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:id>/stop_timer', methods=['POST'])
def stop_timer(id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Find and stop active timer for this job
    db.execute('''
        UPDATE time_entry 
        SET end_time = ? 
        WHERE job_id = ? AND end_time IS NULL
    ''', (now, id))
    
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:id>/pause_timer', methods=['POST'])
def pause_timer(id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Just stop the current timer but don't change job status
    db.execute('''
        UPDATE time_entry 
        SET end_time = ? 
        WHERE job_id = ? AND end_time IS NULL
    ''', (now, id))
    
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:id>/resume_timer', methods=['POST'])
def resume_timer(id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Create new time entry but don't change job status
    db.execute(
        'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
        (id, now, 'auto')
    )
    db.commit()
    
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

# Add to routes.py
@bp.route('/job/<int:id>/update_total', methods=['POST'])
def update_job_total(id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    # Calculate total hours including current running timer
    total = db.execute('''
        SELECT COALESCE(
            (
                SELECT SUM(
                    CASE 
                        WHEN end_time IS NOT NULL 
                        THEN (julianday(end_time) - julianday(start_time)) * 24
                        ELSE (julianday(?) - julianday(start_time)) * 24
                    END
                )
                FROM time_entry 
                WHERE job_id = ?
            ), 
            0
        ) as total_hours
    ''', (now, id)).fetchone()['total_hours']
    
    # Update the job's total_hours
    db.execute('UPDATE job SET total_hours = ? WHERE id = ?', 
               (total, id))
    db.commit()
    
    return json.dumps({
        'success': True, 
        'total_hours': total
    }), 200, {'ContentType': 'application/json'}


@bp.route('/job/<int:job_id>/add_note', methods=['POST'])
def add_note(job_id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
        (job_id, request.form['note'], now)
    )
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:job_id>/add_material', methods=['POST'])
def add_material(job_id):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        'INSERT INTO job_material (job_id, material, quantity, unit, timestamp) VALUES (?, ?, ?, ?, ?)',
        (job_id, request.form['material'], float(request.form['quantity']), request.form['unit'], now)
    )
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

