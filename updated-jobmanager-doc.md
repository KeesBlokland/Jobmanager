# Job Manager System Design

## Core Requirements
- Must run entirely offline/local
- Mobile-friendly interface
- Lightweight enough for Raspberry Pi deployment
- No external CDNs or dependencies
- Daily local database backups
- Complete file management (no partial updates)
- Practical implementation focus
- Workshop-friendly interface

## Core Philosophy
- Interactive list-based interface is the heart of the system
- Time tracking should be seamless and automatic
- Smart behaviors reduce administrative overhead
- Design for workshop environment
- Future-proof for billing and automation
- Support for work breaks via pause function
- Comprehensive search across all data

## Main Entities

### Customer
```
- ID
- Name
- Email
- Phone
- Address
  - Street
  - City
  - Postal Code
  - Country
- VAT/Tax Number
- Payment Terms
- Notes
```

### Job
```
- ID
- Customer ID
- Description
- Status (Active/Pending/Completed)
- Creation Date
- Deadline
- Rate Information
  - Base Rate
  - Custom Rate (if different)
- Estimated Hours
- Total Hours Accumulated
- Last Active
```

### TimeEntry
```
- ID
- Job ID
- Start Time
- End Time
- Entry Type (auto/manual/adjusted)
- Notes
- Materials Used
- Adjusted By (if corrected)
- Adjustment Reason
- Location (future: for RFID integration)
- Break Duration
```

## User Interface Design

### Main Screen Layout
```
+----------------------------------------+
|  Search/Filter Bar                      |
+----------------------------------------+
|  Timer Controls [▶️ ⏸️ ⏹️]              |
+----------------------------------------+
|  [Active Jobs]                         |
|  - Customer | Job | Timer | Hours | €  |
|    ↳ Expanded details when clicked     |
|  - Next job...                         |
+----------------------------------------+
|  [Pending Jobs]                        |
|  - Same format                         |
+----------------------------------------+
|  [Recent Completed]                    |
|  - Same format                         |
+----------------------------------------+
|  Quick Actions Bar                     |
+----------------------------------------+
```

### Mobile Considerations
- Touch-friendly large tap targets
- Responsive design (no horizontal scrolling)
- Simplified views for small screens
- Bottom navigation for thumb reach
- Swipe gestures for common actions

### Smart Behaviors
- Drag job to top = Start timer
- Auto-stop previous job when new one started
- Click to expand/collapse details
- Double-click for quick edits
- Color coding for status/alerts
- Break tracking with pause button
- Global search across all fields

### Expanded Job View
```
+----------------+------------------+---------------+
| Customer Info  | Time Entries    | Running       |
| Job Details   | Progress Notes  | Totals        |
| Rate Info     | Materials Used  | Costs         |
+----------------+------------------+---------------+
```

## Time Tracking System

### Automatic Tracking
- Start on job activation (drag to top)
- Stop on new job start
- Manual pause for breaks
- Batch similar entries

### Manual Adjustments
- Split time entries
- Merge entries
- Backdate entries
- Bulk time entry
- Corrections with audit trail
- Break time tracking

### Time Views
- Real-time active job timer
- Daily totals per job
- Weekly summaries
- Monthly reports
- Customer statements

## Data Management

### Backup System
- Daily automatic local backups
- Rolling 7-day backup retention
- Manual backup option
- Simple restoration process
- Backup verification

### Search Functionality
- Global search across all fields
- Search in:
  - Job descriptions
  - Customer details
  - Notes
  - Materials
  - Time entries
- Real-time search results
- Search history

## Implementation Notes

### Database Considerations
- SQLite for simplicity and portability
- Regular VACUUM operations
- Efficient indexing for search
- Minimal writes for Pi storage
- Transaction safety

### UI Guidelines
- Touch-friendly interface
- Clear visual feedback
- Minimal click operations
- Workshop-friendly design
- Error prevention over error handling
- Offline-first architecture
- No external resources

### Performance Considerations
- Lazy loading for long lists
- Minimal DOM updates
- Efficient search indexing
- Optimized for Pi resources
- Background backup process
