# app/__init__.py
from flask import Flask
import sqlite3
import os

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = os.path.join(app.instance_path, 'jobmanager.db')
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    from . import routes
    app.register_blueprint(routes.bp)
    
    return app