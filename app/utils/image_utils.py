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