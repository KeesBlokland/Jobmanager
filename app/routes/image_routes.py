# app/routes/image_routes.py
from flask import Blueprint, request, jsonify, send_file, abort, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ..db import with_db
from ..utils.image_utils import ImageManager
import logging

bp = Blueprint('image', __name__)
logger = logging.getLogger('jobmanager')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = 'instance/uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload/direct/<int:job_id>', methods=['POST'])
@with_db
def upload_direct(db, job_id):
    """Handle direct file uploads from mobile/desktop"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        image_mgr = ImageManager(os.path.join(current_app.instance_path, 'images'))
        filename = image_mgr.process_image(job_id, file, db)
        
        # Store in database
        db.execute(
            'INSERT INTO job_image (job_id, filename, description, timestamp) VALUES (?, ?, ?, ?)',
            (job_id, filename, request.form.get('description', ''), datetime.now().isoformat())
        )
        db.commit()
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/upload/watch/<int:job_id>', methods=['POST'])
@with_db
def process_watch_folder(db, job_id):
    """Process images from a watch folder"""
    watch_folder = os.path.join(current_app.instance_path, UPLOAD_FOLDER, f'job_{job_id}')
    
    if not os.path.exists(watch_folder):
        return jsonify({'error': 'Watch folder does not exist'}), 400
        
    image_mgr = ImageManager(os.path.join(current_app.instance_path, 'images'))
    processed = []
    errors = []
    
    for filename in os.listdir(watch_folder):
        if not allowed_file(filename):
            continue
            
        filepath = os.path.join(watch_folder, filename)
        try:
            with open(filepath, 'rb') as file:
                new_filename = image_mgr.process_image(job_id, file, db)
                
                # Store in database
                db.execute(
                    'INSERT INTO job_image (job_id, filename, timestamp) VALUES (?, ?, ?)',
                    (job_id, new_filename, datetime.now().isoformat())
                )
                
                processed.append(filename)
                os.remove(filepath)  # Remove processed file
                
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
            logger.error(f"Processing failed for {filename}: {str(e)}", exc_info=True)
    
    db.commit()
    return jsonify({
        'success': True,
        'processed': processed,
        'errors': errors
    })

@bp.route('/watch/setup/<int:job_id>', methods=['POST'])
def setup_watch_folder(job_id):
    """Create a watch folder for a specific job"""
    folder_path = os.path.join(current_app.instance_path, UPLOAD_FOLDER, f'job_{job_id}')
    try:
        os.makedirs(folder_path, exist_ok=True)
        return jsonify({
            'success': True,
            'path': folder_path
        })
    except Exception as e:
        logger.error(f"Watch folder setup failed: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    
@bp.route('/serve/<int:job_id>/<path:filename>')
def serve_image(job_id, filename):
    """Serve an image file"""
    try:
        thumbnail = request.args.get('thumbnail', 'false').lower() == 'true'
        image_mgr = ImageManager(os.path.join(current_app.instance_path, 'images'))
        return send_file(
            image_mgr.get_image_path(job_id, filename, thumbnail),
            mimetype='image/jpeg'
        )
    except FileNotFoundError:
        abort(404)