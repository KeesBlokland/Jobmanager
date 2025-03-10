# app/utils/time_utils.py
import time
from datetime import datetime, timezone

def get_current_time():
    """Get current time as ISO format string."""
    return datetime.now().isoformat()

def format_time(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """Format timestamp as string using specified format.
    
    Handles both ISO format strings and Unix timestamps.
    """
    if timestamp is None:
        return ""
    
    try:
        # If timestamp is already a string (ISO format), parse it
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp)
        # If timestamp is a number (Unix timestamp), convert it
        else:
            dt = datetime.fromtimestamp(timestamp)
        
        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return "Invalid time"

def format_duration(seconds):
    """Format duration in seconds to human-readable format."""
    if seconds is None or seconds < 0:
        return "00:00:00"
    
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def parse_time(time_str, format_str='%Y-%m-%d %H:%M:%S'):
    """Parse time string to ISO format string."""
    if not time_str:
        return None
    
    try:
        dt = datetime.strptime(time_str, format_str)
        return dt.isoformat()
    except ValueError:
        return None