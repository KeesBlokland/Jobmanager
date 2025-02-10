# Job Image Management System

## Storage Strategy

### 1. File Structure
```
/home/pi/jobmanager/
├── instance/
│   ├── jobmanager.db
│   └── images/
│       ├── job_1/
│       │   ├── thumbnails/
│       │   │   ├── img_20250209_001.jpg
│       │   │   └── img_20250209_002.jpg
│       │   ├── img_20250209_001.jpg
│       │   └── img_20250209_002.jpg
│       └── job_2/
           └── ...
```

### 2. Database Schema Addition
```sql
-- Add to schema.sql
CREATE TABLE IF NOT EXISTS job_image (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    description TEXT,
    timestamp TEXT NOT NULL,
    location TEXT,  -- Optional GPS coordinates
    tags TEXT,      -- Comma-separated tags
    FOREIGN KEY (job_id) REFERENCES job (id)
);
```

### 3. Image Processing
We'll use Pillow (PIL) for Python - it's lightweight and efficient:

```python
# app/utils/image_utils.py
from PIL import Image
from PIL.ExifTags import TAGS
import os
from datetime import datetime
import hashlib

class ImageManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.THUMBNAIL_SIZE = (300, 300)
        self.MAX_SIZE = (1024, 1024)

    def process_image(self, job_id, image_file):
        # Create job directory if it doesn't exist
        job_path = os.path.join(self.base_path, f'job_{job_id}')
        thumb_path = os.path.join(job_path, 'thumbnails')
        os.makedirs(thumb_path, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(image_file.read()).hexdigest()[:6]
        filename = f'img_{timestamp}_{file_hash}.jpg'
        
        # Reset file pointer
        image_file.seek(0)

        # Open and process image
        with Image.open(image_file) as img:
            # Auto-rotate based on EXIF
            try:
                for orientation in TAGS.keys():
                    if TAGS[orientation] == 'Orientation':
                        break
                exif = dict(img._getexif().items())
                if exif[orientation] == 3:
                    img = img.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    img = img.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                pass

            # Resize if needed
            if img.size[0] > self.MAX_SIZE[0] or img.size[1] > self.MAX_SIZE[1]:
                img.thumbnail(self.MAX_SIZE, Image.LANCZOS)

            # Save main image
            img.save(os.path.join(job_path, filename), 
                    'JPEG', 
                    quality=85, 
                    optimize=True)

            # Create thumbnail
            img.thumbnail(self.THUMBNAIL_SIZE, Image.LANCZOS)
            img.save(os.path.join(thumb_path, filename),
                    'JPEG',
                    quality=70,
                    optimize=True)

        return filename

    def get_image_path(self, job_id, filename, thumbnail=False):
        base = os.path.join(self.base_path, f'job_{job_id}')
        if thumbnail:
            return os.path.join(base, 'thumbnails', filename)
        return os.path.join(base, filename)
```

### 4. Flask Routes

```python
# app/routes/job_routes.py (additions)
from ..utils.image_utils import ImageManager
from flask import send_file

image_manager = ImageManager(os.path.join(current_app.instance_path, 'images'))

@bp.route('/<int:id>/add_image', methods=['POST'])
@with_db
def add_image(db, id):
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
        
    image = request.files['image']
    description = request.form.get('description', '')
    
    if image.filename == '':
        return jsonify({'error': 'No image selected'}), 400
        
    try:
        filename = image_manager.process_image(id, image)
        
        db.execute(
            'INSERT INTO job_image (job_id, filename, description, timestamp) '
            'VALUES (?, ?, ?, ?)',
            (id, filename, description, datetime.now().isoformat())
        )
        db.commit()
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/image/<int:job_id>/<path:filename>')
def serve_image(job_id, filename):
    thumbnail = request.args.get('thumbnail', 'false').lower() == 'true'
    try:
        return send_file(
            image_manager.get_image_path(job_id, filename, thumbnail),
            mimetype='image/jpeg'
        )
    except FileNotFoundError:
        abort(404)
```

### 5. Template Modifications

```html
<!-- job_details.html (addition) -->
<div class="detail-section">
    <h3>Photos</h3>
    <div class="image-upload">
        <form action="{{ url_for('job.add_image', id=job.id) }}" 
              method="post" 
              enctype="multipart/form-data">
            <input type="file" name="image" accept="image/*" capture="environment">
            <input type="text" name="description" placeholder="Image description">
            <button type="submit" class="action-btn save-btn">Upload</button>
        </form>
    </div>
    
    <div class="image-gallery">
        {% for image in images %}
        <div class="image-item">
            <img src="{{ url_for('job.serve_image', 
                                job_id=job.id, 
                                filename=image.filename, 
                                thumbnail=true) }}"
                 onclick="showFullImage('{{ url_for('job.serve_image', 
                                                   job_id=job.id, 
                                                   filename=image.filename) }}',
                                      '{{ image.description }}')"
                 alt="{{ image.description }}">
            <p class="image-description">{{ image.description }}</p>
            <span class="image-timestamp">{{ image.timestamp[:-7] }}</span>
        </div>
        {% endfor %}
    </div>
</div>

<!-- Add to base.html -->
<div id="image-modal" class="modal" onclick="this.style.display='none'">
    <img class="modal-content" id="full-image">
    <div id="image-caption"></div>
</div>

<style>
.image-gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
    padding: 10px;
}

.image-item {
    position: relative;
    cursor: pointer;
}

.image-item img {
    width: 100%;
    height: auto;
    border-radius: 4px;
}

.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.9);
}

.modal-content {
    margin: auto;
    display: block;
    max-width: 90%;
    max-height: 90%;
}

#image-caption {
    color: white;
    text-align: center;
    padding: 10px;
}
</style>

<script>
function showFullImage(src, description) {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('full-image');
    const caption = document.getElementById('image-caption');
    
    img.src = src;
    caption.innerHTML = description;
    modal.style.display = 'flex';
}
</script>
```

### 6. Maintenance Scripts

```python
# cleanup_images.py
import os
import sqlite3
from datetime import datetime, timedelta

def cleanup_orphaned_images():
    """Remove image files that don't have database entries"""
    db = sqlite3.connect('instance/jobmanager.db')
    cursor = db.cursor()
    
    # Get all image records
    cursor.execute('SELECT job_id, filename FROM job_image')
    valid_images = set((row[0], row[1]) for row in cursor.fetchall())
    
    base_path = 'instance/images'
    for job_dir in os.listdir(base_path):
        if not job_dir.startswith('job_'):
            continue
            
        job_id = int(job_dir.split('_')[1])
        job_path = os.path.join(base_path, job_dir)
        
        for root, dirs, files in os.walk(job_path):
            for file in files:
                if file.endswith('.jpg'):
                    if (job_id, file) not in valid_images:
                        os.remove(os.path.join(root, file))

def compress_old_images():
    """Further compress images older than 6 months"""
    db = sqlite3.connect('instance/jobmanager.db')
    cursor = db.cursor()
    
    six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()
    
    cursor.execute('''
        SELECT job_id, filename 
        FROM job_image 
        WHERE timestamp < ?
    ''', (six_months_ago,))
    
    for job_id, filename in cursor.fetchall():
        path = f'instance/images/job_{job_id}/{filename}'
        if os.path.exists(path):
            with Image.open(path) as img:
                img.save(path, 'JPEG', quality=60, optimize=True)
```

## Storage Considerations

1. Space Requirements:
   - 1024x1024 JPEG ≈ 100-200KB per image
   - Thumbnail ≈ 20-30KB per image
   - 10 images per job = ~2MB per job
   - 1000 jobs = ~2GB for images

2. Optimization:
   - Aggressive compression for older images
   - Automatic cleanup of orphaned files
   - Option to archive old jobs with images to external storage

3. Backup Strategy:
   - Include images in regular backups
   - Option to exclude thumbnails (can be regenerated)
   - Consider incremental backups for images

4. Performance:
   - Thumbnails for gallery view
   - Lazy loading for image grid
   - Client-side caching
   - Nginx caching for images

