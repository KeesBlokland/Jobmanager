# app/routes/system_routes.py
from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime, timezone, timedelta
import os
import logging
from ..db import with_db
from ..utils.profile_utils import profile_manager

bp = Blueprint('system', __name__)
logger = logging.getLogger('jobmanager')

@bp.route('/settings')
@with_db
def settings(db):
    """Render system settings page"""
    # Get current system time info
    now = datetime.now()
    
    return render_template('system_settings.html', 
                          current_time=now,
                          instance_path=current_app.instance_path)

@bp.route('/set_time_offset', methods=['POST'])
def set_time_offset():
    """Set user time offset preference"""
    try:
        # Get the user's local time from form
        user_time_str = request.form.get('user_time')
        if not user_time_str:
            return jsonify({'success': False, 'message': 'No time provided'})
        
        # Parse the user's time
        user_time = datetime.fromisoformat(user_time_str.replace('T', ' '))
        
        # Get current system time
        system_time = datetime.now()
        
        # Calculate offset in minutes
        offset_minutes = int((user_time - system_time).total_seconds() / 60)
        
        # Update profile with new offset
        profile = profile_manager.get_profile()
        if 'preferences' not in profile:
            profile['preferences'] = {}
        profile['preferences']['time_offset_minutes'] = offset_minutes
        
        # Save the profile
        success = profile_manager.save_profile(profile)
        
        message = f"Time settings saved. Your local time is set to {user_time.strftime('%Y-%m-%d %H:%M:%S')}."
        return jsonify({'success': success, 'message': message, 'offset_minutes': offset_minutes})
    except Exception as e:
        logger.error(f"Error setting time offset: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f"Error: {str(e)}"})

@bp.route('/profile', methods=['GET', 'POST'])
def profile_settings():
    """Render and handle user profile settings."""
    if request.method == 'POST':
        # Build profile object from form data
        profile = {
            "business_name": request.form.get('business_name', ''),
            "address": {
                "street": request.form.get('street', ''),
                "city": request.form.get('city', ''),
                "postal_code": request.form.get('postal_code', ''),
                "country": request.form.get('country', 'DE')
            },
            "contact": {
                "email": request.form.get('email', ''),
                "phone": request.form.get('phone', '')
            },
            "tax_info": {
                "is_small_business": request.form.get('is_small_business') == 'true',
                "vat_id": request.form.get('vat_id', '')
            },
            "banking": {
                "account_holder": request.form.get('account_holder', ''),
                "iban": request.form.get('iban', ''),
                "bic": request.form.get('bic', '')
            }
        }
        
        # Preserve existing preferences
        current_profile = profile_manager.get_profile()
        if 'preferences' in current_profile:
            profile['preferences'] = current_profile['preferences']
        
        # Save the profile
        success = profile_manager.save_profile(profile)
        
        if success:
            return render_template('profile_settings.html', 
                                  profile=profile, 
                                  message="Profile saved successfully",
                                  message_type="success")
        else:
            return render_template('profile_settings.html', 
                                  profile=profile, 
                                  message="Error saving profile",
                                  message_type="error")
    
    # GET method - display profile form
    profile = profile_manager.get_profile()
    return render_template('profile_settings.html', profile=profile)

@bp.route('/timer_diagnostics')
@with_db
def timer_diagnostics(db):
    """Show timer diagnostic information"""
    active_timer = db.execute('''
        SELECT *, 
            (julianday(datetime('now')) - julianday(start_time)) * 24 as hours_utc,
            (julianday(datetime('now', 'localtime')) - julianday(start_time)) * 24 as hours_local,
            start_time
        FROM time_entry 
        WHERE end_time IS NULL
        ORDER BY id DESC LIMIT 1
    ''').fetchone()
    
    if not active_timer:
        return "No active timer"
    
    return f"""
    Timer ID: {active_timer['id']}<br>
    Start time: {active_timer['start_time']}<br>
    Hours (UTC): {active_timer['hours_utc']}<br>
    Hours (local): {active_timer['hours_local']}<br>
    """