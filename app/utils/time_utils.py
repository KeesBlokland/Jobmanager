# app/utils/time_utils.py
from datetime import datetime, timezone
import logging

logger = logging.getLogger('jobmanager')

def get_current_time():
    """Get current time as ISO format string with UTC timezone."""
    # Always include timezone information for consistent calculations
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def format_time(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """Format timestamp as string using specified format."""
    if timestamp is None:
        return ""
    
    try:
        # Parse timestamp with appropriate timezone handling
        if isinstance(timestamp, str):
            if 'Z' in timestamp:
                # Handle UTC marker
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif '+' in timestamp or '-' in timestamp and 'T' in timestamp:
                # Handle ISO format with timezone
                dt = datetime.fromisoformat(timestamp)
            else:
                # Handle without timezone (assume UTC)
                dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        else:
            # If timestamp is a number (Unix timestamp), convert it
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        return dt.strftime(format_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting time: {e}")
        return "Invalid time"

def format_duration(seconds):
    """Format seconds duration as HH:MM:SS."""
    if seconds is None:
        return "00:00:00"
    
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def parse_time(time_str, format_str='%Y-%m-%d %H:%M:%S'):
    """Parse time string to ISO format string with UTC timezone."""
    if not time_str:
        return None
    
    try:
        dt = datetime.strptime(time_str, format_str)
        # Always include timezone for consistency
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError as e:
        logger.error(f"Error parsing time: {e}")
        return None

def get_time_difference_seconds(start_time_str, end_time_str=None):
    """Calculate the difference in seconds between two ISO format times."""
    if not start_time_str:
        return 0
    
    try:
        # Parse start time with timezone handling
        if isinstance(start_time_str, str):
            if 'Z' in start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            elif '+' in start_time_str or '-' in start_time_str and 'T' in start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
            else:
                start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        else:
            # Handle non-string input (like datetime objects)
            start_time = start_time_str
            if not start_time.tzinfo:
                start_time = start_time.replace(tzinfo=timezone.utc)
        
        # Get end time or use current UTC time
        if end_time_str:
            if isinstance(end_time_str, str):
                if 'Z' in end_time_str:
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                elif '+' in end_time_str or '-' in end_time_str and 'T' in end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                else:
                    end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
            else:
                # Handle non-string input
                end_time = end_time_str
                if not end_time.tzinfo:
                    end_time = end_time.replace(tzinfo=timezone.utc)
        else:
            end_time = datetime.now(timezone.utc)
        
        # Return the raw time difference including negative values
        diff_seconds = (end_time - start_time).total_seconds()
        return diff_seconds
        
    except Exception as e:
        logger.error(f"Error calculating time difference: {e}")
        return 0

def iso_to_datetime(iso_str):
    """Convert an ISO format string to a datetime object with timezone."""
    if not iso_str:
        return None
        
    try:
        if 'Z' in iso_str:
            return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        elif '+' in iso_str or '-' in iso_str and 'T' in iso_str:
            return datetime.fromisoformat(iso_str)
        else:
            return datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
    except ValueError as e:
        logger.error(f"Error parsing ISO datetime: {e}")
        return None
def format_display_time(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """Format time with user's timezone offset applied."""
    dt = iso_to_datetime(timestamp) if isinstance(timestamp, str) else timestamp
    if not dt:
        return ""
        
    try:
        # Apply user's time offset if needed
        offset_minutes = profile_manager.get_time_offset_minutes()
        if offset_minutes and dt.tzinfo:  # Only apply if timestamp has timezone info
            from datetime import timedelta
            dt = dt + timedelta(minutes=offset_minutes)
            
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting display time: {e}")
        return "Invalid time"