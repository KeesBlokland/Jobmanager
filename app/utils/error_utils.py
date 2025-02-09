# app/utils/error_utils.py
from functools import wraps
import logging
from flask import current_app
import traceback

class JobManagerError(Exception):
    """Base exception for job manager errors"""
    pass

class DatabaseError(JobManagerError):
    """Database operation errors"""
    pass

class TimerError(JobManagerError):
    """Timer operation errors"""
    pass

def setup_logging():
    # Create logs directory if it doesn't exist
    import os
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up file handler
    file_handler = logging.FileHandler('logs/jobmanager.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    
    # Set up logger
    logger = logging.getLogger('jobmanager')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    return logger

def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger = current_app.logger
        try:
            return f(*args, **kwargs)
        except DatabaseError as e:
            logger.error(f"Database error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            raise
        except TimerError as e:
            logger.error(f"Timer error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            raise
    return decorated_function