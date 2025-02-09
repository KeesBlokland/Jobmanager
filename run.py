# run.py
from app import create_app
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_production_logging():
    # Ensure logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up rotating file handler (10 MB per file, keep 10 files)
    file_handler = RotatingFileHandler(
        'logs/jobmanager.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    
    # Set up console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

if __name__ == '__main__':
    setup_production_logging()
    
    app = create_app()
    logger = logging.getLogger('jobmanager')
    
    try:
        logger.info("Starting Job Manager application")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise