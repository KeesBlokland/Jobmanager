# migrate.py
import sqlite3
import os
import shutil
from datetime import datetime
import logging

def setup_migration_logging():
    # Ensure logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    logging.basicConfig(
        filename=f'logs/migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

def backup_database(db_path):
    """Create a backup of the existing database"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    logging.info(f"Database backed up to {backup_path}")
    return backup_path

def migrate():
    setup_migration_logging()
    logging.info("Starting migration")
    
    # Database paths
    old_db_path = 'instance/jobmanager.db'
    
    # Verify old database exists
    if not os.path.exists(old_db_path):
        logging.error("Original database not found!")
        return False
        
    try:
        # Backup existing database
        backup_path = backup_database(old_db_path)
        logging.info("Database backup created successfully")
        
        # Connect to the database
        conn = sqlite3.connect(old_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Add new columns and tables
        migration_steps = [
            ("ALTER TABLE job ADD COLUMN is_template INTEGER DEFAULT 0", True),
            ("ALTER TABLE job ADD COLUMN template_name TEXT", True),
            ("""CREATE TABLE IF NOT EXISTS template_material (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                material TEXT NOT NULL,
                quantity REAL DEFAULT 1,
                price REAL DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES job (id)
            )""", False),
            ("CREATE INDEX IF NOT EXISTS idx_job_template ON job(is_template)", False),
        ]
        
        for sql, allow_fail in migration_steps:
            try:
                cursor.execute(sql)
                logging.info(f"Executed: {sql}")
            except sqlite3.OperationalError as e:
                if not allow_fail:
                    raise
                logging.warning(f"Ignored error in step {sql}: {str(e)}")
        
        # Commit changes
        conn.commit()
        logging.info("Migration completed successfully")
        
        return True
        
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        # Restore from backup
        if 'backup_path' in locals():
            shutil.copy2(backup_path, old_db_path)
            logging.info("Restored database from backup")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if migrate():
        print("Migration completed successfully. Check logs for details.")
    else:
        print("Migration failed. Check logs for details.")