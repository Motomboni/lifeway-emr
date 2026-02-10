"""
Script to import clinic services from the provided data into the billing system.

This script parses the clinic services data and imports them into the appropriate
departmental price lists.
"""
import os
import sys
import django
from decimal import Decimal, InvalidOperation

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.billing.price_lists import (
    LabServicePriceList,
    PharmacyServicePriceList,
    RadiologyServicePriceList,
    ProcedureServicePriceList,
)

# Map categories to departments
CATEGORY_TO_DEPARTMENT = {
    'CLINICAL CONSULTATION': 'PROCEDURE',
    'ANC': 'PROCEDURE',
    'REGISTRATION': 'PROCEDURE',
    'VACCINES': 'PHARMACY',
    'PROCEDURES': 'PROCEDURE',
    'DENTAL': 'PROCEDURE',
    'IVF DRUGS': 'PHARMACY',
    'FERTILITY SERVICES': 'PROCEDURE',
    'CONSUMABLES': 'PROCEDURE',
}

DEPARTMENT_MODELS = {
    'LAB': LabServicePriceList,
    'PHARMACY': PharmacyServicePriceList,
    'RADIOLOGY': RadiologyServicePriceList,
    'PROCEDURE': ProcedureServicePriceList,
}


def parse_amount(amount_str):
    """Parse amount string, removing commas and converting to Decimal."""
    if not amount_str or amount_str == '0' or amount_str.strip() == '':
        return None
    
    # Remove commas and spaces
    amount_str = str(amount_str).replace(',', '').replace(' ', '').strip()
    
    try:
        return Decimal(amount_str)
    except (ValueError, TypeError, InvalidOperation):
        return None


def generate_service_code(category, name, index):
    """Generate a unique service code."""
    # Create a code from category prefix and index
    category_prefix = {
        'CLINICAL CONSULTATION': 'CONS',
        'ANC': 'ANC',
        'REGISTRATION': 'REG',
        'VACCINES': 'VAC',
        'PROCEDURES': 'PROC',
        'DENTAL': 'DENT',
        'IVF DRUGS': 'IVF-DRUG',
        'FERTILITY SERVICES': 'FERT',
        'CONSUMABLES': 'CONS',
    }.get(category, 'SVC')
    
    # Clean name for code
    name_clean = ''.join(c for c in name.upper() if c.isalnum())[:10]
    return f"{category_prefix}-{index:03d}-{name_clean}"


def import_services():
    """Import all clinic services."""
    
    # Clinic services data
    services_data = """
CLINICAL CONSULTATION:
1	DENTAL CONSULTATION	20000.00
2	VISITING PAEDIATRICS CONSULTATION	45000.00
3	GOPD CONSULTATION	15000.00
4	Obstetrics and Gynaecology	10000.00
5	FOLLOW UP (GOPD)	10000.00
6	FOLLOW UP (CONSULTANT)	15000.00
7	perioapical and bitewing film	6000.00
8	occlusion radiograph	6000.00
9	panoramic radiograph	12000.00
10	TMJ panoramic radiograpg	15000.00
11	panoramic sinus view	15000.00
12	scaling and polishing	15000.00
13	paedo scaling and polishing	7000.00
14	wisdom tooth flushing	1500.00
15	topical fluoridetion per tooth	1500.00
16	periapical and bitewing film	6000.00
17	occlusal x ray	6000.00
18	panoramic radiograph	12000.00
19	TMJ panoramic radiograph	15000.00
20	panoramic sinus	15000.00
21	scaling and polishing	15000.00
22	paedo scaling and polishing	7000.00
23	wisdom tooth flushing	1500.00
24	topical fluoridation	1500.00
25	tooth extraction (adult)	15000.00
26	tooth extraction	7500.00
27	surgical extraction (use of surgical drill and flap surgery)	40000.00
28	surgical extractionof root	60000.00
29	surgical extraction (by consultant surgeon)	90000.00
30	simple enucleation of cyst	30000.00
31	operculectomy	10000.00
32	simple suturing	10000.00
33	splinting (per tooth)	5000.00
34	Repositioning decidous teeth	10000.00
35	open reduction and internal fixation	350000.00
36	surgical re-insertion of healing colar	25000.00
37	preventive resin restoration	7500.00
38	ZNOE temporary dressing without L.A	3000.00
39	ZNOE temporary dressing with	5000.00
40	Pin retained restoration	500.00
41	pulpotomy	30000.00
42	pulpectomy	40000.00
43	RCT anterior	60000.00
44	RCT premolar	60000.00
45	RCT molar	70000.00
46	RCT on 3rd molar	80000.00
47	Root canal repeat	80000.00
48	Root canal through a crown	70000.00
49	Non vital whitening per tooth	15000.00
50	tooth whitening (Normal)	85000.00
51	Tooth whitening (full option)	100000.00
52	Non hydrogen peroxide bleaching	40000.00
53	lower study model	2500.00
54	upper study model	2500.00
55	use of clasp	2000.00
56	upper biteguard	25000.00
57	HAEMATOLOGIST CONSULTATION	25000.00
58	OBSTETRICS/GYNAECOLOGIST CONSULTATION	25000.00
59	visiting peditrician consultant	20000.00
60	visiting orthopaedici consultant	20000.00
61	IVF REGISTRATION/CONSULTATION	60000.00
62	VISITING ORTHOPAEDIC CONSULTATION	45000.00
63	VISITING ENDOCRINOLOGIST CONSULTATION	55000.00
64	VISITING CARDIOLOGIST CONSULTATION	45000.00
65	VISITING ENT CONSULTATION	50000.00
66	VISITING NEUROLOGIST CONSULTATION	45000.00
67	VISITING UROLOGIST CONSULTATION	45000.00
68	VISITING DERMATOLOGIST CONSULTATION	45000.00
69	VISITING PLASTIC SURGEON CONSULTATION	50000.00
70	VISITING GENERAL SURGEON CONSULTATION	50000.00

ANC:
1	ANC REGISTRATION (1ST 3 MONTHS)	250000.00
2	ANTENATAL REGISTRATION (Including Antenatal Tests, 2 sections of Scan, Tetanus Immunization, Routine Antenatal Drugs)	300000.00
3	NORMAL VAGINAL DELIVERY	200000.00
4	ASSISTED VAGINAL DELIVERY	270000.00
5	NORMAL VAGINAL DELIVERY	300000.00
6	ASSISTED VAGINAL DELIVERY	350000.00

REGISTRATION:
1	REGISTRATION	5000.00
2	DENTAL REGISTRATION	5000.00
3	REGISTRATION/CONSULTATION FOR IVF	60000.00

VACCINES:
1	BCG	12000.00
2	HEPATITIS B VACCINE (ADULT)	28000.00
3	MENNINGITIS	12000.00
4	OPV	4000.00
5	ORAL ROTAVIRUS	12000.00
6	PCV (PNEUMOCCOCAL VACCINE)	35000.00
7	PENTAVALENT	12000.00
8	ROTAVIRUS	15000.00
9	MEASLES	12000.00
10	VITAMIN A	4000.00
11	CERVAREX	39000.00
12	HEPATITIS B VACCINE (CHILD)	15000.00

PROCEDURES:
1	Adhesionlysis of uterus or cervix	80000.00
2	Amuptation and/or joint disarticulation	150000.00
3	Anaesthetic fee Intermediate	20000.00
4	Anaesthetic fee Minor	10000.00
5	Anaesthetic Major ( General Anaesthesia)	35000.00
6	Anal Sphincterectomy	0
7	ANC Booking- booking test, Reg and booking consult	5000.00
8	ANC Booking test-HIV, PCV,VDRL,HBV,HCV,Urinalysis,blood group	0
9	ANC Booking test-HIV, PCV,VDRL,HBV,HCV,Urinalysis,blood group	0
10	Ante Natal Card (6weeks after Delivery Validity)	0
11	Appendicectomy ( Uncomplicated )	70000.00
12	Appendicectomy (complicated )	135000.00
13	Assisted  Breech delivery (Block)	40000.00
14	Assisted delivery -Vacuum delivery	20000.00
15	Augumentation Labour	5000.00
16	Bilateral tube Ligation (Elective)	120000.00
17	BilateralTubal ligation during CS	30000.00
18	Biopsy of  superfial mass	20000.00
19	Biopsy of breast	35000.00
20	Biopsy of prostate	65000.00
21	Biopsy of the bone tumour (Block fee)	50000.00
22	Biopsy Of Tumour Of Abdominal Wall  ( Block fee )	0
23	Birth Before Arrival care	10000.00
24	Birth Certificate	1000.00
25	BLOOD TRANSFUSION (OUTSOURCED) X1 POSITIVE UNIT	44500.00
26	Bone grafting	100000.00
27	Bone marrow biopsy   (Block fee)	50000.00
28	Bowel resection & Anastomosis	250000.00
29	Breast Lump Excision  ( Block fee )	50000.00
30	Bronchooscopy (Block fee)	0
31	Caesarian section (previous Scar) booked case	200000.00
32	Caesarian section (previous Scar) Unbooked case	230000.00
33	Caesarian section(First cs or without previous Scar) Booked	180000.00
34	Caesarian section(First cs or without previous scar) unbooked	200000.00
35	Cardiotocography ( CTG)	0
36	Catheterisation Of Urinary Bladder + Urine Bag	3000.00
37	Cautherization	0
38	Certificate of medical fitness(Excluding Relevant Test)	5000.00
39	Cervical Circlage insertion Surgery	50000.00
40	Cervical Circlage removal	10000.00
41	Cervical polypectomy	200000.00
42	Cervical repair	40000.00
43	Cholecystectomy	0
44	Circumcision Of Male Baby(Local)	7500.00
45	Circumcision Of Male Baby(Plastible)	5000.00
46	Closed reduction only	50000.00
47	Consultation after 1week	0
48	Correction of Duputyren Contracture	0
49	Crutches/Walking frame	0
50	Cystourethroscopy	120000.00
51	Death Certificate	4000.00
52	Double bed ward - (Private)	8000.00
53	Drainage of Anal Abscess	30000.00
54	Drainage of Septic arthritis (Block fee)	70000.00
55	Drainage of whitlow ( Block fee )	5000.00
56	Ear Piercing For Female Baby	2500.00
57	Ectopic Pregnancy	150000.00
58	Emmergency Consultation	0
59	Episiotomy	10000.00
60	EUA	35000.00
61	Evacuation of retained product of conception	20000.00
62	Exchange Blood Transfussion (Rh +Ve, Inclusive Of Materials)	20000.00
63	Exchange Blood Transfussion (Rh -Ve, Inclusive Of Materials)	20000.00
64	Excison of intrascrotal mass	90000.00
65	Family Card (2yrs Duration)	0
66	Fibroid Surgery	280000.00
67	Fistula - in - ano	180000.00
68	foot/Ankle cast	30000.00
69	Fore arm cast only	30000.00
70	Ganglion Excision	60000.00
71	Gastric Lavage	15000.00
72	Gastroduodenoscopy (Block fee)	0
73	General  ward (3 beds and more) per night	3000.00
74	General Consultation (covers 1week)	1000.00
75	Gynaecology	2000.00
76	Haemorriodectomy	120000.00
77	Hand/Wrist cast only	30000.00
78	Herniorrhaphy ( Complicated or recurrent hernier)	0
79	Herniorrhaphy ( Normal uncomplicated hernier)	80000.00
80	Hydrocelectomy (Bilateral (Minor)	100000.00
81	Hydrocelectomy (Unilateral (Minor)	60000.00
82	Hydrointubation	400000.00
83	Hyperglycaemia but consciouse	25000.00
84	Hypertension severe	25000.00
85	Hysterectomy	250000.00
86	Hysteroscopy	0
87	Incision & Drainage	5000.00
88	Incubator	25000.00
89	Incubator Care Per Day	25000.00
90	Induction of Labour	8000.00
91	Ingrowing Toe nail Excision  ( Block fee )	30000.00
92	Injection Sclerotherapy Of Varicose Veins ( Block fee )	0
93	Insertion of IUCD	6500.00
94	Intensive Care ward for critical patient	10000.00
95	Intensive Care ward for non critical patient	0
96	Intestinal Obstruction with resection	250000.00
97	Intestinal Obstruction without resection	200000.00
98	Intra articular injection excluding drug	5000.00
99	Joint Aspiration (Block fee)	5000.00
100	Keloid Excision (Block fee)	50000.00
101	Knee /Ankle brace	0
102	Knee Effusion Tap	2500.00
103	Labour (woman in labour)	10000.00
104	Laparatomy	150000.00
105	Laparoscopy & Dye test	0
106	Leg/Knee cast	35000.00
107	Lipoma excision  (Block fee)	30000.00
108	Lumbar Puncture	3000.00
109	Major I&D ( Block fee )	30000.00
110	Major I&D ( Block fee )	30000.00
111	Major Woiund Debridement (<18%)	100000.00
112	Major Wound Debridement (>18%)	50000.00
113	Major Wound Dressing / Day	1000.00
114	Marsupialization	50000.00
115	Medical Care for critically ill of coma, tetenus	7500.00
116	Medical Care Per Day	2500.00
117	Medical Report	3000.00
118	Minimum Non-refundable Admission Deposit	10000.00
119	Minor Debridement Of Burns   ( Block fee )	0
120	Minor wound Debridement	10000.00
121	Minor Wound Dressing	750.00
122	Moderately ill (Normal)	10000.00
123	Multiple Delivery (Booked Patient)	35000.00
124	Multiple Delivery (Unbooked Patient)	40000.00
125	Myomectomy (Fibroid Surgery)	280000.00
126	Nasal Packing	10000.00
127	Nebulisation +Drug (Out patient)	2000.00
128	Neck Collar (Hard)	0
129	Neck Collar (Soft)	0
130	Nephrectomy	250000.00
131	Non refundable admission deposit	10000.00
132	Normal Delivery (Booked Patient)	25000.00
133	Normal Delivery (Unbooked Patient)	30000.00
134	NURSING CARE PER DAY	5000.00
135	Oesophagoscopy (Block fee)	0
136	Orchidectomy/Orchidopexy (Bilateral)	90000.00
137	Orchidectomy/Orchidopexy (unilateral)	50000.00
138	ORIF + Implant (Hand or Foot)	360000.00
139	ORIF +Implant ( Major bone )	260000.00
140	Ovarectomy	150000.00
141	OVARIAN CYST CYSTECTOMY	350000.00
142	Oxygen Therapy Per hour	1000.00
143	PAP SMEAR (Procedure + Cytology)	75000.00
144	Phototherapy Per Day	10000.00
145	Physiotherapy Service / Session per day	10000.00
146	POP APPLICATION	40000.00
147	Proctoscopy (Block fee)	0
148	Prostate Biopsy	70000.00
149	Prostatectomy	250000.00
150	Radical mastectomy	270000.00
151	REFERRAL LETTER	0
152	Release Of Chordae  (Block fee)	0
153	Removal Impacted Faces	10000.00
154	Removal of Implant	180000.00
155	Removal Of IUCD (No  General Anaesthesia)	5000.00
156	Repair of 3rd degree tear  (Block fee)	40000.00
157	Repair of bowel perforation	150000.00
158	Repair of minor vaginal laceration ( 2nd degree)	10000.00
159	Repair of minor vaginal laceration ( 2nd degree) (Block fee)	10000.00
160	Repair Of Ruptured Uterus	200000.00
161	Repair of Third degree tear	40000.00
162	Report of medical fitness(Excluding Relevant Test)	3000.00
163	SALPHINGECTOMY/OOPHORECTOMY	200000.00
164	Severely ill	30000.00
165	Sigmoidoscopy (Block fee)	0
166	Simple mastectomy + Histology	240000.00
167	SINGLE BED - PRIVATE (VIP 1)	20000.00
168	Skin Grafting ( <9% )	0
169	Skin Grafting ( >9% )	0
170	Skin traction	50000.00
171	Small Cyst Excision ( Block fee )	30000.00
172	Specialist Consultation - 1st Visit (O&G, Surgery, Paediatrics)	5000.00
173	Specialist consultation follow up	3000.00
174	Specialist for Rare Specielties(Neuro,Ortho,Cardiothoracic)	0
175	Splenectomy	150000.00
176	Subdural Tap	0
177	Supra pubic cystostomy	80000.00
178	Suprapubic cystectomy (SPC)	80000.00
179	Suturing Of Major Wounds ( 10cm and above)	30.00
180	Suturing Of Simple Laceration  ( Less than 10cm)	20.00
181	Thearter fee Intermediate	15000.00
182	Thearter fee Major	30000.00
183	Thearter fee Minor	5000.00
184	THERAPEUTIC D&C / UTERINE EVACUATION (LEGAL)	150000.00
185	THIGH/HIP CAST	70000.00
186	Thyroidectomy	200000.00
187	TONGUE TIE RELEASE	5000.00
188	Torsion spermatic cord	150000.00
189	Tracheostomy (Block fee)	0
190	Unconsciouse Patient	50000.00
191	upper arm cast only	35000.00
192	Ureteral re-implantation	250000.00
193	Ureteral Repair	200000.00
194	Urethroplasty	250000.00
195	Whole lower limb cast	40000.00
196	whole upper limb	35000.00
197	perioepical xray	3000.00
198	INDUCTION OF LABOUR	400000.00
199	CEASERAN SECTION: Includes Surgery, Admission (For not more than 5 days, Post-OP Drugs)	1200000.00
200	REPEAT CS	850000.00
201	MANUAL VACUUM ASPIRATION (With Anaesthesia)	350000.00
202	MANUAL VACUUM ASPIRATION (Without Anaesthesia)	200000.00
203	HISTOLOGY	45000.00
204	PAP SMEAR	40000.00
205	OPEN SURGERY	1000000.00
206	MYOMECTOMY	1200000.00
207	DIAGNOSTIC HYSTEROSCOPY	400000.00
208	DIAGNOSTIC LAPAROSCOPY	800000.00
209	OPERATIVE HYSTEROSCOPY	800000.00
210	CYST DRAINAGE WITH ANAESTHESIA	250000.00
211	CYST WITHOUT ANAESTHESIA	150000.00
212	ENDOMETRIAL SCRATCHING WITH ANAESTHESIA	350000.00
213	ENDOMETRIAL SCRATCHING WITHOUT ANAESTHESIA	200000.00
214	DIAGNOSTIC LAPARSOCOPY	400000.00
215	LAPAROSCOPIC CYSTECTOMY	1000000.00
216	LAPAROSCOPIC APPENDECTOMY	1000000.00
217	MYOMECTOMY	800000.00
218	HYSTERECTOMY	1000000.00
219	CERVICAL CERCLAGE	450000.00
220	FREEZING OF EMBRYOS (1 Year)	1000000.00
221	FREEZING OF EMBRYOS (<1 Year)	500000.00
222	INTRA-UTERINE INSEMINATION (IUI)	600000.00
223	EPISIORRHAPHY	100000.00
224	SUTURE OF LACERATIONS	30000.00
225	APPENDECTOMY	800000.00
226	WOUND DRESSING	8000.00
227	MEDICAL REPORT	10000.00
228	BIRTH CERTIFICATE	10000.00
229	MEDICAL FITNESS CERTIFICATE	10000.00
230	BONE MARROW ASPIRATION	350000.00
231	BONE MARROW ASPIRATION + TREPHINE BIOPSY (EXCLUSIVE OF HISTOLOGY)	400000.00
232	THEATRE USE	80000.00
233	ANAESTHESIA	70000.00
234	ANAESTHETIST	80000.00
235	BLOOD TRANSFUSION (PATIENT'S DONOR) X1 POSITIVE UNIT	34500.00
236	BLOOD TRANSFUSION (OUTSOURCED) X1 NEGATIVEUNIT	60000.00
237	EAR PIERCING	5000.00
238	OXYGEN ADMINISTRATION (BIG CYLINDER)	22000.00
239	OXYGEN ADMINISTRATION (SMALL CYLINDER)	8000.00
240	PHOTOTHERAPY PER DAY	10000.00
241	INTRA-UTERINE INSEMINATION (IUI)	600000.00
242	SINGLE BED - PRIVATE (VIP 2)	20000.00
243	SINGLE BED - PRIVATE (VIP 3)	20000.00
244	NURSING CARE - PRIVATE WARD	10000.00
245	EUA PROCEDURE	200000.00
246	LUTEAL PHASE SUPPORT DRUGS	500000.00
247	PAP SMEAR AND HPV TESTING	90000.00
248	HPV TESTING	60000.00

DENTAL:
1	3D panoramic radiograph	18000.00
2	currettage	10000.00
3	fissure sealand per tooth	5000.00
4	fluoredation whole mouth	20000.00
5	fluoride varnish	10000.00
6	desensitiation	5000.00
7	3D panorami radiograph	18000.00
8	currettage	10000.00
9	fissure sealant (per tooth)	5000.00
10	fluoridation (whole mouth)	20000.00
11	fluoride varnish	10000.00
12	desensitization	5000.00
13	Dry socket treatment (external extraction)	10000.00
14	incosion and drainage	15000.00
15	apicectomy (excluding the RCT)	40000.00
16	frenectomy by consultant surgeon	75000.00
17	biopsies by consultant	30000.00
18	Inter maxillary mandibular fixation (IMF)	100000.00
19	anaesthetic fee	20000.00
20	intravenous sedation	30000.00
21	dycal lining	1000.00
22	composite filling	15000.00
23	composite build up	25000.00
24	composite splinting	15000.00
25	cervical composite restoration	20000.00
26	GIC RESTORATION	35000.00
27	cuspal grinding	5000.00
28	Fail RCT appointment	10000.00
29	Home bleaching with tray	50000.00
30	Bleachbright home bleach	30000.00
31	Acrylic denture(single tooth)	15000.00
32	additional tooth	7500.00
33	flexible dentures	35000.00
34	additional tooth for flexible	15000.00
35	Lab relining denture	8000.00
36	chairside lining and repair	5000.00
37	full denture lining	25000.00
38	full lower/upper denture	100000.00
39	immediate denture (single tooth)	20000.00
40	additional immediate denture	7500.00
41	lower biteguard	2500.00
42	SCALING/POLISHING	25000.00

IVF DRUGS:
1	ENRIFOL 2mg	10000.00
2	PROGENOVA 2mg (1 Card)	10000.00
3	BUSERELIN 0.5ml	3500.00
4	LUPRODEX 3.75mg	70000.00
5	ZOLADEX 3.6mg	150000.00
6	HUMOG 75iu	13000.00
7	ARGININE	15000.00
8	HUMOG 150iu	35000.00
9	GONAL F  75iu	18000.00
10	MENUPUR 57iu	10200.00
11	MEROFERT 150iu	20000.00
12	HCG 5000iu	25000.00
13	CYCLOGEST (1 Pkt)	25000.00
14	CITROGEST (1 Pkt)	25000.00
15	VASOPRIM (1 Card)	150.00
16	GESTONE (1 Vial)	5000.00
17	OVOFOLIC (1 Pkt by 60)	20000.00
18	OVOFOLIC (By 30)	11000.00
19	PROXEED (1 Pkt)	22000.00
20	MEDFERTIL (1 Bottle)	28000.00
21	FERTILAID MEN (1 Bottle)	18000.00
22	FERTILAID WOMEN (1 Bottle)	15000.00
23	DHEA (1 Bottle)	6500.00
24	VIGOR CHOCOLATE (1 Bar)	2500.00
25	MANIX (1 Capsule)	400.00
26	MENOTROPIN (BLUE) 150iu	28000.00
27	NON SPERMICIDAL CONDOM (1)	8000.00
28	FERTIGAIN	18000.00
29	CEFRORELOC (0.25mg)	18000.00
30	POTENCIATOR (1 Pkt)	15000.00
31	CITRODIOL 2mg (1 Pkt)	10000.00
32	BUSERILIN 0.5ml (Per Dose)	3500.00
33	OCP (1 Card)	1200.00
34	PRIMOLUT N (1 Card)	0
35	ESTRADIOL 2mg	10000.00

FERTILITY SERVICES:
1	SPERM FREEZING (PER VIAL) FOR 6 MONTHS	400000.00
2	SPERM FREEZING (PER VIAL) FOR 1 Year	800000.00
3	EMBRYO FREEZING (6 MONTHS)	800000.00
4	EMBRYO FREEZING (1 Year)	1500000.00
5	EGG FREEZING (6 MONTHS)	700000.00
6	EGG FREEZING (1 Year)	1400000.00
7	IVF REGISTRATION AND CONSULTATION	60000.00
8	IVF (1 CYCLE)	2500000.00
9	IVF (2 CYCLES)	4800000.00
10	IVF (3 CYCLES)	7000000.00
11	SURROGACY	13000000.00
12	FROZEN EMBRYO TRANSFER (FET)	1200000.00
13	IVF (1 CYCLE) WITH DONOR EGGS	3300000.00
14	DONOR EGGS	800000.00
15	IVF (2 CYCLES) WITH DONOR EGGS	5600000.00

CONSUMABLES:
1	ABDOMOP (Per Piece)	400.00
2	BLOOD BAG	6000.00
3	BLOOD GIVING SET	1200.00
4	CANNULA	600.00
5	CORD CLAMP	300.00
6	DISPENSING ENVELOPES	100.00
7	DRIP GIVING SET	800.00
8	FACE MASK	300.00
9	HVS MCS	4500.00
10	I.V FLUIDS 500ml	1500.00
11	LATEX GLOVES (PER PACK)	7000.00
12	LATEX GLOVES (1 PIECE)	200.00
13	MANTOUX TEST	2000.00
14	NEBULIZER (PER SESSION)	5000.00
15	NEEDLE & SYRINGE (2mg, 5mg, 10mg)	250.00
16	OXYGEN (BIG CYLINDER)	22000.00
17	OXYGEN (SMALL CYLINDER)	12000.00
18	PAEDIATRICS FEEDING TUBE (PER ONE)	900.00
19	PLASTER (DURAPHONE WHITE)	1800.00
20	PROCEDURE	2000.00
21	SOLUSET	4500.00
22	SPINAL NEEDLE	3000.00
23	SURGICAL GLOVES (PER PAIR)	1000.00
24	SYRINGE 50mls	3000.00
25	URETHRAL CATHETER (Different sizes)	1500.00
26	URINE BAG	3000.00
27	URINE/SPUTUM/WD SWAB MCS	4500.00
28	DISPOSABLE SPECULUM	500.00
29	SUFRATUL (VASELINE GAUGE)	1000.00
30	PLASTIBEL	900.00
31	VICRYL SUTURE (PER PIECE)	2500.00
32	INSULIN SYRINGE	600.00
33	SPIKE	300.00
34	NITINGALE	3500.00
35	IVF (1L)	3000.00
36	10ml SYRINGE (PER PIECE)	250.00
37	WATER FOR INJECTION	300.00
38	INJECTION WATER (PER PIECE)	300.00
39	NYLON SUTURE (PER PIECE)	1000.00
40	SUBCUTE NEEDLE	500.00
41	HOURLY OXYGEN ADMINISTRATION (PER HOUR)	8000.00
"""
    
    # Parse the data
    current_category = None
    services = []
    
    for line in services_data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Check if it's a category header
        if line.endswith(':'):
            current_category = line[:-1].strip()
            continue
        
        # Parse service line (format: number name amount)
        parts = line.split('\t')
        if len(parts) >= 3:
            try:
                sn = parts[0].strip()
                name = parts[1].strip()
                amount_str = parts[2].strip()
                
                amount = parse_amount(amount_str)
                
                # Skip if amount is 0 or None
                if amount is None or amount == 0:
                    continue
                
                if current_category and name:
                    department = CATEGORY_TO_DEPARTMENT.get(current_category, 'PROCEDURE')
                    service_code = generate_service_code(current_category, name, int(sn))
                    
                    services.append({
                        'department': department,
                        'service_code': service_code,
                        'service_name': name,
                        'amount': amount,
                        'description': f"{current_category} service"
                    })
            except Exception as e:
                print(f"Error parsing line: {line} - {e}")
                continue
    
    # Import services
    stats = {
        'total': len(services),
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    print(f"\nImporting {stats['total']} services...\n")
    
    for service in services:
        try:
            Model = DEPARTMENT_MODELS[service['department']]
            
            # Check if service already exists
            existing = Model.objects.filter(service_code=service['service_code']).first()
            
            if existing:
                existing.service_name = service['service_name']
                existing.amount = service['amount']
                existing.description = service['description']
                existing.is_active = True
                existing.save()
                stats['updated'] += 1
                print(f"  Updated: {service['department']} - {service['service_code']} - {service['service_name']}")
            else:
                Model.objects.create(
                    service_code=service['service_code'],
                    service_name=service['service_name'],
                    amount=service['amount'],
                    description=service['description'],
                    is_active=True
                )
                stats['created'] += 1
                amount_str = f"NGN {service['amount']:,.2f}"
                print(f"  Created: {service['department']} - {service['service_code']} - {service['service_name']} - {amount_str}")
        
        except Exception as e:
            stats['errors'].append(f"{service['service_code']}: {str(e)}")
            stats['skipped'] += 1
            print(f"  ERROR: {service['service_code']} - {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Import Summary")
    print("=" * 60)
    print(f"Total services: {stats['total']}")
    print(f"Created: {stats['created']}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more errors")
    print("=" * 60)


if __name__ == '__main__':
    import_services()

