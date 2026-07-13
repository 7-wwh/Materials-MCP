-- Database Schema for Kamco Aluminium

-- Table for Company Profile
CREATE TABLE company_info (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    established_year INTEGER,
    years_experience INTEGER,
    custom_profiles_count INTEGER,
    export_countries_count INTEGER,
    description TEXT,
    phone TEXT,
    fax TEXT,
    email TEXT,
    address TEXT
);

-- Table for Product Categories
CREATE TABLE product_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    product_count INTEGER,
    description TEXT
);

-- Table for Services
CREATE TABLE services (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

-- Table for Alloy Grades
CREATE TABLE alloy_grades (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    strength TEXT,
    surface_finish TEXT,
    suitable_for TEXT
);

-- Table for Chemical Composition
CREATE TABLE chemical_composition (
    id INTEGER PRIMARY KEY,
    alloy_grade_id INTEGER,
    si TEXT,
    fe TEXT,
    cu TEXT,
    mn TEXT,
    mg TEXT,
    cr TEXT,
    zn TEXT,
    ti TEXT,
    al_min TEXT,
    FOREIGN KEY (alloy_grade_id) REFERENCES alloy_grades(id)
);

-- Table for Mechanical and Physical Properties
CREATE TABLE mechanical_properties (
    id INTEGER PRIMARY KEY,
    alloy_grade_id INTEGER,
    temper TEXT,
    thickness_diameter TEXT,
    tensile_ultimate_mpa TEXT,
    tensile_yield_mpa TEXT,
    hardness_hrb TEXT,
    webster_hardness TEXT,
    density_kg_mm3 TEXT,
    modulus_of_elasticity_mpa TEXT,
    elongation_percent TEXT,
    conductivity_iacs TEXT,
    FOREIGN KEY (alloy_grade_id) REFERENCES alloy_grades(id)
);

-- Table for Locations
CREATE TABLE locations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

-- Insert Initial Data
INSERT INTO company_info (name, established_year, years_experience, custom_profiles_count, export_countries_count, description, phone, fax, email, address)
VALUES ('Kamco Aluminium Sdn Bhd', 1980, 40, 1000, 20, 'A trusted name in aluminium profiles and engineered solutions. Expertise in extrusion, bending, and product innovation.', '+ (603) 8964 9991', '+ (603) 8964 5990', 'sales@kamcoaluminium.com', 'No.3A, Jalan Suria Park 1, Suria Park, Kawasan Perindustrian Kampung Baru Balakong, 43300 Seri Kembangan, Selangor');

INSERT INTO locations (name, description) VALUES
('HQ Office', 'Headquarters for sales and administration.'),
('Factory K2', 'Manufacturing facility.'),
('Factory K3', 'Manufacturing facility.'),
('Warehouse K5', 'Warehouse facility.');

INSERT INTO product_categories (name, product_count, description) VALUES
('Standard Geometric', 9, 'Busbar, hollow sections, angles, channels'),
('Industry Profile', 7, 'Machine frames, heatsinks, pneumatic cylinders, solar panel mounting structures'),
('Building & Construction Material', 1, 'Shop front, windows, louvers, skylight sections'),
('Solar Mounting System', 1, NULL),
('Canopy Structure Profile', 6, NULL),
('Event Aluminium System', 4, NULL),
('Aluminium Scaffold', 1, NULL),
('Aluminium Ladder', 4, NULL),
('Aluminium Fabrication', 1, 'Custom welded frames, CNC machined parts, machine base plates, fully assembled workstations'),
('Sound Barrier', 1, NULL);

INSERT INTO services (name, description) VALUES
('Aluminium Die Manufacturing', 'In-house die manufacturing facility using Fanuc Wire-cut and CNC/Lathe machines for precision and rapid turnaround.'),
('Aluminium Extrusion', 'Specialized presses (4-inch to 8-inch) for versatile order volumes, from prototypes to mass production, with 5-7 day lead times.'),
('Anodizing', 'Automated lines for uniform, durable finishes (Clear, Champagne, Bronze, Black, Hairline, Bright Deep) up to 20 feet.'),
('Powder Coating', 'AAMA-compliant, TGIC-free, chrome-free pre-treatment, partnering with Jotun, AkzoNobel, etc.'),
('Woodgrain Sublimation', 'Authentic Italian technology (Sublitex/Decoral) for wood aesthetics with aluminium durability.'),
('Precision Machining', 'CNC machining, precision cutting (up to 24"), drilling, punching, and bending using CAD/CAM and Solidwork systems.'),
('Advanced Welding', 'TIG and MIG welding for constructing complex structural frames.'),
('Export & Project Support', 'Proven track record in international markets with specialized packaging, logistics, and regulatory compliance (MITI, AFAS).'),
('Sound Barrier Solutions', 'Comprehensive noise mitigation lifecycle management: acoustic modeling, Japanese-engineered metallic panels, transparent acrylic panels, and in-house testing.');

-- Insert Alloy Data Grouped by Alloy
-- 1050
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('1050', 'Heat-Treatable Extrusion Alloy', 'Very Low', 'Not Suitable for Anodizing and powder coating', 'Electrical application such as busbars and lighting protection systems.');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '1050'), '0.09', '0.108', '0.002', '0.04', '0.047', '-', '0.001', '0.01', '99.50%');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES ((SELECT id FROM alloy_grades WHERE name = '1050'), 'T4', '2', '75', '30', NULL, NULL, '2.705', NULL, '30%', '57-58%');

-- 1070
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('1070', 'Heat-Treatable Extrusion Alloy', 'Very Low', 'Not Suitable for Anodizing and powder coating', 'Electrical application such as busbars and lighting protection systems.');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '1070'), '0.062', '0.12', '0.001', '0.001', '0.003', '-', '0.004', '0.013', '99.70%');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES ((SELECT id FROM alloy_grades WHERE name = '1070'), 'T4', '2', '95', '35', NULL, NULL, '2.705', NULL, '35%', '58-60%');

-- 6005
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('6005', 'Heat-Treatable Extrusion Alloy', 'High', 'Suitable for Anodizing an powder coating finishing', 'Structural components, solar panel framing, solar mounting structure,transport and industrial used');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '6005'), '0.67-0.75', '0.11-0.15', '0.04-0.07', '0.04-0.07', '0.53-0.59', '0.04-0.07', '0.02', '0.03', 'Rem');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES 
((SELECT id FROM alloy_grades WHERE name = '6005'), 'T4', '<25', '150', '80', '30', '0-2', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6005'), 'T5', '3', '215', '160', '65', '11-13', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6005'), 'T6', '5', '260', '200', '75', '13-15', '2.705', '69 × 10³', NULL, NULL);

-- 6060
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('6060', 'Heat-Treatable Extrusion Alloy', 'Medium', 'Excellent for Anodizing, powder coating finishing', 'Architectural profile, furniture, household products, industrial profile and more');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '6060'), '0.3-0.6', '0.1-0.3', '0.05-0.1', '0.05-0.1', '0.35-0.6', '0.05', '0.15', '0.1', 'Rem');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES
((SELECT id FROM alloy_grades WHERE name = '6060'), 'T4', '<25', '120', '55', '23', '0-2', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6060'), 'T5', '3', '150', '95', '58', '10-12', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6060'), 'T6', '3.1', '190', '150', '70', '11-13', '2.705', '69 × 10³', NULL, NULL);

-- 6061
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('6061', 'Heat-Treatable Extrusion Alloy', 'High', 'Not Suitable for Anodizing but can be powder coated', 'Structural components, transport and industrial used');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '6061'), '0.4-0.8', '0.7', '0.14-0.35', '0.15', '0.7-1.2', '0.04-0.35', '0.25', '0.15', 'Rem');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES
((SELECT id FROM alloy_grades WHERE name = '6061'), 'T4', '<25', '180', '110', '40', '0-2', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6061'), 'T5', '3', '240', '145', '60', '11-13', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6061'), 'T6', '5', '300', '265', '90', '14-16', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6061'), 'T651', '5', '310', '275', '95', '14-16', '2.705', '69 × 10³', NULL, NULL);

-- 6063
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('6063', 'Heat-Treatable Extrusion Alloy', 'Medium', 'Excellent for Anodizing, powder coating finishing', 'Architectural profile, furniture, household products, industrial profile and more');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '6063'), '0.2-0.6', '0.1-0.3', '0.002', '0.05-0.1', '0.45-0.9', '0.5', '0.1', '0.1', 'Rem');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES
((SELECT id FROM alloy_grades WHERE name = '6063'), 'T4', '<25', '130', '65', '25', '0-2', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6063'), 'T5', '3', '150', '110', '60', '9-11', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6063'), 'T6', '3.1', '205', '170', '73', '12-14', '2.705', '69 × 10³', NULL, NULL);

-- 6082
INSERT INTO alloy_grades (name, type, strength, surface_finish, suitable_for) VALUES ('6082', 'Heat-Treatable Extrusion Alloy', 'Very High', 'Not Suitable for Anodizing but can be powder coated', 'Structural components, marine, cranes and heavy duty products');
INSERT INTO chemical_composition (alloy_grade_id, si, fe, cu, mn, mg, cr, zn, ti, al_min) VALUES ((SELECT id FROM alloy_grades WHERE name = '6082'), '0.7-1.3', '0.5', '0.1', '0.4-1.0', '0.45-0.8', '0.25', '0.2', '0.1', 'Rem');
INSERT INTO mechanical_properties (alloy_grade_id, temper, thickness_diameter, tensile_ultimate_mpa, tensile_yield_mpa, hardness_hrb, webster_hardness, density_kg_mm3, modulus_of_elasticity_mpa, elongation_percent, conductivity_iacs) VALUES
((SELECT id FROM alloy_grades WHERE name = '6082'), 'T5', '5', '260', '200', '75', '12-14', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6082'), 'T6', '5', '300', '250', '90', '13-15', '2.705', '69 × 10³', NULL, NULL),
((SELECT id FROM alloy_grades WHERE name = '6082'), 'T651', '5', '310', '260', '95', '14-16', '2.705', '69 × 10³', NULL, NULL);
