# app/utils/jinja_filters.py
from flask import Flask
from datetime import datetime, timezone, timedelta
from .profile_utils import profile_manager
from .time_utils import format_time

def register_jinja_filters(app):
    """Register custom Jinja2 filters related to time handling."""
    
    @app.template_filter('format_datetime')
    def format_datetime_filter(value, format='%Y-%m-%d %H:%M'):
        """Format datetime with user's time offset applied."""
        if not value:
            return ""
            
        try:
            # Parse timestamp
            if isinstance(value, str):
                if 'Z' in value:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                elif '+' in value or '-' in value and 'T' in value:
                    dt = datetime.fromisoformat(value)
                else:
                    dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromtimestamp(value, tz=timezone.utc)
                
            # Apply user offset
            offset_minutes = profile_manager.get_time_offset_minutes()
            adjusted_dt = dt + timedelta(minutes=offset_minutes)
            return adjusted_dt.strftime(format)
        except Exception as e:
            return format_time(value, format)
    
    @app.template_filter('format_time')
    def format_time_filter(value, format='%H:%M'):
        """Format time portion with user's time offset applied."""
        if not value:
            return ""
        return format_datetime_filter(value, format)
    
    @app.template_filter('format_date')
    def format_date_filter(value, format='%Y-%m-%d'):
        """Format date portion with user's time offset applied."""
        if not value:
            return ""
        return format_datetime_filter(value, format)
    
    @app.template_filter('format_duration')
    def format_duration_filter(hours):
        """Format hours as HH:MM."""
        if hours is None:
            return "00:00"
        
        hours_int = int(hours)
        minutes = int((hours - hours_int) * 60)
        return f"{hours_int:02d}:{minutes:02d}"
    
    @app.context_processor
    def inject_time_helpers():
        """Inject time helper functions into template context."""
        def get_adjusted_now():
            """Get current time with user's offset applied."""
            now = datetime.now(timezone.utc)
            offset_minutes = profile_manager.get_time_offset_minutes()
            return now + timedelta(minutes=offset_minutes)
            
        return {
            'adjusted_now': get_adjusted_now
        }