"""
Parse pharmacy services data and create CSV for ServiceCatalog import.
"""
import csv
import re

# Paste your pharmacy data here
PHARMACY_DATA = """Comet Sanitary Pad, 2,500.00
10ml Syringe, 250
150ml Burette IV Set, 1,500.00
1ml syringe, 1,200.00
20 ml Syringe, 500
2ml Syringe, 250
2Way 16Fr 30ml Catheter, 1,500.00
50ml Perfuser Syringe, 3,000.00
5ml syringe, 250
ABIDEC DROP, 6,000.00
ABIDEC SYRUP, 30,000.00
ABITREN 100MG, 1,000.00
Absorent Gauze, 14,000.00
ACCOLATE 20MG, 4,000.00
ACICLOVIR CREAM 10 GRAMS, 3,500.00
ACTIFED, 700
ACTIFED SYRUP 60ML, 3,500.00
ACTIVATED VEG CHARCOAL 260MG CAP, 1,500.00
ACTRAPID INSULIN 10MLS ( 100UNITS/ML ), 15,000.00
ACTRAPID INSULIN 10MLS ( 40UNITS/ML ), 10,000.00"""

def parse_pharmacy_data(data_text):
    """Parse pharmacy data from text format."""
    lines = data_text.strip().split('\n')
    services = []
    
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        # Find the last occurrence of a comma followed by digits (the amount)
        # This handles amounts with commas like "2,500.00"
        match = re.search(r',\s*([\d,]+(?:\.\d{1,2})?)$', line)
        if not match:
            print(f'Skipping line {i}: No amount found - {line[:50]}')
            continue
        
        amount_str = match.group(1).strip()
        name = line[:match.start()].strip()
        
        # Remove commas from amount and convert to float
        amount_str = amount_str.replace(',', '')
        try:
            amount = float(amount_str)
            # Skip if amount is 0 or negative
            if amount <= 0:
                print(f'Skipping line {i}: Zero or negative amount - {name}')
                continue
            
            service_code = f'PHARM-{i:04d}'
            services.append({
                'Department': 'PHARMACY',
                'Service Code': service_code,
                'Service Name': name,
                'Amount': f'{amount:.2f}',
                'Description': name,
                'Category': 'DRUG',
                'Workflow Type': 'DRUG_DISPENSE',
                'Requires Visit': 'TRUE',
                'Requires Consultation': 'TRUE',
                'Auto Bill': 'TRUE',
                'Bill Timing': 'AFTER',
                'Allowed Roles': 'DOCTOR, PHARMACIST',
                'Is Active': 'TRUE'
            })
        except ValueError:
            print(f'Skipping line {i}: Invalid amount - {amount_str} for {name[:30]}')
    
    return services

def write_to_csv(services, filename='pharmacy_services.csv'):
    """Write services to CSV file."""
    fieldnames = [
        'Department', 'Service Code', 'Service Name', 'Amount', 
        'Description', 'Category', 'Workflow Type', 'Requires Visit', 
        'Requires Consultation', 'Auto Bill', 'Bill Timing', 
        'Allowed Roles', 'Is Active'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(services)
    
    print(f'[OK] Created {filename} with {len(services)} services')

if __name__ == '__main__':
    # Read the full data from a file if it exists, otherwise use the sample
    try:
        with open('pharmacy_data.txt', 'r', encoding='utf-8') as f:
            data = f.read()
        print('Reading from pharmacy_data.txt')
    except FileNotFoundError:
        data = PHARMACY_DATA
        print('Using embedded sample data (only first 20 items)')
        print('To process full data: Create pharmacy_data.txt with all items')
    
    services = parse_pharmacy_data(data)
    write_to_csv(services)
    
    # Show summary
    print(f'\nSummary:')
    print(f'  Total services: {len(services)}')
    if services:
        total_value = sum(float(s['Amount']) for s in services)
        print(f'  Total catalog value: N{total_value:,.2f}')
        print(f'  Average price: N{total_value/len(services):,.2f}')
        print(f'\nFirst 5 services:')
        for s in services[:5]:
            print(f'  {s["Service Code"]}: {s["Service Name"][:40]:40s} - N{s["Amount"]}')
        print(f'\nLast 5 services:')
        for s in services[-5:]:
            print(f'  {s["Service Code"]}: {s["Service Name"][:40]:40s} - N{s["Amount"]}')
    
    print(f'\nNext steps:')
    print(f'  1. Review pharmacy_services.csv')
    print(f'  2. Run: python manage.py import_service_catalog pharmacy_services.csv --dry-run')
    print(f'  3. If OK: python manage.py import_service_catalog pharmacy_services.csv')

