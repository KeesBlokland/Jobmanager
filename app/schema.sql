-- app/schema.sql
CREATE TABLE IF NOT EXISTS customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    street TEXT,
    city TEXT,
    postal_code TEXT,
    country TEXT,
    payment_terms TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    creation_date TEXT NOT NULL,
    deadline TEXT,
    base_rate REAL,
    custom_rate REAL,
    estimated_hours REAL,
    total_hours REAL DEFAULT 0,
    last_active TEXT,
    FOREIGN KEY (customer_id) REFERENCES customer (id)
);

CREATE TABLE IF NOT EXISTS time_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    entry_type TEXT NOT NULL,
    notes TEXT,
    materials_used TEXT,
    adjusted_by TEXT,
    adjustment_reason TEXT,
    location TEXT,
    break_duration INTEGER DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES job (id)
);

CREATE TABLE IF NOT EXISTS job_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES job (id)
);

CREATE TABLE IF NOT EXISTS job_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    material TEXT NOT NULL, 
    quantity REAL,
    unit TEXT,
    timestamp TEXT NOT NULL,
    price REAL DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES job (id)
);

-- ALTER TABLE job ADD COLUMN invoice_number TEXT;
-- ALTER TABLE job_material ADD COLUMN price REAL DEFAULT 0;

-- Add is_template column to job table
-- ALTER TABLE job ADD COLUMN is_template INTEGER DEFAULT 0;
-- ALTER TABLE job ADD COLUMN template_name TEXT;

-- Create table for template materials
CREATE TABLE IF NOT EXISTS template_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    material TEXT NOT NULL,
    quantity REAL DEFAULT 1,
    price REAL DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES job (id)
);

CREATE TABLE IF NOT EXISTS job_image (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    description TEXT,
    timestamp TEXT NOT NULL,
    location TEXT,  -- Optional GPS coordinates
    tags TEXT,      -- Comma-separated tags
    FOREIGN KEY (job_id) REFERENCES job (id)
);

