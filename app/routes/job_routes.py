# app/routes/job_routes.py
import shutil
from datetime import datetime
import os
import zipfile
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from ..db import with_db
from ..utils.job_utils import JobManager
from ..utils.material_utils import MaterialManager
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

# app/routes/job_routes.py
@bp.route('/')
@with_db
def job_list(db):
    jobs = db.execute('''
        WITH job_hours AS (
            SELECT 
                job_id,
                SUM(
                    CASE 
                        WHEN end_time IS NULL THEN
                            (julianday(datetime('now')) - julianday(start_time)) * 24
                        ELSE
                            (julianday(end_time) - julianday(start_time)) * 24
                    END
                ) as hours
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

# app/routes/job_routes.py

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
                 datetime.now().isoformat(), 
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
                         datetime.now().isoformat())
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
        now = datetime.now().isoformat()
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
            now = datetime.now().isoformat()
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
    
    job = db.execute('''
        WITH job_hours AS (
            SELECT job_id,
                SUM((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24) as hours
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
    
    time_entries = db.execute('''
        SELECT *, 
        (julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 as hours
        FROM time_entry 
        WHERE job_id = ? 
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
                         images=images)  # Add images to template context

@bp.route('/<int:job_id>/edit_time_entry/<int:entry_id>', methods=['POST'])
@with_db
def edit_time_entry(db, job_id, entry_id):
    db.execute('''
        UPDATE time_entry 
        SET start_time = ?, end_time = ? 
        WHERE id = ? AND job_id = ?
    ''', [request.form['start_time'], request.form['end_time'], 
          entry_id, job_id])
    db.commit()
    return redirect(url_for('job.job_details', id=job_id))

@bp.route('/<int:id>/add_material', methods=['POST'])
@with_db
def add_material(db, id):
    material = request.form.get('material', '').strip()
    quantity = request.form.get('quantity', 0, type=float)
    price = request.form.get('price', 0, type=float)
    
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
    db.execute('''
        UPDATE job_material 
        SET material = ?, quantity = ?, price = ?
        WHERE id = ? AND job_id = ?
    ''', [request.form['material'], request.form['quantity'], 
          request.form['price'], material_id, id])
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
    job = db.execute('''
        SELECT job.*, customer.*
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [id]).fetchone()
    
    time_entries = db.execute('''
        SELECT *,
        (julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 as hours
        FROM time_entry
        WHERE job_id = ? AND 
              (julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 > 0
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
                         invoice_number=invoice_number)
    
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
    
    
# Mobile phone route to app/routes/job_routes.py
@bp.route('/quick_timer')
@with_db
def quick_timer(db):
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
        WHERE job.status = 'Active'
        ORDER BY 
            te_active.id IS NOT NULL DESC,
            CASE job.status
                WHEN 'Active' THEN 1
                WHEN 'Pending' THEN 2
            END,
            job.last_active DESC NULLS LAST,
            job.creation_date DESC
    ''').fetchall()
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