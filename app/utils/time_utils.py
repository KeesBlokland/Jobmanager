# app/utils/time_utils.py
from datetime import datetime, timezone

def get_current_time():
    """Get current time as UTC ISO format string."""
    # Force UTC and include 'Z' suffix to mark as UTC
    return datetime.now(timezone.utc).isoformat()


def format_time(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """Format timestamp as string using specified format.
        Handles both ISO format strings and Unix timestamps.
    Args:
        timestamp: ISO format string or Unix timestamp
        format_str: Format string for output
    Returns:
        str: Formatted time string
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
    """Format duration in seconds to human-readable format.
    Args:
        seconds: Duration in seconds
    Returns:
        str: Formatted duration as "HH:MM:SS"
    """
    if seconds is None or seconds < 0:
        return "00:00:00"
    
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def parse_time(time_str, format_str='%Y-%m-%d %H:%M:%S'):
    """Parse time string to ISO format string.
    
    Args:
        time_str: Time string to parse
        format_str: Format of the input string
        
    Returns:
        str: ISO format string or None if parsing fails
    """
    if not time_str:
        return None
    
    try:
        dt = datetime.strptime(time_str, format_str)
        return dt.isoformat(timespec='seconds')
    except ValueError:
        return None

def iso_to_datetime(iso_str):
    """Convert ISO format string to datetime object.
    
    Args:
        iso_str: ISO format datetime string
        
    Returns:
        datetime: Parsed datetime object
    """
    if not iso_str:
        return None
    
    try:
        return datetime.fromisoformat(iso_str)
    except ValueError:
        return None

def get_time_difference_seconds(start_time_str, end_time_str=None):
    """Calculate the difference in seconds between two ISO format times.
    
    If end_time_str is not provided, uses current time.
    
    Args:
        start_time_str: Start time as ISO format string
        end_time_str: End time as ISO format string, or None for current time
        
    Returns:
        float: Difference in seconds
    """
    if not start_time_str:
        return 0
    
    try:
        start_time = iso_to_datetime(start_time_str)
        
        if end_time_str:
            end_time = iso_to_datetime(end_time_str)
        else:
            end_time = datetime.now()
            
        # Ensure both datetimes are naive (no timezone) for consistent comparison
        if start_time.tzinfo:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo:
            end_time = end_time.replace(tzinfo=None)
            
        return (end_time - start_time).total_seconds()
    except (ValueError, TypeError):
        return 0