# init_db.py
import os
import sqlite3
from app import create_app

app = create_app()

def init_db():
    with app.app_context():
        from app.routes import get_db
        db = get_db()
        
        # Get the absolute path to schema.sql
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'schema.sql')
        
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()