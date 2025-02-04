# app/routes.py
from flask import Blueprint, render_template, current_app, g
import sqlite3

bp = Blueprint('main', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@bp.teardown_app_request
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@bp.route('/')
def index():
    return render_template('base.html')
