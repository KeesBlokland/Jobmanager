// app/static/js/time_formatter.js

document.addEventListener('DOMContentLoaded', function() {
    // Format all time elements with data-time attribute
    formatTimeElements();
});

function formatTimeElements() {
    const timeElements = document.querySelectorAll('.format-time');
    
    timeElements.forEach(el => {
        const timestamp = el.getAttribute('data-time');
        const format = el.getAttribute('data-format') || 'datetime';
        
        if (!timestamp) return;
        
        try {
            const date = new Date(timestamp);
            
            // Check if date is valid
            if (isNaN(date.getTime())) {
                el.textContent = timestamp;
                return;
            }
            
            switch(format) {
                case 'date':
                    el.textContent = formatDate(date);
                    break;
                case 'date-short':
                    el.textContent = formatShortDate(date);
                    break;
                case 'time':
                    el.textContent = formatTime(date);
                    break;
                case 'datetime':
                    el.textContent = formatDateTime(date);
                    break;
                case 'full':
                    el.textContent = formatFullDateTime(date);
                    break;
                default:
                    el.textContent = formatDateTime(date);
            }
        } catch (e) {
            console.error('Error formatting date:', e);
            el.textContent = timestamp;
        }
    });
}

function formatDate(date) {
    // Format: dd Mmm yyyy (e.g., 15 Mar 2025)
    const day = date.getDate();
    const month = date.toLocaleString('en-US', { month: 'short' });
    const year = date.getFullYear();
    return `${day} ${month} ${year}`;
}

function formatShortDate(date) {
    // Format: dd Mmm (e.g., 15 Mar)
    const day = date.getDate();
    const month = date.toLocaleString('en-US', { month: 'short' });
    return `${day} ${month}`;
}

function formatTime(date) {
    // Format: HH:MM (e.g., 14:30)
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

function formatDateTime(date) {
    // Format: dd Mmm, HH:MM (e.g., 15 Mar, 14:30)
    return `${formatShortDate(date)}, ${formatTime(date)}`;
}

function formatFullDateTime(date) {
    // Format: dd Mmm yyyy, HH:MM (e.g., 15 Mar 2025, 14:30)
    return `${formatDate(date)}, ${formatTime(date)}`;
}

// Function to format duration in hours to HH:MM
function formatDuration(hours) {
    if (hours === null || hours === undefined) return "00:00";
    
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    
    return `${wholeHours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

// Calculate time difference between two timestamps
function calculateHours(startTime, endTime) {
    if (!startTime) return 0;
    
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    
    // Calculate difference in milliseconds
    const diffMs = end - start;
    
    // Convert to hours
    return diffMs / (1000 * 60 * 60);
}

// Update all time entries on the page (can be called periodically)
function updateAllTimers() {
    // Update active timers
    updateTimerDuration();
    
    // Re-format all time elements
    formatTimeElements();
}