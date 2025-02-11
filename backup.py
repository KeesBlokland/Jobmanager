# app_backup.py
import os
import zipfile
from datetime import datetime
import shutil
import logging

def create_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    backup_name = f'jobmanager_backup_{timestamp}.zip'
    
    include_dirs = ['app', 'instance']
    include_files = ['run.py', 'init_db.py', 'gitback.sh', 'LICENSE']
    
    # Explicitly what to exclude
    EXCLUDE_PREFIXES = ['instance/images/', 'instance/backups/']
    
    try:
        with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add individual files
            for file in include_files:
                if os.path.exists(file):
                    zipf.write(file)
                    logging.info(f"Adding file: {file}")
                    
            # Add directories
            for dir_name in include_dirs:
                if os.path.exists(dir_name):
                    for root, dirs, files in os.walk(dir_name):
                        # Convert Windows paths if needed
                        root_path = root.replace('\\', '/')
                        
                        # Debug print
                        logging.info(f"Checking path: {root_path}")
                        
                        # Check if this directory should be excluded
                        if any(root_path.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
                            logging.info(f"Excluding directory: {root_path}")
                            dirs[:] = []
                            continue
                            
                        for file in files:
                            if file.endswith('.db'):
                                continue
                                
                            file_path = os.path.join(root, file).replace('\\', '/')
                            
                            # Check if file path should be excluded
                            if not any(file_path.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
                                zipf.write(file_path)
                                logging.info(f"Adding file: {file_path}")
                            else:
                                logging.info(f"Excluding file: {file_path}")
                                
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            shutil.move(backup_name, os.path.join(backup_dir, backup_name))
            
    except Exception as e:
        logging.error(f"Error creating backup: {str(e)}")

if __name__ == '__main__':
    create_backup()