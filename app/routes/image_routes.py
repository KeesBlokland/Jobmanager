# app/routes/image_routes.py
from flask import Blueprint, request, jsonify, send_file, abort, current_app, url_for, redirect
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
import uuid
import json
import zipfile
import io
from ..db import with_db
from ..utils.image_utils import ImageManager
import logging

bp = Blueprint('image', __name__)
logger = logging.getLogger('jobmanager')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = 'instance/uploads'

# Store temporary share links
SHARE_LINKS = {}

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
    timestamp = (datetime.now() + timedelta(hours=1)).strftime('%y%m%d%H%M')
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

@bp.route('/delete/<int:job_id>/<int:image_id>', methods=['POST'])
@with_db
def delete_image(db, job_id, image_id):
    """Delete an image file"""
    try:
        # Get image record
        image = db.execute(
            'SELECT * FROM job_image WHERE id = ? AND job_id = ?',
            (image_id, job_id)
        ).fetchone()
        
        if not image:
            # Redirect back to job details page instead of showing error
            logger.warning(f"Attempted to delete non-existent image {image_id} for job {job_id}")
            return redirect(url_for('job.job_details', id=job_id))
            
        filename = image['filename']
        logger.info(f"Deleting image {filename} (ID: {image_id}) from job {job_id}")
        
        # Delete physical files
        image_mgr = ImageManager(os.path.join(current_app.instance_path, 'images'))
        try:
            # Delete main image
            main_path = image_mgr.get_image_path(job_id, filename)
            if os.path.exists(main_path):
                os.remove(main_path)
                logger.info(f"Deleted main image file: {main_path}")
            else:
                logger.warning(f"Main image file not found: {main_path}")
                
            # Delete thumbnail
            thumb_path = image_mgr.get_image_path(job_id, filename, thumbnail=True)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                logger.info(f"Deleted thumbnail file: {thumb_path}")
            else:
                logger.warning(f"Thumbnail file not found: {thumb_path}")
        except OSError as e:
            logger.error(f"Error deleting image files: {str(e)}")
            # Continue to delete database record even if file deletion fails
        
        # Delete database record
        db.execute('DELETE FROM job_image WHERE id = ?', (image_id,))
        db.commit()
        logger.info(f"Deleted image record from database: {image_id}")
        
        # Redirect back to job details page
        return redirect(url_for('job.job_details', id=job_id))
    except Exception as e:
        logger.error(f"Image deletion failed: {str(e)}", exc_info=True)
        # Redirect with error param instead of showing JSON error
        return redirect(url_for('job.job_details', id=job_id, error=str(e)))

@bp.route('/share/<int:job_id>', methods=['POST'])
@with_db
def create_share_link(db, job_id):
    """Create a temporary share link for images"""
    try:
        # Get images to share
        image_ids = request.json.get('image_ids', [])
        expiry_hours = request.json.get('expiry_hours', 24)
        
        # Validate job exists
        job = db.execute('SELECT * FROM job WHERE id = ?', (job_id,)).fetchone()
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # If no specific images, share all images for this job
        if not image_ids:
            images = db.execute(
                'SELECT * FROM job_image WHERE job_id = ?',
                (job_id,)
            ).fetchall()
        else:
            images = db.execute(
                'SELECT * FROM job_image WHERE id IN ({}) AND job_id = ?'.format(
                    ','.join(['?'] * len(image_ids))
                ),
                image_ids + [job_id]
            ).fetchall()
        
        if not images:
            return jsonify({'error': 'No images found'}), 404
            
        # Create share token
        share_token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(hours=expiry_hours)
        
        SHARE_LINKS[share_token] = {
            'job_id': job_id,
            'images': [{'id': img['id'], 'filename': img['filename']} for img in images],
            'expires': expiry.isoformat(),
            'customer_name': job['customer_name'] if 'customer_name' in job else None,
            'job_description': job['description']
        }
        
        # Generate share URL
        share_url = url_for('image.shared_images', token=share_token, _external=True)
        
        return jsonify({
            'success': True,
            'share_url': share_url,
            'expires': expiry.isoformat()
        })
    except Exception as e:
        logger.error(f"Creating share link failed: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/shared/<token>')
def shared_images(token):
    """Display shared images"""
    if token not in SHARE_LINKS:
        abort(404)
        
    share_data = SHARE_LINKS[token]
    
    # Check if expired
    if datetime.now() > datetime.fromisoformat(share_data['expires']):
        del SHARE_LINKS[token]
        abort(410)  # Gone
        
    return render_template(
        'shared_images.html',
        share_data=share_data,
        token=token
    )

@bp.route('/download/<token>')
def download_images(token):
    """Download all shared images as ZIP"""
    if token not in SHARE_LINKS:
        abort(404)
        
    share_data = SHARE_LINKS[token]
    
    # Check if expired
    if datetime.now() > datetime.fromisoformat(share_data['expires']):
        del SHARE_LINKS[token]
        abort(410)  # Gone
    
    try:
        # Create in-memory ZIP file
        memory_file = io.BytesIO()
        job_id = share_data['job_id']
        image_mgr = ImageManager(os.path.join(current_app.instance_path, 'images'))
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in share_data['images']:
                image_path = image_mgr.get_image_path(job_id, img['filename'])
                if os.path.exists(image_path):
                    zf.write(image_path, img['filename'])
        
        # Reset file pointer and send file
        memory_file.seek(0)
        job_identifier = f"job_{job_id}"
        filename = f"{job_identifier}_images_{datetime.now().strftime('%Y%m%d')}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Download ZIP failed: {str(e)}", exc_info=True)
        abort(500)