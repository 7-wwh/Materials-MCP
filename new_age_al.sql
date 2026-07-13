-- Improved Database Schema for New Age Aluminium

-- 1. Categories Table
CREATE TABLE categories (
    category_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- 2. Products Table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    category_id VARCHAR(50),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    url VARCHAR(500),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 3. Services Table
CREATE TABLE services (
    service_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id VARCHAR(50),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 4. Product Attributes Table
CREATE TABLE product_attributes (
    attribute_id SERIAL PRIMARY KEY,
    product_id INTEGER,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value VARCHAR(255) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- 5. Company Info Table
CREATE TABLE company_info (
    info_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    address TEXT,
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100)
);

INSERT INTO company_info (contact_person, phone, email, company_name, address) VALUES
('Sam Loh', '603-78591320', 'sales@newagealuminium.com', 'NEW AGE ALUMINIUM INDUSTRIES SDN BHD', 'Lot 1, No. 160-B Subang New Village, Jalan TUDM, 40150 Shah Alam, Selangor Malaysia');

-- --- INITIAL DATA POPULATION ---

-- Insert Categories
INSERT INTO categories (category_id, name, description) VALUES
('025158f7-dc11-46a0-ae25-d43c46deb188', 'Common Aluminium Profiles', 'Standard aluminium profiles for various applications.'),
('94320a9b-0265-40e0-96f2-776425a0aa79', 'Customized Aluminium Profiles', 'Aluminium profiles designed according to customer specifications.'),
('bb78f1f1-4111-4583-a9ab-5951f7cdeebf', 'Fabrication Solutions', 'Value-added fabrication services for aluminium products.'),
('34f845ca-4f71-472c-ab0d-5a5b3a809973', 'Surface Treatment', 'Surface finishing services to enhance aesthetics and durability.');

-- Insert Some Products (using extracted data)
INSERT INTO products (category_id, name, description, url) VALUES
('025158f7-dc11-46a0-ae25-d43c46deb188', 'Aluminium Extrusion Profiles', 'Shaped by forcing aluminium alloy through a predesigned die opening.', 'https://newagealuminium.com/ProductDetail/aluminium-extrusion-profiles/0aff2723-1781-42d0-8215-b749bcc9335a'),
('025158f7-dc11-46a0-ae25-d43c46deb188', 'Flat Bar', 'Cost-effective and recyclable materials used in construction, engineering, and manufacturing.', 'https://newagealuminium.com/ProductDetail/flat-bar/eb472910-412d-4595-9263-5994f0b31c2f'),
('025158f7-dc11-46a0-ae25-d43c46deb188', 'Rectangular Hollow', 'Used in mechanical, structural and construction applications.', 'https://newagealuminium.com/ProductDetail/rectangular-hollow/e4d1926d-b99e-4ab9-942f-0b3c4efab409'),
('025158f7-dc11-46a0-ae25-d43c46deb188', 'U Channel', 'Metal rail used to secure glass panels to a floor, ceiling or wall.', 'https://newagealuminium.com/ProductDetail/u-channel/52daf34c-bf2e-4fa3-912b-3f8825da2699');

-- Insert Services
INSERT INTO services (name, description, category_id) VALUES
('Powder Coating', 'Electrostatic surface treatment for corrosion resistance.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('PVDF Coating', 'Weather-resistant surface treatment for enhanced durability.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('Wood Grain Finishing', 'Decorative finishing to make surfaces resemble wood.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('Anodizing', 'Electrochemical process for durable, corrosion-resistant oxide finish.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('Sand Blasting', 'Abrasive surface preparation to smooth surfaces.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('Plating', 'Applying a thin metal layer to improve hardness and decoration.', '34f845ca-4f71-472c-ab0d-5a5b3a809973'),
('Punch and Brake Press', 'Fabrication service for bending and shaping metal.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('Miter Cutting', 'Precision cutting service for angled joints.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('CNC Milling', 'Automated machining service for complex parts.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('Drill and Tapping', 'Creating holes and internal threads in metal components.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('Lathe Machining', 'Fabrication process for producing cylindrical parts.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('CNC Machining', 'General automated precision machining services.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('Stamping Press', 'High-volume metal forming and shaping service.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf'),
('Tapping', 'Creating threads in holes.', 'bb78f1f1-4111-4583-a9ab-5951f7cdeebf');
