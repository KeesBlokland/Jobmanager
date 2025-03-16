# app/utils/jinja_filters.py
from flask import Flask, current_app
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger('jobmanager')

def register_jinja_filters(app):
    """Register custom Jinja2 filters related to time handling."""
    
    @app.template_filter('format_datetime')
    def format_datetime_filter(value, format='%Y-%m-%d %H:%M'):
        """Format datetime with user's time offset applied."""
        if not value:
            return ""
            
        try:
            logger.info(f"format_datetime input: {value}, format: {format}")
            
            # Parse timestamp
            if isinstance(value, str):
                if 'Z' in value:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    logger.info(f"Parsed Z timestamp: {dt}")
                elif '+' in value or '-' in value and 'T' in value:
                    dt = datetime.fromisoformat(value)
                    logger.info(f"Parsed ISO timestamp with TZ: {dt}")
                else:
                    dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
                    logger.info(f"Parsed timestamp without TZ: {dt}")
            else:
                dt = datetime.fromtimestamp(value, tz=timezone.utc)
                logger.info(f"Parsed non-string timestamp: {dt}")
                
            # Get offset directly from profile_manager to avoid circular import
            from app.utils.profile_utils import profile_manager
            offset_minutes = profile_manager.get_time_offset_minutes()
            logger.info(f"User time offset: {offset_minutes} minutes")
            
            adjusted_dt = dt + timedelta(minutes=offset_minutes)
            logger.info(f"Adjusted timestamp: {adjusted_dt}")
            
            result = adjusted_dt.strftime(format)
            logger.info(f"Final formatted result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error formatting datetime: {str(e)}", exc_info=True)
            # Fall back to direct formatting without timezone handling
            try:
                if isinstance(value, str):
                    if 'T' in value:
                        # Remove timezone info for direct formatting
                        value = value.split('T')[0] + 'T' + value.split('T')[1].split('+')[0].split('Z')[0]
                    return datetime.fromisoformat(value).strftime(format)
                else:
                    return datetime.fromtimestamp(value).strftime(format)
            except:
                return value
    
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
            # Import on demand to avoid circular import
            from app.utils.profile_utils import profile_manager
            offset_minutes = profile_manager.get_time_offset_minutes()
            return now + timedelta(minutes=offset_minutes)
            
        return {
            'adjusted_now': get_adjusted_now
        }