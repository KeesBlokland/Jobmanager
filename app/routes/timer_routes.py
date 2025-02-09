# app/routes/timer_routes.py
from flask import Blueprint, jsonify
from ..utils.db_utils import with_db
from ..utils.timer_utils import TimerManager
from datetime import datetime

bp = Blueprint('timer', __name__)

@bp.route('/job/<int:id>/start_timer', methods=['POST'])
@with_db 
def start_timer(db, id):
    timer = TimerManager(db)
    timer.start(id)
    return jsonify({'success': True})

@bp.route('/job/<int:id>/stop_timer', methods=['POST'])
@with_db
def stop_timer(db, id):
    timer = TimerManager(db)
    timer.stop(id)
    return jsonify({'success': True})

@bp.route('/job/<int:id>/pause_timer', methods=['POST'])
@with_db
def pause_timer(db, id):
    timer = TimerManager(db)
    now = datetime.now().isoformat()
    timer.stop(id)
    return jsonify({'success': True})

@bp.route('/job/<int:id>/resume_timer', methods=['POST'])
@with_db
def resume_timer(db, id):
    timer = TimerManager(db)
    timer.start(id)
    return jsonify({'success': True})

@bp.route('/job/<int:id>/update_total', methods=['POST'])
@with_db
def update_job_total(db, id):
    timer = TimerManager(db)
    total = timer.calculate_total_hours(id)
    return jsonify({
        'success': True,
        'total_hours': total
    })