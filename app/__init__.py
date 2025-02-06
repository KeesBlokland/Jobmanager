# app/__init__.py
from flask import Flask
import sqlite3
import os

def month_name(month_num):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    try:
        return months[int(month_num) - 1]
    except (ValueError, IndexError):
        return month_num

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = os.path.join(app.instance_path, 'jobmanager.db')
    
    # Register the month_name filter
    app.jinja_env.filters['month_name'] = month_name
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    from . import routes
    app.register_blueprint(routes.bp)
    
    return app

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read().decode('utf8'))