# app/utils/date_helper.py
from datetime import date, datetime
import calendar

def iso_week_number(year, month, day):
    """Calculate the ISO week number for a given date"""
    d = date(year, month, day)
    return d.isocalendar()[1]

def iso_week_year(year, month, day):
    """Calculate the ISO week year for a given date (may differ from calendar year at year boundaries)"""
    d = date(year, month, day)
    return d.isocalendar()[0]

def format_week(week_data):
    """Format a week string in format 'YYYY-WNN' to 'Week NN, YYYY'"""
    try:
        parts = week_data.split('-W')
        year = parts[0]
        week = parts[1]
        # Remove leading zeros for display
        week_num = int(week)
        return f"Week {week_num}, {year}"
    except (ValueError, IndexError):
        return week_data

def iso_date_to_datetime(date_str):
    """Convert ISO date string (YYYY-MM-DD) to datetime object"""
    try:
        year = int(date_str[0:4])
        month = int(date_str[5:7])
        day = int(date_str[8:10])
        return datetime(year, month, day)
    except (ValueError, IndexError):
        return datetime.now()

def add_template_helpers(app):
    """Add custom template helpers to the Flask application"""
    
    @app.template_filter('iso_week')
    def iso_week_filter(date_str):
        """Filter to extract the ISO week number from a date string in format YYYY-MM-DD"""
        try:
            year = int(date_str[0:4])
            month = int(date_str[5:7])
            day = int(date_str[8:10])
            return iso_week_number(year, month, day)
        except (ValueError, IndexError):
            return 0
            
    @app.template_filter('iso_week_year')
    def iso_week_year_filter(date_str):
        """Filter to extract the ISO week year from a date string in format YYYY-MM-DD"""
        try:
            year = int(date_str[0:4])
            month = int(date_str[5:7])
            day = int(date_str[8:10])
            return iso_week_year(year, month, day)
        except (ValueError, IndexError):
            return 0

    @app.template_filter('format_week')
    def format_week_filter(week_data):
        """Filter to format week string"""
        return format_week(week_data)
    
    @app.template_filter('iso_date_to_datetime')
    def iso_date_to_datetime_filter(iso_str):
        if not iso_str:
            return None
        
        try:
            if 'Z' in iso_str:
                return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            elif '+' in iso_str or '-' in iso_str and 'T' in iso_str:
                return datetime.fromisoformat(iso_str)
            else:
                return datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    
    @app.template_filter('timestamp_to_datetime')
    def timestamp_to_datetime(timestamp):
        """Convert Unix timestamp to datetime object"""
        if isinstance(timestamp, (int, float)) or (isinstance(timestamp, str) and timestamp.isdigit()):
            timestamp = int(timestamp)
            return datetime.fromtimestamp(timestamp)
        return datetime.now()  # Fallback
    
    # Add a 'now' function for use in templates
    app.jinja_env.globals.update(now=datetime.now)