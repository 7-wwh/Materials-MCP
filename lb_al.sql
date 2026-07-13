-- SQL schema and data for LB Aluminium

-- Table: companies
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    founded_year INTEGER,
    headquarters TEXT,
    website TEXT,
    logo_url TEXT
);

-- Insert LB Aluminium
INSERT INTO companies (name, founded_year, headquarters, website, logo_url) 
VALUES ('LB Aluminium Berhad', 1985, 'Malaysia', 'https://www.lbalum.com/', 'https://www.lbalum.com/sites/default/files/lb_logo_4.png');

-- Table: subsidiaries
CREATE TABLE IF NOT EXISTS subsidiaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    name TEXT NOT NULL,
    address TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO subsidiaries (company_id, name, address) VALUES
(1, 'Façade Performance Lab Sdn Bhd', 'Lot. PT20470, Jalan Perindustrian Mahkota 3/F, Taman Perindustrian Mahkota, 43700 Beranang, Semenyih, Selangor'),
(1, 'SEMS Sdn Bhd', 'Lot 2.14, Jalan Perindutrian Mahkota 5, Kawasan Perindustrian Mahkota, 43700 Beranang, Semenyih, Selangor'),
(1, 'LB Aluminium (Singapore) Pte. Ltd.', 'No.11, Kaki Bukit Road I #03-07 EunosTechnolink Singapore 415939'),
(1, 'ALBE Marketing Sdn Bhd', NULL),
(1, 'ALBE Metal Sdn Bhd', NULL);

-- Table: facilities
CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    facility_name TEXT,
    address TEXT,
    phone TEXT,
    fax TEXT,
    email TEXT,
    size_acres REAL,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO facilities (company_id, facility_name, address, phone, fax, email, size_acres) VALUES
(1, 'Head Office & Factory', 'Lot 11, Jalan Perusahaan 1, Kawasan Perusahaan Beranang, 43700 Beranang, Semenyih, Selangor Darul Ehsan, Malaysia', '+603-8725 8822', '+603-8725 8828 (General); +603-8725 8866 (Export); +603-8725 8920 (Export)', 'enquiry@lbalum.com.my', 36),
(1, 'Central Sales Office', NULL, '+603-8725 8833; +603-8725 8886; +603-8725 8826', NULL, NULL, NULL),
(1, 'Factory', 'Kuching, Sarawak', NULL, NULL, NULL, 4);

-- Table: products
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    product_name TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO products (company_id, product_name) VALUES
(1, 'Aluminium Extrusion'),
(1, 'Aluminium Sheets / Coil'),
(1, 'Albe Tee Ceiling Suspension System'),
(1, 'Fitting & Accessories');

-- Table: services
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    service_name TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO services (company_id, service_name) VALUES
(1, 'Die Shop'),
(1, 'Extrusion Presses'),
(1, 'Anodising'),
(1, 'Powder Coating and PVDF'),
(1, 'Engineering'),
(1, 'Test Rigs');

-- Table: core_values
CREATE TABLE IF NOT EXISTS core_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    value_name TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO core_values (company_id, value_name) VALUES
(1, 'Continuous innovation'),
(1, 'Uncompromising quality control'),
(1, 'Prompt service'),
(1, 'Eco-sustainability'),
(1, 'Professionalism');

-- Table: industries
CREATE TABLE IF NOT EXISTS industries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    industry_name TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO industries (company_id, industry_name) VALUES
(1, 'Architecture & Building Construction'),
(1, 'Electronic & Electrical Components'),
(1, 'Furniture & Interior Decoration'),
(1, 'Formwork'),
(1, 'Transportation & Automotive'),
(1, 'Marine'),
(1, 'Solar'),
(1, 'Conveyor & Automation'),
(1, 'Bazaar'),
(1, 'Miscellaneous');

-- Table: markets
CREATE TABLE IF NOT EXISTS markets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    market_name TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

INSERT INTO markets (company_id, market_name) VALUES
(1, 'Malaysia (Local)'),
(1, 'Europe'),
(1, 'North America'),
(1, 'Oceania'),
(1, 'Asia');
