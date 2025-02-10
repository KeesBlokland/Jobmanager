# app_backup.py
import os
import zipfile
from datetime import datetime
import shutil

def create_backup():
    # Get current date-time for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    backup_name = f'jobmanager_backup_{timestamp}.zip'

    # Define what to include and exclude
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
        'logs',
        '.db',
        '.md',
        '.txt',
        '.jpg',
        'backups',
        '.zip'
    ]
    
    # Add specific paths to exclude
    exclude_paths = ['/app/instance/images']

    try:
        with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add individual files from root
            for file in include_files:
                if os.path.exists(file):
                    zipf.write(file)

            # Add directories
            for dir_name in include_dirs:
                if os.path.exists(dir_name):
                    for root, dirs, files in os.walk(dir_name):
                        # Check if current path should be excluded
                        if any(excluded in root for excluded in exclude_paths):
                            continue
                            
                        # Remove excluded directories
                        dirs[:] = [d for d in dirs if d not in exclude_patterns]
                        
                        for file in files:
                            # Check if file should be excluded
                            if not any(file.endswith(pat.strip('*')) for pat in exclude_patterns):
                                file_path = os.path.join(root, file)
                                zipf.write(file_path)

            print(f"Backup created successfully: {backup_name}")

            # Optional: Move backup to a backup directory
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            shutil.move(backup_name, os.path.join(backup_dir, backup_name))
            print(f"Backup moved to {backup_dir} directory")

    except Exception as e:
        print(f"Error creating backup: {str(e)}")

if __name__ == '__main__':
    create_backup()