# app/routes.py
from flask import Blueprint, render_template, current_app, g, request, redirect, url_for, flash
from datetime import datetime, timezone
import json
import sqlite3

bp = Blueprint('main', __name__)

# =============================================================================
# Database Setup
# =============================================================================
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

# =============================================================================
# Customer Routes
# =============================================================================
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

# =============================================================================
# Job Routes (Main CRUD)
# =============================================================================
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

# =============================================================================
# Timer Routes
# =============================================================================
@bp.route('/job/<int:id>/start_timer', methods=['POST'])
def start_timer(id):
    db = get_db()
    now = datetime.now().isoformat()
    
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
    now = datetime.now().isoformat()
    
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
    now = datetime.now().isoformat()
    
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
    now = datetime.now().isoformat()
    
    # Create new time entry but don't change job status
    db.execute(
        'INSERT INTO time_entry (job_id, start_time, entry_type) VALUES (?, ?, ?)',
        (id, now, 'auto')
    )
    db.commit()
    
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:id>/update_total', methods=['POST'])
def update_job_total(id):
    db = get_db()
    now = datetime.now().isoformat()
    
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

# =============================================================================
# Job Details Routes (Notes, Materials, Time Entries)
# =============================================================================
@bp.route('/job/<int:id>/details', methods=['GET', 'POST'])
def job_details(id):
    db = get_db()
    
    # Handle note updates
    if request.method == 'POST':
        notes = request.form['notes'].strip()
        if notes:
            db.execute('DELETE FROM job_note WHERE job_id = ?', (id,))
            for line in notes.splitlines():
                if line.strip():
                    # Remove any existing timestamps from the start of the line
                    import re
                    clean_line = re.sub(r'^\d{2} \w{3} \d{2} \d{2}:\d{2}: ', '', line.strip())
                    if clean_line:
                        db.execute(
                            'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
                            (id, clean_line, datetime.now(timezone.utc).isoformat())
                        )
            db.commit()
        return redirect(url_for('main.job_details', id=id))

    # Get job info
    job = db.execute('''
        SELECT job.*, customer.name as customer_name
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [id]).fetchone()

    # Get notes
    notes = db.execute('''
        SELECT note, timestamp 
        FROM job_note 
        WHERE job_id = ? 
        ORDER BY timestamp DESC
    ''', [id]).fetchall()

    # Format notes with timestamps for display
    combined_notes = ''
    for note in notes:
        ts = datetime.fromisoformat(note['timestamp']).strftime('%d %b %y %H:%M')
        combined_notes += f"{ts}: {note['note']}\n"

    # Get materials
    materials = db.execute('''
        SELECT * FROM job_material
        WHERE job_id = ?
        ORDER BY timestamp DESC
    ''', (id,)).fetchall()

# Get time entries
    time_entries = db.execute('''
        SELECT *,
        ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24, 2) as hours
        FROM time_entry
        WHERE job_id = ? AND 
        ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24, 2) > 0.03
        ORDER BY start_time DESC
    ''', (id,)).fetchall()

    total_hours = sum(entry['hours'] for entry in time_entries)
    total_amount = total_hours * job['base_rate'] if job['base_rate'] else 0

    return render_template('job_details.html',
        job=job,
        combined_notes=combined_notes,
        materials=materials,
        time_entries=time_entries,
        total_hours=total_hours,
        total_amount=total_amount)
    

# Notes routes
@bp.route('/job/<int:job_id>/add_note', methods=['POST'])
def add_note(job_id):
    db = get_db()
    now = datetime.now().isoformat()
    db.execute(
        'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
        (job_id, request.form['note'], now)
    )
    db.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@bp.route('/job/<int:job_id>/delete_note/<int:note_id>', methods=['POST'])
def delete_note(job_id, note_id):
    db = get_db()
    db.execute('DELETE FROM job_note WHERE id = ? AND job_id = ?', (note_id, job_id))
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:job_id>/edit_note/<int:note_id>', methods=['POST'])
def edit_note(job_id, note_id):
    db = get_db()
    db.execute('UPDATE job_note SET note = ? WHERE id = ? AND job_id = ?',
               (request.form['note'], note_id, job_id))
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:job_id>/save_notes', methods=['POST'])
def save_notes(job_id):
    db = get_db()
    notes = request.form['notes'].strip()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Clear existing notes
    db.execute('DELETE FROM job_note WHERE job_id = ?', (job_id,))
    
    # Save each non-empty line
    for line in notes.splitlines():
        if line.strip():
            db.execute(
                'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
                (job_id, line.strip(), timestamp)
            )
    
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/dump_notes/<int:job_id>')
def dump_notes(job_id):
    db = get_db()
    notes = db.execute('SELECT * FROM job_note WHERE job_id = ?', [job_id]).fetchall()
    return [dict(row) for row in notes]

# Materials routes
@bp.route('/job/<int:job_id>/add_material', methods=['POST'])
def add_material(job_id):
    db = get_db()
    now = datetime.now().isoformat()
    material = request.form['material']
    quantity = float(request.form['quantity'])
    price = float(request.form['price']) if 'price' in request.form else 0.0
    
    db.execute(
        'INSERT INTO job_material (job_id, material, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?)',
        (job_id, material, quantity, price, now)
    )
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:job_id>/delete_material/<int:material_id>', methods=['POST'])
def delete_material(job_id, material_id):
    db = get_db()
    db.execute('DELETE FROM job_material WHERE id = ? AND job_id = ?', (material_id, job_id))
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:job_id>/edit_material/<int:material_id>', methods=['POST'])
def edit_material(job_id, material_id):
    db = get_db()
    db.execute('UPDATE job_material SET material = ?, quantity = ?, price = ? WHERE id = ? AND job_id = ?',
               (request.form['material'], request.form['quantity'], request.form['price'], material_id, job_id))
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

# Time Entry routes
@bp.route('/job/<int:job_id>/delete_time_entry/<int:entry_id>', methods=['POST'])
def delete_time_entry(job_id, entry_id):
    db = get_db()
    db.execute('DELETE FROM time_entry WHERE id = ? AND job_id = ?', (entry_id, job_id))
    db.commit()
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:job_id>/edit_time_entry/<int:entry_id>', methods=['POST'])
def edit_time_entry(job_id, entry_id):
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        db = get_db()
        db.execute(
            'UPDATE time_entry SET start_time = ?, end_time = ? WHERE id = ? AND job_id = ?',
            (start_time, end_time, entry_id, job_id)
        )
        db.commit()
        
        return redirect(url_for('main.job_details', id=job_id))
    return redirect(url_for('main.job_details', id=job_id))

@bp.route('/job/<int:id>/invoice')
def job_invoice(id):
    db = get_db()
    
    # Get job info with customer details
    job = db.execute('''
        SELECT job.*, customer.*
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [id]).fetchone()

    # Get time entries (excluding 0:00)
    time_entries = db.execute('''
        SELECT *,
        ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24, 2) as hours
        FROM time_entry
        WHERE job_id = ? AND 
        ROUND((julianday(COALESCE(end_time, CURRENT_TIMESTAMP)) - julianday(start_time)) * 24, 2) > 0
        ORDER BY start_time
    ''', (id,)).fetchall()

    # Get materials
    materials = db.execute('''
        SELECT * FROM job_material
        WHERE job_id = ?
        ORDER BY timestamp
    ''', (id,)).fetchall()

    # Calculate totals
    total_hours = sum(entry['hours'] for entry in time_entries)
    total_amount = total_hours * job['base_rate'] if job['base_rate'] else 0
    
    # Generate invoice number
    date_str = datetime.now().strftime('%Y%m%d')
    last_invoice = db.execute(
        'SELECT invoice_number FROM job WHERE invoice_number LIKE ? ORDER BY invoice_number DESC LIMIT 1', 
        (f'{date_str}%',)
    ).fetchone()
    
    if last_invoice and last_invoice['invoice_number']:
        sequence = int(last_invoice['invoice_number'][-2:]) + 1
    else:
        sequence = 1
        
    invoice_number = f'{date_str}-{sequence:02d}'
    
    # Update job with invoice number
    db.execute('UPDATE job SET invoice_number = ? WHERE id = ?', (invoice_number, id))
    db.commit()

    return render_template('invoice.html',
        job=job,
        time_entries=time_entries,
        materials=materials,
        total_hours=total_hours,
        total_amount=total_amount,
        invoice_number=invoice_number)

