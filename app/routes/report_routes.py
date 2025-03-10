# app/routes/report_routes.py
from flask import Blueprint, render_template, request, redirect, url_for
from ..db import with_db
from datetime import datetime, timedelta, date
import sqlite3
import logging

bp = Blueprint('report', __name__)
logger = logging.getLogger('jobmanager')

@bp.route('/weekly_summary')
@with_db
def weekly_summary(db):
    """Generate a weekly summary report of all jobs worked on"""
    try:
        # Get parameters from request
        selected_week = request.args.get('week', None)
        show_all = request.args.get('show_all', 'false').lower() == 'true'
        
        # Debug logging
        logger.info(f"Weekly summary request - selected_week: {selected_week}, show_all: {show_all}")
        
        # If no week is selected, use current week
        if not selected_week:
            today = date.today()
            # Get ISO week
            year, week_num, _ = today.isocalendar()
            selected_week = f"{year}-W{week_num:02d}"
            logger.info(f"No week selected, using current week: {selected_week}")

        # Get all available weeks for the dropdown
        try:
            # Use a simpler query that's less likely to fail
            logger.info("Fetching available weeks")
            db.execute("SELECT 1").fetchone()  # Test database connection
            
            available_weeks = []
            weeks_query = '''
                SELECT DISTINCT
                    date(start_time) as entry_date
                FROM time_entry
                ORDER BY entry_date DESC
            '''
            
            # Process each date and convert to ISO week format
            dates = db.execute(weeks_query).fetchall()
            logger.info(f"Found {len(dates)} distinct dates with time entries")
            
            week_set = set()  # Use a set to avoid duplicates
            for date_row in dates:
                try:
                    entry_date = datetime.fromisoformat(date_row['entry_date']).date()
                    year, week, _ = entry_date.isocalendar()
                    week_str = f"{year}-W{week:02d}"
                    week_set.add(week_str)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing date {date_row['entry_date']}: {str(e)}")
                    continue
            
            # Convert set to sorted list
            available_weeks = [{'week_str': week} for week in sorted(week_set, reverse=True)]
            logger.info(f"Processed {len(available_weeks)} unique weeks")
            
        except Exception as e:
            logger.error(f"Error fetching available weeks: {str(e)}", exc_info=True)
            available_weeks = []
        
        # Make sure current week is in the list
        today = date.today()
        year, week_num, _ = today.isocalendar()
        current_week = f"{year}-W{week_num:02d}"
        
        # Check if current week is in available weeks
        current_week_exists = False
        for week in available_weeks:
            if week['week_str'] == current_week:
                current_week_exists = True
                break
                
        # Add current week if not in list
        if not current_week_exists:
            available_weeks = [{'week_str': current_week}] + list(available_weeks)
        
        # If a dropdown change was made (not a toggle button click)
        if request.args.get('week') and 'show_all' not in request.args:
            # Force single week view when selecting from dropdown
            show_all = False
            logger.info(f"Week selected from dropdown: {selected_week}, setting show_all=False")
        
        logger.info(f"Final view settings - selected_week: {selected_week}, show_all: {show_all}")
        
        # Get all weeks data if show_all is true
        if show_all:
            try:
                # Get summary data for all weeks
                weekly_data = db.execute('''
                    WITH time_summary AS (
                        SELECT 
                            job_id,
                            date(start_time) as entry_date,
                            SUM((julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24) AS day_hours
                        FROM time_entry
                        GROUP BY job_id, entry_date
                    )
                    SELECT 
                        ts.job_id,
                        ts.entry_date,
                        job.description AS job_description,
                        customer.name AS customer_name,
                        job.base_rate,
                        ts.day_hours AS total_hours
                    FROM time_summary ts
                    JOIN job ON ts.job_id = job.id
                    JOIN customer ON job.customer_id = customer.id
                    ORDER BY ts.entry_date DESC, job.id
                ''').fetchall()
                
                # Group by week
                weeks_summary = {}
                
                for entry in weekly_data:
                    try:
                        # Convert date to ISO week
                        entry_date = datetime.fromisoformat(entry['entry_date']).date()
                        year, week, _ = entry_date.isocalendar()
                        week_str = f"{year}-W{week:02d}"
                        
                        if week_str not in weeks_summary:
                            weeks_summary[week_str] = {
                                'week_start': entry['entry_date'],
                                'job_totals': {},
                                'total_hours': 0,
                                'total_amount': 0
                            }
                        
                        # Create job key
                        job_key = f"{entry['job_id']}-{entry['job_description']}-{entry['customer_name']}"
                        
                        # Ensure total_hours is not None
                        total_hours = entry['total_hours'] if entry['total_hours'] is not None else 0
                        
                        # Calculate amount only if base_rate is not None
                        amount = total_hours * (entry['base_rate'] or 0)
                        
                        # Add or update job data
                        if job_key not in weeks_summary[week_str]['job_totals']:
                            weeks_summary[week_str]['job_totals'][job_key] = {
                                'job_id': entry['job_id'],
                                'description': entry['job_description'],
                                'customer': entry['customer_name'],
                                'hours': total_hours,
                                'amount': amount
                            }
                        else:
                            # Add to existing totals
                            weeks_summary[week_str]['job_totals'][job_key]['hours'] += total_hours
                            weeks_summary[week_str]['job_totals'][job_key]['amount'] += amount
                        
                        # Update week totals
                        weeks_summary[week_str]['total_hours'] += total_hours
                        weeks_summary[week_str]['total_amount'] += amount
                    except Exception as e:
                        logger.error(f"Error processing entry for week summary: {str(e)}")
                        continue
                
                # Sort weeks by most recent first
                sorted_weeks = sorted(weeks_summary.items(), key=lambda x: x[0], reverse=True)
                logger.info(f"Generated summary for {len(sorted_weeks)} weeks")
                
                return render_template('weekly_summary.html',
                                    selected_week=selected_week,
                                    available_weeks=available_weeks,
                                    show_all=show_all,
                                    all_weeks=sorted_weeks)
            except Exception as e:
                logger.error(f"Error generating all weeks data: {str(e)}", exc_info=True)
                return render_template('weekly_summary.html',
                                      selected_week=selected_week,
                                      available_weeks=available_weeks,
                                      show_all=False,
                                      error=f"Could not generate weekly summary: {str(e)}")
        
        # Process selected week
        try:
            if '-W' in selected_week:
                year, week_num = selected_week.split('-W')
                year = int(year)
                week_num = int(week_num)
                
                # Calculate start and end dates of the selected week
                start_date = date.fromisocalendar(year, week_num, 1)  # Monday
                end_date = date.fromisocalendar(year, week_num, 7)    # Sunday
            else:
                # Default to current week if format is invalid
                today = date.today()
                year, week_num, _ = today.isocalendar()
                start_date = date.fromisocalendar(year, week_num, 1)  # Monday
                end_date = date.fromisocalendar(year, week_num, 7)    # Sunday
                selected_week = f"{year}-W{week_num:02d}"
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing week format: {str(e)}")
            # Handle invalid week format
            return redirect(url_for('report.weekly_summary'))
        
        # Format for SQLite date comparison
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Get all time entries for the selected week
        try:
            time_entries = db.execute('''
                SELECT 
                    time_entry.*,
                    job.description AS job_description,
                    job.base_rate,
                    customer.name AS customer_name,
                    (julianday(COALESCE(end_time, datetime('now'))) - julianday(start_time)) * 24 AS hours
                FROM time_entry
                JOIN job ON time_entry.job_id = job.id
                JOIN customer ON job.customer_id = customer.id
                WHERE date(start_time) >= ? AND date(start_time) <= ?
                ORDER BY start_time
            ''', (start_date_str, end_date_str)).fetchall()
            
            logger.info(f"Found {len(time_entries)} time entries for week {selected_week}")
        except Exception as e:
            logger.error(f"Error fetching time entries: {str(e)}")
            time_entries = []
        
        # Group by day and job
        days = {}
        job_totals = {}
        week_total_hours = 0
        week_total_amount = 0
        
        for entry in time_entries:
            try:
                # Skip any entries with NULL hours
                if entry['hours'] is None:
                    continue
                    
                entry_date = datetime.fromisoformat(entry['start_time']).date()
                day_str = entry_date.strftime('%Y-%m-%d')
                
                # Create a key for this job
                job_key = f"{entry['job_id']}-{entry['job_description']}-{entry['customer_name']}"
                
                # Initialize day if not exists
                if day_str not in days:
                    days[day_str] = {
                        'date': entry_date,
                        'day_name': entry_date.strftime('%A'),
                        'jobs': {},
                        'total_hours': 0,
                        'total_amount': 0
                    }
                
                # Initialize job for this day if not exists
                if job_key not in days[day_str]['jobs']:
                    days[day_str]['jobs'][job_key] = {
                        'job_id': entry['job_id'],
                        'description': entry['job_description'],
                        'customer': entry['customer_name'],
                        'entries': [],
                        'hours': 0,
                        'amount': 0
                    }
                
                # Ensure we're working with a number, not None
                hours = entry['hours'] if entry['hours'] is not None else 0
                
                # Add entry to the job for this day
                days[day_str]['jobs'][job_key]['entries'].append(entry)
                days[day_str]['jobs'][job_key]['hours'] += hours
                
                # Calculate amount if base_rate exists
                amount = 0
                if entry['base_rate']:
                    amount = hours * entry['base_rate']
                    days[day_str]['jobs'][job_key]['amount'] += amount
                
                # Update day totals
                days[day_str]['total_hours'] += hours
                days[day_str]['total_amount'] += amount
                
                # Update week totals
                week_total_hours += hours
                week_total_amount += amount
                
                # Update job totals for the week
                if job_key not in job_totals:
                    job_totals[job_key] = {
                        'job_id': entry['job_id'],
                        'description': entry['job_description'],
                        'customer': entry['customer_name'],
                        'hours': 0,
                        'amount': 0
                    }
                job_totals[job_key]['hours'] += hours
                job_totals[job_key]['amount'] += amount
            except Exception as e:
                logger.error(f"Error processing entry {entry['id']}: {str(e)}")
                continue
        
        # Sort days chronologically
        sorted_days = sorted(days.items())
        
        return render_template('weekly_summary.html',
                              selected_week=selected_week,
                              available_weeks=available_weeks,
                              show_all=show_all,
                              days=sorted_days,
                              job_totals=job_totals,
                              week_total_hours=week_total_hours,
                              week_total_amount=week_total_amount,
                              start_date=start_date,
                              end_date=end_date)
    except Exception as e:
        logger.error(f"Unhandled exception in weekly_summary: {str(e)}", exc_info=True)
        return render_template('500.html', error=str(e))