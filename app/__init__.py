# app/__init__.py
from flask import Flask, render_template
import os
from .utils.error_utils import setup_logging, DatabaseError, TimerError

# Inside create_app():
app = Flask(__name__)


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
    
    
    # Setup logging
    app.logger = setup_logging()
    
    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Database configuration
    app.config['DATABASE'] = os.path.join(app.instance_path, 'jobmanager.db')
    
    # Register error handlers
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        app.logger.error(f"Database error: {str(error)}")
        return "Database error occurred", 500
        
    @app.errorhandler(TimerError)
    def handle_timer_error(error):
        app.logger.error(f"Timer error: {str(error)}")
        return "Timer operation failed", 500
        
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error(f"Unexpected error: {str(error)}")
        return "An unexpected error occurred", 500

    # Register routes and database handlers
    from . import routes
    routes.init_app(app)
    
    # Register database commands
    from .utils.db_utils import close_db
    app.teardown_appcontext(close_db)
    
    return app