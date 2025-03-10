# app/routes/system_routes.py
from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
import pytz
import os
import subprocess
import logging
from ..db import with_db

bp = Blueprint('system', __name__)
logger = logging.getLogger('jobmanager')

@bp.route('/settings')
@with_db
def settings(db):
    """Render system settings page"""
    # Get current system time info
    now = datetime.now()
    
    # Get time zones with common ones first
    common_timezones = ['Europe/Berlin', 'Europe/Amsterdam', 'Europe/London', 'America/New_York', 'America/Los_Angeles']
    all_timezones = sorted([tz for tz in pytz.all_timezones if tz not in common_timezones])
    timezones = common_timezones + all_timezones
    
    # Get current timezone
    current_timezone = "Europe/Berlin"  # Default
    try:
        # Try to read timezone from system
        with open('/etc/timezone', 'r') as f:
            current_timezone = f.read().strip()
    except Exception as e:
        logger.warning(f"Could not read system timezone: {str(e)}")
    
    return render_template('system_settings.html', 
                          current_time=now,
                          timezones=timezones,
                          current_timezone=current_timezone,
                          instance_path=current_app.instance_path)

@bp.route('/set_timezone', methods=['POST'])
def set_timezone():
    """Set system timezone"""
    try:
        timezone = request.form.get('timezone')
        
        if not timezone or timezone not in pytz.all_timezones:
            return jsonify({'success': False, 'message': 'Invalid timezone'})
            
        # Use timedatectl to set timezone
        result = subprocess.run(['sudo', 'timedatectl', 'set-timezone', timezone], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to set timezone: {result.stderr}")
            return jsonify({
                'success': False, 
                'message': f"Failed to set timezone. Error: {result.stderr}"
            })
            
        logger.info(f"System timezone set to {timezone}")
        return jsonify({'success': True, 'message': f"Timezone set to {timezone}"})
        
    except Exception as e:
        logger.error(f"Error setting timezone: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/sync_ntp', methods=['POST'])
def sync_ntp():
    """Sync time with NTP servers"""
    try:
        # Use systemctl to restart timesyncd service
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'systemd-timesyncd'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to sync with NTP: {result.stderr}")
            return jsonify({
                'success': False, 
                'message': "Failed to sync with NTP servers."
            })
        
        logger.info("Time synchronized with NTP servers")
        return jsonify({'success': True, 'message': "Time synchronized with NTP servers"})
        
    except Exception as e:
        logger.error(f"Error syncing with NTP: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})