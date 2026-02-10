"""
Script to parse clinic services data and convert to Excel format for import.
"""
import pandas as pd
from decimal import Decimal
import re

# Raw data from user
raw_data = """
CLINICAL CONSULTATION:
1	DENTAL CONSULTATION	20,000.00
2	VISITING PAEDIATRICS CONSULTATION	45,000.00
3	GOPD CONSULTATION	15,000.00
4	Obstetrics and Gynaecology	10,000.00
5	FOLLOW UP (GOPD)	10,000.00
6	FOLLOW UP (CONSULTANT)	15,000.00
7	perioapical and bitewing film	6,000.00
8	occlusion radiograph	6,000.00
9	panoramic radiograph	12,000.00
10	TMJ panoramic radiograpg	15,000.00
11	panoramic sinus view	15,000.00
12	scaling and polishing	15,000.00
13	paedo scaling and polishing	7,000.00
14	wisdom tooth flushing	1,500.00
15	topical fluoridetion per tooth	1,500.00
16	periapical and bitewing film	6,000.00
17	occlusal x ray	6,000.00
18	panoramic radiograph	12,000.00
19	TMJ panoramic radiograph	15,000.00
20	panoramic sinus	15,000.00
21	scaling and polishing	15,000.00
22	paedo scaling and polishing	7,000.00
23	wisdom tooth flushing	1,500.00
24	topical fluoridation	1,500.00
25	tooth extraction (adult)	15,000.00
26	tooth extraction	7,500.00
27	surgical extraction (use of surgical drill and flap surgery)	40,000.00
28	surgical extractionof root	60,000.00
29	surgical extraction (by consultant surgeon)	90,000.00
30	simple enucleation of cyst	30,000.00
31	operculectomy	10,000.00
32	simple suturing	10,000.00
33	splinting (per tooth)	5,000.00
34	Repositioning decidous teeth	10,000.00
35	open reduction and internal fixation	350,000.00
36	surgical re-insertion of healing colar	25,000.00
37	preventive resin restoration	7,500.00
38	ZNOE temporary dressing without L.A	3,000.00
39	ZNOE temporary dressing with	5,000.00
40	Pin retained restoration	500
41	pulpotomy	30,000.00
42	pulpectomy	40,000.00
43	RCT anterior	60,000.00
44	RCT premolar	60,000.00
45	RCT molar	70,000.00
46	RCT on 3rd molar	80,000.00
47	Root canal repeat	80,000.00
48	Root canal through a crown	70,000.00
49	Non vital whitening per tooth	15,000.00
50	tooth whitening (Normal)	85,000.00
51	Tooth whitening (full option)	100,000.00
52	Non hydrogen peroxide bleaching	40,000.00
53	lower study model	2,500.00
54	upper study model	2,500.00
55	use of clasp	2,000.00
56	upper biteguard	25,000.00
57	HAEMATOLOGIST CONSULTATION	25,000.00
58	OBSTETRICS/GYNAECOLOGIST CONSULTATION	25,000.00
59	visiting peditrician consultant	20,000.00
60	visiting orthopaedici consultant	20,000.00
61	IVF REGISTRATION/CONSULTATION	60,000.00
62	VISITING ORTHOPAEDIC CONSULTATION	45,000.00
63	VISITING ENDOCRINOLOGIST CONSULTATION	55,000.00
64	VISITING CARDIOLOGIST CONSULTATION	45,000.00
65	VISITING ENT CONSULTATION	50,000.00
66	VISITING NEUROLOGIST CONSULTATION	45,000.00
67	VISITING UROLOGIST CONSULTATION	45,000.00
68	VISITING DERMATOLOGIST CONSULTATION	45,000.00
69	VISITING PLASTIC SURGEON CONSULTATION	50,000.00
70	VISITING GENERAL SURGEON CONSULTATION	50,000.00

ANC:
1	ANC REGISTRATION (1ST 3 MONTHS)	250,000.00
2	ANTENATAL REGISTRATION (Including Antenatal Tests, 2 sections of Scan, Tetanus Immunization, Routine Antenatal Drugs)	300,000.00
3	NORMAL VAGINAL DELIVERY	200,000.00
4	ASSISTED VAGINAL DELIVERY	270,000.00
5	NORMAL VAGINAL DELIVERY	300,000.00
6	ASSISTED VAGINAL DELIVERY	350,000.00

REGISTRATION:
1	REGISTRATION	5,000.00
2	DENTAL REGISTRATION	5,000.00
3	REGISTRATION/CONSULTATION FOR IVF	60,000.00

VACCINES:
1	BCG	12,000.00
2	HEPATITIS B VACCINE (ADULT)	28,000.00
3	MENNINGITIS	12,000.00
4	OPV	4,000.00
5	ORAL ROTAVIRUS	12,000.00
6	PCV (PNEUMOCCOCAL VACCINE)	35,000.00
7	PENTAVALENT	12,000.00
8	ROTAVIRUS	15,000.00
9	MEASLES	12,000.00
10	VITAMIN A	4,000.00
11	CERVAREX	39,000.00
12	HEPATITIS B VACCINE (CHILD)	15,000.00
"""

# Function to clean amount string
def clean_amount(amount_str):
    """Convert amount string to decimal number."""
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    # Remove commas and convert to float
    amount_str = str(amount_str).replace(',', '').strip()
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return 0.0

# Function to generate service code
def generate_service_code(name, category, index):
    """Generate a unique service code."""
    # Create prefix from category
    prefix_map = {
        'CLINICAL CONSULTATION': 'CONS',
        'ANC': 'ANC',
        'REGISTRATION': 'REG',
        'VACCINES': 'VAC',
        'PROCEDURES': 'PROC',
        'DENTAL': 'DENT',
        'IVF DRUGS': 'IVF-DRUG',
        'FERTILITY SERVICES': 'FERT',
        'CONSUMABLES': 'CONS'
    }
    prefix = prefix_map.get(category, 'SVC')
    
    # Get first letters of name for code
    words = name.upper().split()
    if len(words) >= 2:
        code_suffix = ''.join([w[0] for w in words[:3]])[:4]
    else:
        code_suffix = name[:4].upper().replace(' ', '')
    
    # Clean code suffix
    code_suffix = re.sub(r'[^A-Z0-9]', '', code_suffix)
    
    return f"{prefix}-{code_suffix}-{index:03d}"

# Function to determine department
def get_department(category, service_name):
    """Determine department based on category and service name."""
    name_upper = service_name.upper()
    
    # Check for radiology services
    if any(word in name_upper for word in ['RADIOGRAPH', 'X-RAY', 'XRAY', 'SCAN', 'CT', 'MRI', 'ULTRASOUND']):
        return 'RADIOLOGY'
    
    # Check for lab services
    if any(word in name_upper for word in ['TEST', 'BLOOD', 'URINE', 'CULTURE', 'SMEAR', 'BIOPSY']):
        if 'PAP SMEAR' not in name_upper:  # PAP SMEAR is a procedure
            return 'LAB'
    
    # Vaccines and drugs go to pharmacy
    if category in ['VACCINES', 'IVF DRUGS']:
        return 'PHARMACY'
    
    # Everything else is a procedure
    return 'PROCEDURE'

# Parse the data
services = []
categories = {
    'CLINICAL CONSULTATION': raw_data.split('CLINICAL CONSULTATION:')[1].split('ANC:')[0].strip(),
    'ANC': raw_data.split('ANC:')[1].split('REGISTRATION:')[0].strip(),
    'REGISTRATION': raw_data.split('REGISTRATION:')[1].split('VACCINES:')[0].strip(),
    'VACCINES': raw_data.split('VACCINES:')[1].split('PROCEDURES:')[0].strip() if 'PROCEDURES:' in raw_data else raw_data.split('VACCINES:')[1].strip(),
}

for category, data in categories.items():
    lines = data.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            try:
                index = int(parts[0].strip())
                name = parts[1].strip()
                amount_str = parts[2].strip()
                amount = clean_amount(amount_str)
                
                if amount > 0 and name:
                    service_code = generate_service_code(name, category, index)
                    department = get_department(category, name)
                    
                    services.append({
                        'Department': department,
                        'Service Code': service_code,
                        'Service Name': name,
                        'Amount': amount,
                        'Description': f'{category} service'
                    })
            except Exception as e:
                print(f"Error parsing line: {line} - {e}")

# Create DataFrame
df = pd.DataFrame(services)

# Save to Excel
output_file = 'clinic_services_import.xlsx'
df.to_excel(output_file, index=False, sheet_name='Services')
print(f"Created Excel file: {output_file}")
print(f"Total services: {len(services)}")
print(f"\nBy Department:")
print(df['Department'].value_counts())

