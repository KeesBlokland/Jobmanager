# app/init_db.py
from app import create_app

app = create_app()

def init_db():
    with app.app_context():
        from app.routes import get_db
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read())  # Remove the decode() since it's already a string
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()