# app/__init__.py
from flask import Flask
import os
from .utils.error_utils import setup_logging
from . import db
from .utils.date_helper import add_template_helpers  # Import the new helper

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
    
    # Add the new date helper functions
    add_template_helpers(app)
    
    # Setup logging
    app.logger = setup_logging()
    
    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Database configuration
    app.config['DATABASE'] = os.path.join(app.instance_path, 'jobmanager.db')
    
    # Register database commands
    app.teardown_appcontext(db.close_db)
    
    # Register routes
    from . import routes
    routes.init_app(app)
    
    # Custom error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return app.render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return app.render_template('500.html'), 500
    
    return app