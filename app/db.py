# app/db.py
import sqlite3
from functools import wraps
from flask import g, current_app
import logging
from datetime import datetime

logger = logging.getLogger('jobmanager')

def get_db():
    """Get a database connection, reusing it if already exists in current context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        
        # Initialize custom time functions
        g.db = init_db_time_functions(g.db)
        
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def with_db(f):
    """Decorator to handle database connections for route functions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db = get_db()
        return f(db, *args, **kwargs)
    return decorated_function

def init_db():
    """Initialize database schema."""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def backup_db():
    """Create a backup of the database."""
    try:
        db_path = current_app.config['DATABASE']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{db_path}.backup_{timestamp}"
        
        # Close any existing connection
        close_db()
        
        with open(db_path, 'rb') as source:
            with open(backup_path, 'wb') as target:
                target.write(source.read())
                
        logger.info(f"Database backed up to {backup_path}")
        return True, backup_path
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        return False, str(e)

def get_job_with_customer(db, job_id):
    """Get job details including customer information."""
    return db.execute('''
        SELECT job.*, customer.name as customer_name
        FROM job
        JOIN customer ON job.customer_id = customer.id
        WHERE job.id = ?
    ''', [job_id]).fetchone()

def get_job_with_hours(db, job_id):
    """Get job details including accumulated hours."""
    return db.execute('''
        WITH job_hours AS (
            SELECT job_id,
                SUM((julianday(COALESCE(end_time, datetime('now', 'localtime'))) - 
                     julianday(start_time)) * 24) as hours
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
    ''', [job_id]).fetchone()

def get_active_timer(db):
    """Get currently active timer if any exists.
    
    Args:
        db: Database connection
        
    Returns:
        dict: Active timer entry or None
    """
    return db.execute('''
        SELECT time_entry.*, job.id as job_id
        FROM time_entry 
        JOIN job ON time_entry.job_id = job.id
        WHERE time_entry.end_time IS NULL
    ''').fetchone()

def calculate_job_total_hours(db, job_id):
    """Calculate total hours for a job using custom time functions."""
    result = db.execute('''
        SELECT 
            SUM(time_diff_hours(start_time, COALESCE(end_time, current_iso_time()))) as total_hours
        FROM time_entry
        WHERE job_id = ? AND 
              time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) > 0.03
    ''', [job_id]).fetchone()
    
    total_hours = result['total_hours'] if result['total_hours'] else 0
    return round(total_hours * 12) / 12  # Round to nearest 5 minutes


def get_job_materials(db, job_id):
    """Get all materials for a specific job."""
    return db.execute('''
        SELECT * FROM job_material 
        WHERE job_id = ? 
        ORDER BY timestamp DESC
    ''', [job_id]).fetchall()

# Use the custom functions in queries
def get_job_time_entries(db, job_id):
    """Get all time entries for a specific job using custom time functions."""
    return db.execute('''
        SELECT 
            time_entry.*,
            time_diff_hours(start_time, COALESCE(end_time, current_iso_time())) as hours
        FROM time_entry 
        WHERE job_id = ? 
        ORDER BY start_time DESC
    ''', [job_id]).fetchall()


def init_db_time_functions(db):
    """Initialize SQLite with custom functions for time handling."""
    from datetime import datetime, timezone
    
    # Use the same UTC format consistently
    def get_current_iso_time():
        """Return current time in ISO format with UTC timezone."""
        return datetime.now(timezone.utc).isoformat()
    
    def time_diff_hours(start_time, end_time=None):
        """Calculate time difference in hours between two timestamps."""
        try:
            # Parse timestamps, handling different possible formats
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                # Handle timestamps with 'Z' suffix
                if 'Z' in start_time:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                else:
                    # Assume naive timestamps are in UTC
                    start_dt = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
            
            if end_time:
                try:
                    end_dt = datetime.fromisoformat(end_time)
                except ValueError:
                    if 'Z' in end_time:
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    else:
                        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
            else:
                end_dt = datetime.now(timezone.utc)
            
            # Normalize timezone info
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            
            return (end_dt - start_dt).total_seconds() / 3600
        except Exception:
            return 0
    
    db.create_function("current_iso_time", 0, get_current_iso_time)
    db.create_function("time_diff_hours", 2, time_diff_hours)
    return db