"""
Script to convert clinic services data and import into billing system.
"""
import pandas as pd
from decimal import Decimal, InvalidOperation
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

PROCEDURES: (long list - will be processed)
"""

def parse_amount(amount_str):
    """Parse amount string, removing commas and converting to Decimal."""
    if isinstance(amount_str, (int, float)):
        return Decimal(str(amount_str))
    
    # Remove commas and spaces
    amount_str = str(amount_str).replace(',', '').replace(' ', '').strip()
    
    # Handle empty or zero
    if not amount_str or amount_str == '0' or amount_str == '':
        return Decimal('0')
    
    try:
        return Decimal(amount_str)
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0')

def generate_service_code(name, department, index):
    """Generate a unique service code."""
    # Clean name for code generation
    name_clean = name.upper().replace(' ', '_').replace('-', '_')
    name_clean = re.sub(r'[^A-Z0-9_]', '', name_clean)
    
    # Take first 3-4 words, max 20 chars
    words = name_clean.split('_')[:4]
    code_base = '_'.join(words)[:20]
    
    # Department prefix
    dept_prefix = {
        'PROCEDURE': 'PROC',
        'PHARMACY': 'PHARM',
        'RADIOLOGY': 'RAD',
        'LAB': 'LAB'
    }.get(department, 'SVC')
    
    # Generate code
    code = f"{dept_prefix}-{code_base}-{index:03d}"
    return code[:50]  # Max length

# Define all services with their categories
services_data = []

# CLINICAL CONSULTATION -> PROCEDURE
clinical_consultation = [
    ("DENTAL CONSULTATION", 20000),
    ("VISITING PAEDIATRICS CONSULTATION", 45000),
    ("GOPD CONSULTATION", 15000),
    ("Obstetrics and Gynaecology", 10000),
    ("FOLLOW UP (GOPD)", 10000),
    ("FOLLOW UP (CONSULTANT)", 15000),
    ("perioapical and bitewing film", 6000),
    ("occlusion radiograph", 6000),
    ("panoramic radiograph", 12000),
    ("TMJ panoramic radiograpg", 15000),
    ("panoramic sinus view", 15000),
    ("scaling and polishing", 15000),
    ("paedo scaling and polishing", 7000),
    ("wisdom tooth flushing", 1500),
    ("topical fluoridetion per tooth", 1500),
    ("periapical and bitewing film", 6000),
    ("occlusal x ray", 6000),
    ("panoramic radiograph", 12000),
    ("TMJ panoramic radiograph", 15000),
    ("panoramic sinus", 15000),
    ("scaling and polishing", 15000),
    ("paedo scaling and polishing", 7000),
    ("wisdom tooth flushing", 1500),
    ("topical fluoridation", 1500),
    ("tooth extraction (adult)", 15000),
    ("tooth extraction", 7500),
    ("surgical extraction (use of surgical drill and flap surgery)", 40000),
    ("surgical extractionof root", 60000),
    ("surgical extraction (by consultant surgeon)", 90000),
    ("simple enucleation of cyst", 30000),
    ("operculectomy", 10000),
    ("simple suturing", 10000),
    ("splinting (per tooth)", 5000),
    ("Repositioning decidous teeth", 10000),
    ("open reduction and internal fixation", 350000),
    ("surgical re-insertion of healing colar", 25000),
    ("preventive resin restoration", 7500),
    ("ZNOE temporary dressing without L.A", 3000),
    ("ZNOE temporary dressing with", 5000),
    ("Pin retained restoration", 500),
    ("pulpotomy", 30000),
    ("pulpectomy", 40000),
    ("RCT anterior", 60000),
    ("RCT premolar", 60000),
    ("RCT molar", 70000),
    ("RCT on 3rd molar", 80000),
    ("Root canal repeat", 80000),
    ("Root canal through a crown", 70000),
    ("Non vital whitening per tooth", 15000),
    ("tooth whitening (Normal)", 85000),
    ("Tooth whitening (full option)", 100000),
    ("Non hydrogen peroxide bleaching", 40000),
    ("lower study model", 2500),
    ("upper study model", 2500),
    ("use of clasp", 2000),
    ("upper biteguard", 25000),
    ("HAEMATOLOGIST CONSULTATION", 25000),
    ("OBSTETRICS/GYNAECOLOGIST CONSULTATION", 25000),
    ("visiting peditrician consultant", 20000),
    ("visiting orthopaedici consultant", 20000),
    ("IVF REGISTRATION/CONSULTATION", 60000),
    ("VISITING ORTHOPAEDIC CONSULTATION", 45000),
    ("VISITING ENDOCRINOLOGIST CONSULTATION", 55000),
    ("VISITING CARDIOLOGIST CONSULTATION", 45000),
    ("VISITING ENT CONSULTATION", 50000),
    ("VISITING NEUROLOGIST CONSULTATION", 45000),
    ("VISITING UROLOGIST CONSULTATION", 45000),
    ("VISITING DERMATOLOGIST CONSULTATION", 45000),
    ("VISITING PLASTIC SURGEON CONSULTATION", 50000),
    ("VISITING GENERAL SURGEON CONSULTATION", 50000),
]

# ANC -> PROCEDURE
anc_services = [
    ("ANC REGISTRATION (1ST 3 MONTHS)", 250000),
    ("ANTENATAL REGISTRATION (Including Antenatal Tests, 2 sections of Scan, Tetanus Immunization, Routine Antenatal Drugs)", 300000),
    ("NORMAL VAGINAL DELIVERY", 200000),
    ("ASSISTED VAGINAL DELIVERY", 270000),
    ("NORMAL VAGINAL DELIVERY", 300000),
    ("ASSISTED VAGINAL DELIVERY", 350000),
]

# REGISTRATION -> PROCEDURE
registration_services = [
    ("REGISTRATION", 5000),
    ("DENTAL REGISTRATION", 5000),
    ("REGISTRATION/CONSULTATION FOR IVF", 60000),
]

# VACCINES -> PHARMACY
vaccines = [
    ("BCG", 12000),
    ("HEPATITIS B VACCINE (ADULT)", 28000),
    ("MENNINGITIS", 12000),
    ("OPV", 4000),
    ("ORAL ROTAVIRUS", 12000),
    ("PCV (PNEUMOCCOCAL VACCINE)", 35000),
    ("PENTAVALENT", 12000),
    ("ROTAVIRUS", 15000),
    ("MEASLES", 12000),
    ("VITAMIN A", 4000),
    ("CERVAREX", 39000),
    ("HEPATITIS B VACCINE (CHILD)", 15000),
]

# PROCEDURES -> PROCEDURE (will add the full list)
procedures = [
    ("Adhesionlysis of uterus or cervix", 80000),
    ("Amuptation and/or joint disarticulation", 150000),
    ("Anaesthetic fee Intermediate", 20000),
    ("Anaesthetic fee Minor", 10000),
    ("Anaesthetic Major ( General Anaesthesia)", 35000),
    ("Anal Sphincterectomy", 0),
    ("ANC Booking- booking test, Reg and booking consult", 5000),
    ("ANC Booking test-HIV, PCV,VDRL,HBV,HCV,Urinalysis,blood group", 0),
    ("Ante Natal Card (6weeks after Delivery Validity)", 0),
    ("Appendicectomy ( Uncomplicated )", 70000),
    ("Appendicectomy (complicated )", 135000),
    ("Assisted  Breech delivery (Block)", 40000),
    ("Assisted delivery -Vacuum delivery", 20000),
    ("Augumentation Labour", 5000),
    ("Bilateral tube Ligation (Elective)", 120000),
    ("BilateralTubal ligation during CS", 30000),
    ("Biopsy of  superfial mass", 20000),
    ("Biopsy of breast", 35000),
    ("Biopsy of prostate", 65000),
    ("Biopsy of the bone tumour (Block fee)", 50000),
    ("Biopsy Of Tumour Of Abdominal Wall  ( Block fee )", 0),
    ("Birth Before Arrival care", 10000),
    ("Birth Certificate", 1000),
    ("BLOOD TRANSFUSION (OUTSOURCED) X1 POSITIVE UNIT", 44500),
    ("Bone grafting", 100000),
    ("Bone marrow biopsy   (Block fee)", 50000),
    ("Bowel resection & Anastomosis", 250000),
    ("Breast Lump Excision  ( Block fee )", 50000),
    ("Bronchooscopy (Block fee)", 0),
    ("Caesarian section (previous Scar) booked case", 200000),
    ("Caesarian section (previous Scar) Unbooked case", 230000),
    ("Caesarian section(First cs or without previous Scar) Booked", 180000),
    ("Caesarian section(First cs or without previous scar) unbooked", 200000),
    ("Cardiotocography ( CTG)", 0),
    ("Catheterisation Of Urinary Bladder + Urine Bag", 3000),
    ("Cautherization", 0),
    ("Certificate of medical fitness(Excluding Relevant Test)", 5000),
    ("Cervical Circlage insertion Surgery", 50000),
    ("Cervical Circlage removal", 10000),
    ("Cervical polypectomy", 200000),
    ("Cervical repair", 40000),
    ("Cholecystectomy", 0),
    ("Circumcision Of Male Baby(Local)", 7500),
    ("Circumcision Of Male Baby(Plastible)", 5000),
    ("Closed reduction only", 50000),
    ("Consultation after 1week", 0),
    ("Correction of Duputyren Contracture", 0),
    ("Crutches/Walking frame", 0),
    ("Cystourethroscopy", 120000),
    ("Death Certificate", 4000),
    ("Double bed ward - (Private)", 8000),
    ("Drainage of Anal Abscess", 30000),
    ("Drainage of Septic arthritis (Block fee)", 70000),
    ("Drainage of whitlow ( Block fee )", 5000),
    ("Ear Piercing For Female Baby", 2500),
    ("Ectopic Pregnancy", 150000),
    ("Emmergency Consultation", 0),
    ("Episiotomy", 10000),
    ("EUA", 35000),
    ("Evacuation of retained product of conception", 20000),
    ("Exchange Blood Transfussion (Rh +Ve, Inclusive Of Materials)", 20000),
    ("Exchange Blood Transfussion (Rh -Ve, Inclusive Of Materials)", 20000),
    ("Excison of intrascrotal mass", 90000),
    ("Family Card (2yrs Duration)", 0),
    ("Fibroid Surgery", 280000),
    ("Fistula - in - ano", 180000),
    ("foot/Ankle cast", 30000),
    ("Fore arm cast only", 30000),
    ("Ganglion Excision", 60000),
    ("Gastric Lavage", 15000),
    ("Gastroduodenoscopy (Block fee)", 0),
    ("General  ward (3 beds and more) per night", 3000),
    ("General Consultation (covers 1week)", 1000),
    ("Gynaecology", 2000),
    ("Haemorriodectomy", 120000),
    ("Hand/Wrist cast only", 30000),
    ("Herniorrhaphy ( Complicated or recurrent hernier)", 0),
    ("Herniorrhaphy ( Normal uncomplicated hernier)", 80000),
    ("Hydrocelectomy (Bilateral (Minor)", 100000),
    ("Hydrocelectomy (Unilateral (Minor)", 60000),
    ("Hydrointubation", 400000),
    ("Hyperglycaemia but consciouse", 25000),
    ("Hypertension severe", 25000),
    ("Hysterectomy", 250000),
    ("Hysteroscopy", 0),
    ("Incision & Drainage", 5000),
    ("Incubator", 25000),
    ("Incubator Care Per Day", 25000),
    ("Induction of Labour", 8000),
    ("Ingrowing Toe nail Excision  ( Block fee )", 30000),
    ("Injection Sclerotherapy Of Varicose Veins ( Block fee )", 0),
    ("Insertion of IUCD", 6500),
    ("Intensive Care ward for critical patient", 10000),
    ("Intensive Care ward for non critical patient", 0),
    ("Intestinal Obstruction with resection", 250000),
    ("Intestinal Obstruction without resection", 200000),
    ("Intra articular injection excluding drug", 5000),
    ("Joint Aspiration (Block fee)", 5000),
    ("Keloid Excision (Block fee)", 50000),
    ("Knee /Ankle brace", 0),
    ("Knee Effusion Tap", 2500),
    ("Labour (woman in labour)", 10000),
    ("Laparatomy", 150000),
    ("Laparoscopy & Dye test", 0),
    ("Leg/Knee cast", 35000),
    ("Lipoma excision  (Block fee)", 30000),
    ("Lumbar Puncture", 3000),
    ("Major I&D ( Block fee )", 30000),
    ("Major I&D ( Block fee )", 30000),
    ("Major Woiund Debridement (<18%)", 100000),
    ("Major Wound Debridement (>18%)", 50000),
    ("Major Wound Dressing / Day", 1000),
    ("Marsupialization", 50000),
    ("Medical Care for critically ill of coma, tetenus", 7500),
    ("Medical Care Per Day", 2500),
    ("Medical Report", 3000),
    ("Minimum Non-refundable Admission Deposit", 10000),
    ("Minor Debridement Of Burns   ( Block fee )", 0),
    ("Minor wound Debridement", 10000),
    ("Minor Wound Dressing", 750),
    ("Moderately ill (Normal)", 10000),
    ("Multiple Delivery (Booked Patient)", 35000),
    ("Multiple Delivery (Unbooked Patient)", 40000),
    ("Myomectomy (Fibroid Surgery)", 280000),
    ("Nasal Packing", 10000),
    ("Nebulisation +Drug (Out patient)", 2000),
    ("Neck Collar (Hard)", 0),
    ("Neck Collar (Soft)", 0),
    ("Nephrectomy", 250000),
    ("Non refundable admission deposit", 10000),
    ("Normal Delivery (Booked Patient)", 25000),
    ("Normal Delivery (Unbooked Patient)", 30000),
    ("NURSING CARE PER DAY", 5000),
    ("Oesophagoscopy (Block fee)", 0),
    ("Orchidectomy/Orchidopexy (Bilateral)", 90000),
    ("Orchidectomy/Orchidopexy (unilateral)", 50000),
    ("ORIF + Implant (Hand or Foot)", 360000),
    ("ORIF +Implant ( Major bone )", 260000),
    ("Ovarectomy", 150000),
    ("OVARIAN CYST CYSTECTOMY", 350000),
    ("Oxygen Therapy Per hour", 1000),
    ("PAP SMEAR (Procedure + Cytology)", 75000),
    ("Phototherapy Per Day", 10000),
    ("Physiotherapy Service / Session per day", 10000),
    ("POP APPLICATION", 40000),
    ("Proctoscopy (Block fee)", 0),
    ("Prostate Biopsy", 70000),
    ("Prostatectomy", 250000),
    ("Radical mastectomy", 270000),
    ("REFERRAL LETTER", 0),
    ("Release Of Chordae  (Block fee)", 0),
    ("Removal Impacted Faces", 10000),
    ("Removal of Implant", 180000),
    ("Removal Of IUCD (No  General Anaesthesia)", 5000),
    ("Repair of 3rd degree tear  (Block fee)", 40000),
    ("Repair of bowel perforation", 150000),
    ("Repair of minor vaginal laceration ( 2nd degree)", 10000),
    ("Repair of minor vaginal laceration ( 2nd degree) (Block fee)", 10000),
    ("Repair Of Ruptured Uterus", 200000),
    ("Repair of Third degree tear", 40000),
    ("Report of medical fitness(Excluding Relevant Test)", 3000),
    ("SALPHINGECTOMY/OOPHORECTOMY", 200000),
    ("Severely ill", 30000),
    ("Sigmoidoscopy (Block fee)", 0),
    ("Simple mastectomy + Histology", 240000),
    ("SINGLE BED - PRIVATE (VIP 1)", 20000),
    ("Skin Grafting ( <9% )", 0),
    ("Skin Grafting ( >9% )", 0),
    ("Skin traction", 50000),
    ("Small Cyst Excision ( Block fee )", 30000),
    ("Specialist Consultation - 1st Visit (O&G, Surgery, Paediatrics)", 5000),
    ("Specialist consultation follow up", 3000),
    ("Specialist for Rare Specielties(Neuro,Ortho,Cardiothoracic)", 0),
    ("Splenectomy", 150000),
    ("Subdural Tap", 0),
    ("Supra pubic cystostomy", 80000),
    ("Suprapubic cystectomy (SPC)", 80000),
    ("Suturing Of Major Wounds ( 10cm and above)", 30),
    ("Suturing Of Simple Laceration  ( Less than 10cm)", 20),
    ("Thearter fee Intermediate", 15000),
    ("Thearter fee Major", 30000),
    ("Thearter fee Minor", 5000),
    ("THERAPEUTIC D&C / UTERINE EVACUATION (LEGAL)", 150000),
    ("THIGH/HIP CAST", 70000),
    ("Thyroidectomy", 200000),
    ("TONGUE TIE RELEASE", 5000),
    ("Torsion spermatic cord", 150000),
    ("Tracheostomy (Block fee)", 0),
    ("Unconsciouse Patient", 50000),
    ("upper arm cast only", 35000),
    ("Ureteral re-implantation", 250000),
    ("Ureteral Repair", 200000),
    ("Urethroplasty", 250000),
    ("Whole lower limb cast", 40000),
    ("whole upper limb", 35000),
    ("perioepical xray", 3000),
    ("INDUCTION OF LABOUR", 400000),
    ("CEASERAN SECTION: Includes Surgery, Admission (For not more than 5 days, Post-OP Drugs)", 1200000),
    ("REPEAT CS", 850000),
    ("MANUAL VACUUM ASPIRATION (With Anaesthesia)", 350000),
    ("MANUAL VACUUM ASPIRATION (Without Anaesthesia)", 200000),
    ("HISTOLOGY", 45000),
    ("PAP SMEAR", 40000),
    ("OPEN SURGERY", 1000000),
    ("MYOMECTOMY", 1200000),
    ("DIAGNOSTIC HYSTEROSCOPY", 400000),
    ("DIAGNOSTIC LAPAROSCOPY", 800000),
    ("OPERATIVE HYSTEROSCOPY", 800000),
    ("CYST DRAINAGE WITH ANAESTHESIA", 250000),
    ("CYST WITHOUT ANAESTHESIA", 150000),
    ("ENDOMETRIAL SCRATCHING WITH ANAESTHESIA", 350000),
    ("ENDOMETRIAL SCRATCHING WITHOUT ANAESTHESIA", 200000),
    ("DIAGNOSTIC LAPARSOCOPY", 400000),
    ("LAPAROSCOPIC CYSTECTOMY", 1000000),
    ("LAPAROSCOPIC APPENDECTOMY", 1000000),
    ("MYOMECTOMY", 800000),
    ("HYSTERECTOMY", 1000000),
    ("CERVICAL CERCLAGE", 450000),
    ("FREEZING OF EMBRYOS (1 Year)", 1000000),
    ("FREEZING OF EMBRYOS (<1 Year)", 500000),
    ("INTRA-UTERINE INSEMINATION (IUI)", 600000),
    ("EPISIORRHAPHY", 100000),
    ("SUTURE OF LACERATIONS", 30000),
    ("APPENDECTOMY", 800000),
    ("WOUND DRESSING", 8000),
    ("MEDICAL REPORT", 10000),
    ("BIRTH CERTIFICATE", 10000),
    ("MEDICAL FITNESS CERTIFICATE", 10000),
    ("BONE MARROW ASPIRATION", 350000),
    ("BONE MARROW ASPIRATION + TREPHINE BIOPSY (EXCLUSIVE OF HISTOLOGY)", 400000),
    ("THEATRE USE", 80000),
    ("ANAESTHESIA", 70000),
    ("ANAESTHETIST", 80000),
    ("BLOOD TRANSFUSION (PATIENT'S DONOR) X1 POSITIVE UNIT", 34500),
    ("BLOOD TRANSFUSION (OUTSOURCED) X1 NEGATIVEUNIT", 60000),
    ("EAR PIERCING", 5000),
    ("OXYGEN ADMINISTRATION (BIG CYLINDER)", 22000),
    ("OXYGEN ADMINISTRATION (SMALL CYLINDER)", 8000),
    ("PHOTOTHERAPY PER DAY", 10000),
    ("INTRA-UTERINE INSEMINATION (IUI)", 600000),
    ("SINGLE BED - PRIVATE (VIP 2)", 20000),
    ("SINGLE BED - PRIVATE (VIP 3)", 20000),
    ("NURSING CARE - PRIVATE WARD", 10000),
    ("EUA PROCEDURE", 200000),
    ("LUTEAL PHASE SUPPORT DRUGS", 500000),
    ("PAP SMEAR AND HPV TESTING", 90000),
    ("HPV TESTING", 60000),
]

# DENTAL -> PROCEDURE
dental_services = [
    ("3D panoramic radiograph", 18000),
    ("currettage", 10000),
    ("fissure sealand per tooth", 5000),
    ("fluoredation whole mouth", 20000),
    ("fluoride varnish", 10000),
    ("desensitiation", 5000),
    ("3D panorami radiograph", 18000),
    ("currettage", 10000),
    ("fissure sealant (per tooth)", 5000),
    ("fluoridation (whole mouth)", 20000),
    ("fluoride varnish", 10000),
    ("desensitization", 5000),
    ("Dry socket treatment (external extraction)", 10000),
    ("incosion and drainage", 15000),
    ("apicectomy (excluding the RCT)", 40000),
    ("frenectomy by consultant surgeon", 75000),
    ("biopsies by consultant", 30000),
    ("Inter maxillary mandibular fixation (IMF)", 100000),
    ("anaesthetic fee", 20000),
    ("intravenous sedation", 30000),
    ("dycal lining", 1000),
    ("composite filling", 15000),
    ("composite build up", 25000),
    ("composite splinting", 15000),
    ("cervical composite restoration", 20000),
    ("GIC RESTORATION", 35000),
    ("cuspal grinding", 5000),
    ("Fail RCT appointment", 10000),
    ("Home bleaching with tray", 50000),
    ("Bleachbright home bleach", 30000),
    ("Acrylic denture(single tooth)", 15000),
    ("additional tooth", 7500),
    ("flexible dentures", 35000),
    ("additional tooth for flexible", 15000),
    ("Lab relining denture", 8000),
    ("chairside lining and repair", 5000),
    ("full denture lining", 25000),
    ("full lower/upper denture", 100000),
    ("immediate denture (single tooth)", 20000),
    ("additional immediate denture", 7500),
    ("lower biteguard", 2500),
    ("SCALING/POLISHING", 25000),
]

# IVF DRUGS -> PHARMACY
ivf_drugs = [
    ("ENRIFOL 2mg", 10000),
    ("PROGENOVA 2mg (1 Card)", 10000),
    ("BUSERELIN 0.5ml", 3500),
    ("LUPRODEX 3.75mg", 70000),
    ("ZOLADEX 3.6mg", 150000),
    ("HUMOG 75iu", 13000),
    ("ARGININE", 15000),
    ("HUMOG 150iu", 35000),
    ("GONAL F  75iu", 18000),
    ("MENUPUR 57iu", 10200),
    ("MEROFERT 150iu", 20000),
    ("HCG 5000iu", 25000),
    ("CYCLOGEST (1 Pkt)", 25000),
    ("CITROGEST (1 Pkt)", 25000),
    ("VASOPRIM (1 Card)", 150),
    ("GESTONE (1 Vial)", 5000),
    ("OVOFOLIC (1 Pkt by 60)", 20000),
    ("OVOFOLIC (By 30)", 11000),
    ("PROXEED (1 Pkt)", 22000),
    ("MEDFERTIL (1 Bottle)", 28000),
    ("FERTILAID MEN (1 Bottle)", 18000),
    ("FERTILAID WOMEN (1 Bottle)", 15000),
    ("DHEA (1 Bottle)", 6500),
    ("VIGOR CHOCOLATE (1 Bar)", 2500),
    ("MANIX (1 Capsule)", 400),
    ("MENOTROPIN (BLUE) 150iu", 28000),
    ("NON SPERMICIDAL CONDOM (1)", 8000),
    ("FERTIGAIN", 18000),
    ("CEFRORELOC (0.25mg)", 18000),
    ("POTENCIATOR (1 Pkt)", 15000),
    ("CITRODIOL 2mg (1 Pkt)", 10000),
    ("BUSERILIN 0.5ml (Per Dose)", 3500),
    ("OCP (1 Card)", 1200),
    ("PRIMOLUT N (1 Card)", 0),
    ("ESTRADIOL 2mg", 10000),
]

# FERTILITY SERVICES -> PROCEDURE
fertility_services = [
    ("SPERM FREEZING (PER VIAL) FOR 6 MONTHS", 400000),
    ("SPERM FREEZING (PER VIAL) FOR 1 Year", 800000),
    ("EMBRYO FREEZING (6 MONTHS)", 800000),
    ("EMBRYO FREEZING (1 Year)", 1500000),
    ("EGG FREEZING (6 MONTHS)", 700000),
    ("EGG FREEZING (1 Year)", 1400000),
    ("IVF REGISTRATION AND CONSULTATION", 60000),
    ("IVF (1 CYCLE)", 2500000),
    ("IVF (2 CYCLES)", 4800000),
    ("IVF (3 CYCLES)", 7000000),
    ("SURROGACY", 13000000),
    ("FROZEN EMBRYO TRANSFER (FET)", 1200000),
    ("IVF (1 CYCLE) WITH DONOR EGGS", 3300000),
    ("DONOR EGGS", 800000),
    ("IVF (2 CYCLES) WITH DONOR EGGS", 5600000),
]

# CONSUMABLES -> PHARMACY
consumables = [
    ("ABDOMOP (Per Piece)", 400),
    ("BLOOD BAG", 6000),
    ("BLOOD GIVING SET", 1200),
    ("CANNULA", 600),
    ("CORD CLAMP", 300),
    ("DISPENSING ENVELOPES", 100),
    ("DRIP GIVING SET", 800),
    ("FACE MASK", 300),
    ("HVS MCS", 4500),
    ("I.V FLUIDS 500ml", 1500),
    ("LATEX GLOVES (PER PACK)", 7000),
    ("LATEX GLOVES (1 PIECE)", 200),
    ("MANTOUX TEST", 2000),
    ("NEBULIZER (PER SESSION)", 5000),
    ("NEEDLE & SYRINGE (2mg, 5mg, 10mg)", 250),
    ("OXYGEN (BIG CYLINDER)", 22000),
    ("OXYGEN (SMALL CYLINDER)", 12000),
    ("PAEDIATRICS FEEDING TUBE (PER ONE)", 900),
    ("PLASTER (DURAPHONE WHITE)", 1800),
    ("PROCEDURE", 2000),
    ("SOLUSET", 4500),
    ("SPINAL NEEDLE", 3000),
    ("SURGICAL GLOVES (PER PAIR)", 1000),
    ("SYRINGE 50mls", 3000),
    ("URETHRAL CATHETER (Different sizes)", 1500),
    ("URINE BAG", 3000),
    ("URINE/SPUTUM/WD SWAB MCS", 4500),
    ("DISPOSABLE SPECULUM", 500),
    ("SUFRATUL (VASELINE GAUGE)", 1000),
    ("PLASTIBEL", 900),
    ("VICRYL SUTURE (PER PIECE)", 2500),
    ("INSULIN SYRINGE", 600),
    ("SPIKE", 300),
    ("NITINGALE", 3500),
    ("IVF (1L)", 3000),
    ("10ml SYRINGE (PER PIECE)", 250),
    ("WATER FOR INJECTION", 300),
    ("INJECTION WATER (PER PIECE)", 300),
    ("NYLON SUTURE (PER PIECE)", 1000),
    ("SUBCUTE NEEDLE", 500),
    ("HOURLY OXYGEN ADMINISTRATION (PER HOUR)", 8000),
]

# Combine all services
all_services = []

# Add PROCEDURE services
index = 1
for name, amount in clinical_consultation + anc_services + registration_services + procedures + dental_services + fertility_services:
    if amount > 0:  # Skip zero amounts
        code = generate_service_code(name, "PROCEDURE", index)
        all_services.append({
            "Department": "PROCEDURE",
            "Service Code": code,
            "Service Name": name,
            "Amount": amount,
            "Description": ""
        })
        index += 1

# Add PHARMACY services
index = 1
for name, amount in vaccines + ivf_drugs + consumables:
    if amount > 0:  # Skip zero amounts
        code = generate_service_code(name, "PHARMACY", index)
        all_services.append({
            "Department": "PHARMACY",
            "Service Code": code,
            "Service Name": name,
            "Amount": amount,
            "Description": ""
        })
        index += 1

# Create DataFrame
df = pd.DataFrame(all_services)

# Save to Excel
output_file = "clinic_services.xlsx"
df.to_excel(output_file, index=False, sheet_name="Services")
print(f"Created Excel file: {output_file}")
print(f"Total services: {len(df)}")
print(f"PROCEDURE services: {len(df[df['Department'] == 'PROCEDURE'])}")
print(f"PHARMACY services: {len(df[df['Department'] == 'PHARMACY'])}")

