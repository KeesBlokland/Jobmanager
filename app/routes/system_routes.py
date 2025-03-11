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
    

# Add to app/routes/system_routes.py

@bp.route('/profile', methods=['GET', 'POST'])
def profile_settings():
    """Render and handle user profile settings."""
    from ..utils.profile_utils import profile_manager
    
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