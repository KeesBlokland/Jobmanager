# app/__init__.py
import os
import logging
import sys

from flask import Flask, render_template
from .utils.error_utils import setup_logging
from . import db
from .utils.date_helper import add_template_helpers
from .utils.jinja_filters import register_jinja_filters
from .utils import profile_utils
from pathlib import Path


def create_app():
    app = Flask(__name__)
    
    def month_name(month):
        months = {
            '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
        }
        return months.get(month, month)
    
    app.jinja_env.filters['month_name'] = month_name
    # Add the date helper functions
    add_template_helpers(app)
    # Register custom Jinja filters for time display
    register_jinja_filters(app)
    # Setup logging
    app.logger = setup_logging()

    
    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Database configuration
    app.config['DATABASE'] = os.path.join(app.instance_path, 'jobmanager.db')
    
    # Initialize the database if it doesn't exist
    db_path = app.config['DATABASE']
    db_exists = os.path.exists(db_path)
    
    if not db_exists:
        app.logger.info("Database does not exist, initializing...")
        
        # Import the database initializer
        # The initializer is outside the app package, so we need to handle imports carefully
        try:
            # Try to import directly if the script is in the Python path
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from db_init import ensure_database_exists
        except ImportError:
            # If that fails, try to import using a relative path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(current_dir, "db_init.py")
            
            if os.path.exists(script_path):
                # Create a module spec and import the script
                import importlib.util
                spec = importlib.util.spec_from_file_location("db_init", script_path)
                db_init = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(db_init)
                ensure_database_exists = db_init.ensure_database_exists
            else:
                app.logger.error(f"Could not import db_init.py, file not found at {script_path}")
                ensure_database_exists = None
        
        if ensure_database_exists:
            # Initialize the database with demo data
            is_new = ensure_database_exists(db_path, with_demo_data=True)
            if is_new:
                app.logger.info("Database initialized successfully")
    
    # Register database commands
    app.teardown_appcontext(db.close_db)
    
    # Initialize user profile
    profile_utils.init_app(app)
    
    # Register routes
    from . import routes
    routes.init_app(app)
    
    # Add the profile to the Jinja environment
    @app.context_processor
    def inject_profile():
        return {'user_profile': profile_utils.profile_manager.get_profile()}
    
    # Custom error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    return app