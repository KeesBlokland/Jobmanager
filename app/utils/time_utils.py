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
        if 'Z' in start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        elif '+' in start_time_str or '-' in start_time_str and 'T' in start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        else:
            start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
        
        # Get end time or use current UTC time
        if end_time_str:
            if 'Z' in end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            elif '+' in end_time_str or '-' in end_time_str and 'T' in end_time_str:
                end_time = datetime.fromisoformat(end_time_str)
            else:
                end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
        else:
            end_time = datetime.now(timezone.utc)
        
        # Direct difference calculation without timezone adjustments
        return (end_time - start_time).total_seconds()
    except Exception as e:
        logger.error(f"Error calculating time difference: {e}")
        return 0