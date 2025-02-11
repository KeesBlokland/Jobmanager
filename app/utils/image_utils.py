# app/utils/image_utils.py
from PIL import Image
from PIL.ExifTags import TAGS
import os
from datetime import datetime
import sqlite3

class ImageManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.THUMBNAIL_SIZE = (300, 300)
        self.MAX_SIZE = (1024, 1024)

    def get_job_identifier(self, db, job_id):
        """Get invoice number or job ID to use in filename"""
        result = db.execute(
            'SELECT invoice_number FROM job WHERE id = ?',
            (job_id,)
        ).fetchone()
        
        if result and result['invoice_number']:
            # Remove year prefix from invoice number (e.g., '2025-0004' becomes '0004')
            return result['invoice_number'].split('-')[1]
        return f"job{job_id}"

    def process_image(self, job_id, image_file, db=None):
        # Create job directory if it doesn't exist
        job_path = os.path.join(self.base_path, f'job_{job_id}')
        thumb_path = os.path.join(job_path, 'thumbnails')
        os.makedirs(thumb_path, exist_ok=True)

        # Generate filename with job identifier
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        job_identifier = self.get_job_identifier(db, job_id) if db else f"job{job_id}"
        filename = f'{job_identifier}-{timestamp}.jpg'

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