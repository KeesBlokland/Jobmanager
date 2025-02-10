-- Create a new table without VAT number
CREATE TABLE customer_new (
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

-- Copy data from old table to new table
INSERT INTO customer_new 
SELECT id, name, email, phone, street, city, postal_code, country, payment_terms, notes 
FROM customer;

-- Drop old table
DROP TABLE customer;

-- Rename new table to customer
ALTER TABLE customer_new RENAME TO customer;