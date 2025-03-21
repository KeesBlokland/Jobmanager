# app/routes/job_routes.py
import shutil
from datetime import datetime, timezone, timedelta
import os
import zipfile
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from ..db import with_db
from ..utils.job_utils import JobManager
from ..utils.material_utils import MaterialManager
from ..utils.time_utils import get_current_time, format_time

import logging
import qrcode
import io
from flask import send_file
from urllib.parse import urljoin

bp = Blueprint('job', __name__)

@bp.route('/backup/<type>')
@with_db
def create_backup(db, type):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # Get and log absolute paths
        root_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        current_app.logger.info(f"Root path: {root_path}")
        current_app.logger.info(f"Current working directory: {os.getcwd()}")
        current_app.logger.info(f"Instance path: {current_app.instance_path}")
        
        # Create backups directory in root path
        backup_dir = os.path.join(root_path, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            current_app.logger.info(f"Created backup directory: {backup_dir}")
                
        if type == 'db':
            # Database backup
            db_path = current_app.config['DATABASE']
            backup_name = f'db_backup_{timestamp}.db'
            backup_path = os.path.join(backup_dir, backup_name)
            
            current_app.logger.info(f"DB Path: {db_path}")
            current_app.logger.info(f"Backup Path: {backup_path}")
            
            # Close the current database connection
            db.close()
            
            # Copy the database file
            shutil.copy2(db_path, backup_path)
            
            current_app.logger.info(f"Database backup created at: {backup_path}")
            current_app.logger.info(f"Backup file exists: {os.path.exists(backup_path)}")
            
            return jsonify({
                'success': True,
                'message': f'Database backup created: {backup_name}'
            })
            
        elif type == 'full':
            backup_name = f'jobmanager_backup_{timestamp}.zip'
            backup_path = os.path.join(backup_dir, backup_name)
            
            current_app.logger.info(f"Creating full backup at: {backup_path}")
            
            include_dirs = ['app', 'instance']
            include_files = ['run.py', 'init_db.py', 'gitback.sh']
            exclude_patterns = [
                '__pycache__',
                '*.pyc',
                '*.pyo',
                '*.pyd',
                '.git',
                '.env',
                'venv',
                'env',
                '*.db',
                'backups',
                'backup.py',
                '*.zip',
                '.txt',
                '*.md',
                'images'
            ]

            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add individual files from root
                for file in include_files:
                    file_path = os.path.join(root_path, file)
                    if os.path.exists(file_path):
                        current_app.logger.info(f"Adding file: {file_path}")
                        zipf.write(file_path, file)

                # Add directories
                for dir_name in include_dirs:
                    dir_path = os.path.join(root_path, dir_name)
                    if os.path.exists(dir_path):
                        for root, dirs, files in os.walk(dir_path):
                            # Remove excluded directories
                            dirs[:] = [d for d in dirs if d not in exclude_patterns]
                            
                            for file in files:
                                if not any(file.endswith(pat.strip('*')) for pat in exclude_patterns):
                                    file_path = os.path.join(root, file)
                                    arc_path = os.path.relpath(file_path, root_path)
                                    current_app.logger.info(f"Adding to zip: {arc_path}")
                                    zipf.write(file_path, arc_path)

            current_app.logger.info(f"Full backup created at: {backup_path}")
            current_app.logger.info(f"Backup file exists: {os.path.exists(backup_path)}")
            
            return jsonify({
                'success': True,
                'message': f'Full system backup created: {backup_name}'
            })
            
        return jsonify({
            'success': False,
            'message': 'Invalid backup type specified'
        })
        
    except Exception as e:
        current_app.logger.error(f"Backup failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Backup failed: {str(e)}'
        })    


@bp.route('/')
@with_db
def job_list(db):
    """Display all jobs with proper time calculations."""
    jobs = db.execute('''
    WITH job_hours AS (
        SELECT 
            job_id,
            SUM(time_diff_hours(start_time, COALESCE(end_time, current_iso_time()))) as hours
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
    
    # We can log information for debugging
    logger = current_app.logger
    for job in jobs:
        if job['active_timer_id']:
            logger.info(f"Job {job['id']} has active timer. Hours: {job['accumulated_hours']}")
    
    return render_template('job_list.html', jobs=jobs)

@bp.route('/add/<int:customer_id>', methods=['GET', 'POST'])
@with_db
def add_job(db, customer_id):
    if request.method == 'POST':
        # Start transaction
        db.execute('BEGIN')
        try:
            is_template = request.form.get('save_as_template') == '1'
            template_name = request.form.get('template_name') if is_template else None
            
            # Insert the job first
            cursor = db.execute(
                'INSERT INTO job (customer_id, description, status, creation_date, '
                'base_rate, estimated_hours, is_template, template_name)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (customer_id, request.form['description'], request.form['status'],
                 get_current_time(),  # Use centralized time function
                 float(request.form['base_rate']) if request.form.get('base_rate') else None,
                 float(request.form['estimated_hours']) if request.form.get('estimated_hours') else None,
                 is_template,
                 template_name)
            )
            job_id = cursor.lastrowid
            
            # Add materials if provided
            materials = request.form.getlist('materials[]')
            quantities = request.form.getlist('quantities[]')
            prices = request.form.getlist('prices[]')
            
            # Only add materials that have actual content
            for material, quantity, price in zip(materials, quantities, prices):
                if material.strip():  # Only add non-empty materials
                    db.execute(
                        'INSERT INTO job_material (job_id, material, quantity, price, timestamp) '
                        'VALUES (?, ?, ?, ?, ?)',
                        (job_id, material.strip(), 
                         float(quantity) if quantity else 1.0,
                         float(price) if price else 0.0,
                         get_current_time())  # Use centralized time function
                    )
            
            db.commit()
            return redirect(url_for('job.job_list'))
            
        except Exception as e:
            db.execute('ROLLBACK')
            raise e
        
    customer = db.execute('SELECT * FROM customer WHERE id = ?', 
                         [customer_id]).fetchone()
    templates = db.execute('''
        SELECT * FROM job WHERE is_template = 1
        ORDER BY template_name
    ''').fetchall()
    
    return render_template('job_form.html', customer=customer, templates=templates)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@with_db
def edit_job(db, id):
    if request.method == 'POST':
        job_mgr = JobManager(db)
        job_mgr.update_job(id, request.form)
        return redirect(url_for('job.job_list'))
        
    job = db.execute('''
        SELECT job.*, customer.name as customer_name 
        FROM job JOIN customer ON job.customer_id = customer.id 
        WHERE job.id = ?''', [id]).fetchone()
    return render_template('job_form.html', job=job)

@bp.route('/<int:id>/delete', methods=['POST'])
@with_db
def delete_job(db, id):
    job_mgr = JobManager(db)
    job_mgr.delete_job(id)
    return redirect(url_for('job.job_list'))


@bp.route('/<int:id>/add_note', methods=['POST'])
@with_db
def add_note(db, id):
    note = request.form.get('note', '').strip()
    if note:
        now = get_current_time()  # Use centralized time function
        db.execute(
            'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
            (id, note, now)
        )
        db.execute(
            'UPDATE job SET last_active = ? WHERE id = ?',
            (now, id)
        )
        db.commit()
        
    return jsonify({"success": True})



@bp.route('/details/<int:id>', methods=['GET', 'POST'])
@with_db
def job_details(db, id):
    if request.method == 'POST':
        # Get the new notes from the form
        new_notes = request.form.get('notes', '').strip()
        
        if new_notes:
            # Delete all existing notes
            db.execute('DELETE FROM job_note WHERE job_id = ?', [id])
            
            # Add the new note
            now = get_current_time()  # Use centralized time function
            db.execute(
                'INSERT INTO job_note (job_id, note, timestamp) VALUES (?, ?, ?)',
                (id, new_notes, now)
            )
            db.execute(
                'UPDATE job SET last_active = ? WHERE id = ?',
                (now, id)
            )
            db.commit()
        
        return redirect(url_for('job.job_details', id=id))
    
    # Use consistent time_diff_hours function for calculations
    job = db.execute('''
    WITH job_hours AS (
        SELECT job_id,
            SUM(time_diff_hours(start_time, COALESCE(end_time, current_iso_time()))) as hours
        FROM time_entry
        GROUP BY job_id
    )
    SELECT job.*, 
           customer.name as customer_name,
           COALESCE(job_hours.hours, 0) as accumulated_hours
    FROM job 
    JOIN customer ON job.customer_id = customer.id 
    LEFT JOIN job_hours ON job_hours.job_id = job.id
    WHERE job.id = ?
''', [id]).fetchone()

    # Also use time_diff_hours for time entries
    time_entries = db.execute('''
        SELECT *,
            time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) as hours
        FROM time_entry
        WHERE job_id = ? AND 
            time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) > 0
        ORDER BY start_time DESC
    ''', [id]).fetchall()
        
    total_hours = sum(entry['hours'] for entry in time_entries)
    total_amount = total_hours * (job['base_rate'] or 0)
    
    materials = db.execute('''
        SELECT * FROM job_material 
        WHERE job_id = ? 
        ORDER BY timestamp DESC
    ''', [id]).fetchall()
    
    notes = db.execute('''
        SELECT * FROM job_note 
        WHERE job_id = ? 
        ORDER BY timestamp DESC
    ''', [id]).fetchall()
    
    combined_notes = '\n'.join(note['note'] for note in notes)
    
    # Get images for this job
    images = db.execute('''
        SELECT * FROM job_image 
        WHERE job_id = ? 
        ORDER BY timestamp DESC
    ''', [id]).fetchall()

    return render_template('job_details.html', 
                         job=job, 
                         time_entries=time_entries,
                         materials=materials,
                         notes=notes,
                         combined_notes=combined_notes,
                         total_hours=total_hours,
                         total_amount=total_amount,
                         images=images)

@bp.route('/<int:job_id>/edit_time_entry/<int:entry_id>', methods=['POST'])
@with_db
def edit_time_entry(db, job_id, entry_id):
    try:
        # Get start time and end time from form
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Log the input values
        current_app.logger.info(f"Edit time entry - received values: start={start_time}, end={end_time}")
        
        # Get user's time offset from profile
        from ..utils.profile_utils import profile_manager
        time_offset_minutes = profile_manager.get_time_offset_minutes()
        current_app.logger.info(f"User time offset: {time_offset_minutes} minutes")
        
        # Get the existing time entry
        original = db.execute('SELECT start_time, end_time FROM time_entry WHERE id = ?', [entry_id]).fetchone()
        if original:
            current_app.logger.info(f"Original values: start={original['start_time']}, end={original['end_time']}")
            
        # Convert to ISO format strings with consistent formatting and timezone
        if start_time:
            # Parse the datetime-local input value (local time)
            dt = datetime.fromisoformat(start_time)
            current_app.logger.info(f"Parsed start time: {dt}")
            
            # If there's a time offset, adjust back to UTC by subtracting the offset
            if time_offset_minutes != 0:
                dt = dt - timedelta(minutes=time_offset_minutes)
                current_app.logger.info(f"Start time adjusted to UTC: {dt}")
            
            # Format with consistent precision
            start_time = dt.replace(tzinfo=timezone.utc).isoformat(timespec='seconds')
        
        if end_time:
            # Parse the datetime-local input value (local time)
            dt = datetime.fromisoformat(end_time)
            current_app.logger.info(f"Parsed end time: {dt}")
            
            # If there's a time offset, adjust back to UTC by subtracting the offset
            if time_offset_minutes != 0:
                dt = dt - timedelta(minutes=time_offset_minutes)
                current_app.logger.info(f"End time adjusted to UTC: {dt}")
            
            # Format with consistent precision
            end_time = dt.replace(tzinfo=timezone.utc).isoformat(timespec='seconds')
        
        current_app.logger.info(f"Final values to save: start={start_time}, end={end_time}")
        
        # Update the time entry
        db.execute('''
            UPDATE time_entry 
            SET start_time = ?, end_time = ? 
            WHERE id = ? AND job_id = ?
        ''', [start_time, end_time, entry_id, job_id])
        
        db.commit()
        
        # Verify the update worked
        updated = db.execute('SELECT start_time, end_time FROM time_entry WHERE id = ?', [entry_id]).fetchone()
        if updated:
            current_app.logger.info(f"Updated values in DB: start={updated['start_time']}, end={updated['end_time']}")
        
        return redirect(url_for('job.job_details', id=job_id))
    except Exception as e:
        current_app.logger.error(f"Error updating time entry: {str(e)}", exc_info=True)
        return redirect(url_for('job.job_details', id=job_id, error=f"Error updating time entry: {str(e)}"))


@bp.route('/<int:id>/add_material', methods=['POST'])
@with_db
def add_material(db, id):
    material = request.form.get('material', '').strip()
    
    # Safely parse quantity and price, handling both decimal point and comma
    try:
        quantity_str = request.form.get('quantity', '0')
        # Replace comma with period if present (for European number format)
        quantity_str = quantity_str.replace(',', '.')
        quantity = float(quantity_str) if quantity_str else 0.0
    except ValueError:
        quantity = 0.0
    
    try:
        price_str = request.form.get('price', '0')
        # Replace comma with period if present
        price_str = price_str.replace(',', '.')
        price = float(price_str) if price_str else 0.0
    except ValueError:
        price = 0.0
    
    if material:
        material_mgr = MaterialManager(db)
        material_mgr.add_material(id, {
            'material': material,
            'quantity': quantity,
            'price': price
        })
    return redirect(url_for('job.job_details', id=id))

@bp.route('/<int:id>/delete_material/<int:material_id>', methods=['POST'])
@with_db
def delete_material(db, id, material_id):
    db.execute('DELETE FROM job_material WHERE id = ? AND job_id = ?', 
               [material_id, id])
    db.commit()
    return redirect(url_for('job.job_details', id=id))



@bp.route('/<int:id>/edit_material/<int:material_id>', methods=['POST'])
@with_db
def edit_material(db, id, material_id):
    material = request.form.get('material', '').strip()
    
    # Safely parse quantity and price, handling both decimal point and comma
    try:
        quantity_str = request.form.get('quantity', '0')
        # Replace comma with period if present (for European number format)
        quantity_str = quantity_str.replace(',', '.')
        quantity = float(quantity_str) if quantity_str else 0.0
    except ValueError:
        quantity = 0.0
    
    try:
        price_str = request.form.get('price', '0')
        # Replace comma with period if present
        price_str = price_str.replace(',', '.')
        price = float(price_str) if price_str else 0.0
    except ValueError:
        price = 0.0
    
    db.execute('''
        UPDATE job_material 
        SET material = ?, quantity = ?, price = ?
        WHERE id = ? AND job_id = ?
    ''', [material, quantity, price, material_id, id])
    db.commit()
    return redirect(url_for('job.job_details', id=id))

@bp.route('/<int:id>/delete_time_entry/<int:entry_id>', methods=['POST'])
@with_db
def delete_time_entry(db, id, entry_id):
    db.execute('DELETE FROM time_entry WHERE id = ? AND job_id = ?', 
               [entry_id, id])
    db.commit()
    return redirect(url_for('job.job_details', id=id))


@bp.route('/<int:id>/invoice')
@with_db
def invoice(db, id):
    # Get invoice date from query parameter, default to None
    invoice_date_param = request.args.get('invoice_date')
    
    # If parameter is 'today', use today's date
    if invoice_date_param == 'today':
        invoice_date = datetime.now().strftime('%Y-%m-%d')
    # If it's a valid date string, use it
    elif invoice_date_param and len(invoice_date_param) == 10:
        try:
            # Validate date format with datetime
            datetime.strptime(invoice_date_param, '%Y-%m-%d')
            invoice_date = invoice_date_param
        except ValueError:
            invoice_date = None
    else:
        invoice_date = None
        
    job = db.execute('''
        SELECT job.*, customer.*
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [id]).fetchone()
    
    # Use consistent time_diff_hours function for calculations
    time_entries = db.execute('''
        SELECT *,
        time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) as hours
        FROM time_entry
        WHERE job_id = ? AND 
              time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) > 0
        ORDER BY start_time
    ''', [id]).fetchall()
    
    materials = db.execute('''
        SELECT * FROM job_material
        WHERE job_id = ?
        ORDER BY timestamp
    ''', [id]).fetchall()
    
    invoice_number = f"{datetime.now().strftime('%Y')}-{str(id).zfill(4)}"
    
    return render_template('invoice.html',
                         job=job,
                         time_entries=time_entries,
                         materials=materials,
                         invoice_number=invoice_number,
                         invoice_date=invoice_date,
                         datetime=datetime)
    
@bp.route('/template/<int:template_id>')
@with_db
def get_template(db, template_id):
    template = db.execute('''
        SELECT * FROM job WHERE id = ? AND is_template = 1
    ''', [template_id]).fetchone()
    
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    materials = db.execute('''
        SELECT * FROM job_material
        WHERE job_id = ?
        ORDER BY id
    ''', [template_id]).fetchall()
    
    return jsonify({
        'description': template['description'],
        'base_rate': template['base_rate'],
        'estimated_hours': template['estimated_hours'],
        'materials': [{
            'material': m['material'],
            'quantity': m['quantity'],
            'price': m['price']
        } for m in materials]
    })
    
@bp.route('/quick_timer')
@with_db
def quick_timer(db):
    """Mobile-friendly timer interface with consistent time handling."""
    jobs = db.execute('''
        WITH job_hours AS (
            SELECT 
                job_id,
                SUM(time_diff_hours(start_time, COALESCE(end_time, current_iso_time()))) as hours
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
        WHERE job.status = 'Active'
        ORDER BY 
            te_active.id IS NOT NULL DESC,
            job.last_active DESC NULLS LAST,
            job.creation_date DESC
    ''').fetchall()
    
    # We can log timestamps for debugging
    logger = current_app.logger
    for job in jobs:
        if job['timer_start']:
            logger.info(f"Job {job['id']} timer_start: {job['timer_start']}")
    
    return render_template('quick_timer.html', jobs=jobs)

@bp.route('/qr_code')
def generate_qr():
    import socket
    
    # Get local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    # Create the full URL with IP and port
    quick_timer_url = f'http://{local_ip}:8080/job/quick_timer'
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(quick_timer_url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')