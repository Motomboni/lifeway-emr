import csv

# Radiology services data
services = [
    ("RAD-XRAY-CHEST-PA", "Chest X-Ray PA", "7500.00", "X-ray imaging of the chest in posteroanterior view"),
    ("RAD-XRAY-CHEST-LAT", "Chest X-Ray Lateral", "7500.00", "X-ray imaging of the chest in lateral view"),
    ("RAD-XRAY-SKULL", "Skull X-Ray", "8500.00", "X-ray imaging of the skull - 2 views"),
    ("RAD-XRAY-ABDOMEN", "Abdominal X-Ray", "8000.00", "X-ray imaging of the abdomen"),
    ("RAD-XRAY-PELVIS", "Pelvic X-Ray", "8500.00", "X-ray imaging of the pelvis"),
    ("RAD-XRAY-SPINE-CERV", "Cervical Spine X-Ray", "9000.00", "X-ray imaging of the cervical spine - 2 views"),
    ("RAD-XRAY-SPINE-THOR", "Thoracic Spine X-Ray", "9500.00", "X-ray imaging of the thoracic spine - 2 views"),
    ("RAD-XRAY-SPINE-LUMB", "Lumbar Spine X-Ray", "10000.00", "X-ray imaging of the lumbar spine - 2 views"),
    ("RAD-XRAY-SHOULDER", "Shoulder X-Ray", "8500.00", "X-ray imaging of the shoulder joint"),
    ("RAD-XRAY-ELBOW", "Elbow X-Ray", "8000.00", "X-ray imaging of the elbow joint"),
    ("RAD-XRAY-WRIST", "Wrist X-Ray", "8000.00", "X-ray imaging of the wrist"),
    ("RAD-XRAY-HAND", "Hand X-Ray", "7500.00", "X-ray imaging of the hand"),
    ("RAD-XRAY-HIP", "Hip X-Ray", "9000.00", "X-ray imaging of the hip joint"),
    ("RAD-XRAY-KNEE", "Knee X-Ray", "8500.00", "X-ray imaging of the knee joint"),
    ("RAD-XRAY-ANKLE", "Ankle X-Ray", "8000.00", "X-ray imaging of the ankle"),
    ("RAD-XRAY-FOOT", "Foot X-Ray", "7500.00", "X-ray imaging of the foot"),
    ("RAD-XRAY-RIBS", "Ribs X-Ray", "9000.00", "X-ray imaging of the ribs"),
    ("RAD-XRAY-FOREARM", "Forearm X-Ray", "8000.00", "X-ray imaging of the forearm"),
    ("RAD-XRAY-LEG", "Leg X-Ray", "8500.00", "X-ray imaging of the leg"),
    ("RAD-XRAY-CLAVICLE", "Clavicle X-Ray", "8000.00", "X-ray imaging of the clavicle"),
    ("RAD-CT-HEAD", "CT Scan Head Plain", "35000.00", "CT scan of the head without contrast"),
    ("RAD-CT-HEAD-CONTRAST", "CT Scan Head with Contrast", "45000.00", "CT scan of the head with IV contrast"),
    ("RAD-CT-BRAIN", "CT Brain Plain", "35000.00", "CT scan of the brain without contrast"),
    ("RAD-CT-CHEST", "CT Scan Chest", "40000.00", "CT scan of the chest"),
    ("RAD-CT-ABDOMEN", "CT Scan Abdomen", "42000.00", "CT scan of the abdomen"),
    ("RAD-CT-PELVIS", "CT Scan Pelvis", "42000.00", "CT scan of the pelvis"),
    ("RAD-CT-ABD-PELVIS", "CT Scan Abdomen & Pelvis", "55000.00", "CT scan of abdomen and pelvis"),
    ("RAD-CT-SPINE-CERV", "CT Scan Cervical Spine", "38000.00", "CT scan of the cervical spine"),
    ("RAD-CT-SPINE-LUMB", "CT Scan Lumbar Spine", "38000.00", "CT scan of the lumbar spine"),
    ("RAD-CT-UROGRAPHY", "CT Urography", "50000.00", "CT scan of the urinary tract with contrast"),
    ("RAD-MRI-BRAIN", "MRI Brain Plain", "65000.00", "MRI scan of the brain without contrast"),
    ("RAD-MRI-BRAIN-CONTRAST", "MRI Brain with Contrast", "85000.00", "MRI scan of the brain with IV contrast"),
    ("RAD-MRI-SPINE-CERV", "MRI Cervical Spine", "70000.00", "MRI scan of the cervical spine"),
    ("RAD-MRI-SPINE-THOR", "MRI Thoracic Spine", "70000.00", "MRI scan of the thoracic spine"),
    ("RAD-MRI-SPINE-LUMB", "MRI Lumbar Spine", "70000.00", "MRI scan of the lumbar spine"),
    ("RAD-MRI-SPINE-WHOLE", "MRI Whole Spine", "120000.00", "MRI scan of the entire spine"),
    ("RAD-MRI-SHOULDER", "MRI Shoulder Joint", "60000.00", "MRI scan of the shoulder joint"),
    ("RAD-MRI-KNEE", "MRI Knee Joint", "60000.00", "MRI scan of the knee joint"),
    ("RAD-MRI-ANKLE", "MRI Ankle Joint", "55000.00", "MRI scan of the ankle joint"),
    ("RAD-MRI-WRIST", "MRI Wrist Joint", "55000.00", "MRI scan of the wrist joint"),
    ("RAD-MRI-PELVIS", "MRI Pelvis", "65000.00", "MRI scan of the pelvis"),
    ("RAD-MRI-ABDOMEN", "MRI Abdomen", "65000.00", "MRI scan of the abdomen"),
    ("RAD-US-ABDOMEN", "Ultrasound Abdomen", "12000.00", "Abdominal ultrasound scan"),
    ("RAD-US-PELVIS", "Ultrasound Pelvis", "12000.00", "Pelvic ultrasound scan"),
    ("RAD-US-OB-FIRST", "Obstetric Ultrasound (1st Trimester)", "15000.00", "First trimester pregnancy ultrasound"),
    ("RAD-US-OB-SECOND", "Obstetric Ultrasound (2nd Trimester)", "18000.00", "Second trimester pregnancy ultrasound with anatomy survey"),
    ("RAD-US-OB-THIRD", "Obstetric Ultrasound (3rd Trimester)", "18000.00", "Third trimester pregnancy ultrasound"),
    ("RAD-US-TVS", "Transvaginal Ultrasound", "15000.00", "Transvaginal ultrasound scan"),
    ("RAD-US-BREAST", "Breast Ultrasound", "13000.00", "Ultrasound scan of the breast"),
    ("RAD-US-THYROID", "Thyroid Ultrasound", "12000.00", "Ultrasound scan of the thyroid gland"),
    ("RAD-US-NECK", "Neck Ultrasound", "12000.00", "Ultrasound scan of the neck"),
    ("RAD-US-SCROTAL", "Scrotal Ultrasound", "12000.00", "Ultrasound scan of the scrotum"),
    ("RAD-US-PROSTATE", "Prostate Ultrasound (TRUS)", "15000.00", "Transrectal ultrasound of the prostate"),
    ("RAD-US-RENAL", "Renal Ultrasound", "12000.00", "Ultrasound scan of the kidneys"),
    ("RAD-US-KUB", "Ultrasound KUB", "13000.00", "Ultrasound scan of kidneys ureters and bladder"),
    ("RAD-US-SOFT-TISSUE", "Soft Tissue Ultrasound", "10000.00", "Ultrasound scan of soft tissues"),
    ("RAD-US-MSK", "Musculoskeletal Ultrasound", "12000.00", "Ultrasound scan of muscles tendons and joints"),
    ("RAD-US-DOPPLER-CAROTID", "Carotid Doppler Ultrasound", "18000.00", "Doppler ultrasound of carotid arteries"),
    ("RAD-US-DOPPLER-DVT", "Lower Limb Doppler (DVT)", "18000.00", "Doppler ultrasound for deep vein thrombosis"),
    ("RAD-US-ECHO", "Echocardiography", "25000.00", "Ultrasound scan of the heart"),
    ("RAD-MAMMO-BILATERAL", "Mammography Bilateral", "18000.00", "Mammogram of both breasts"),
    ("RAD-MAMMO-UNILATERAL", "Mammography Unilateral", "12000.00", "Mammogram of one breast"),
    ("RAD-MAMMO-DIAGNOSTIC", "Diagnostic Mammography", "20000.00", "Diagnostic mammography with targeted views"),
    ("RAD-BARIUM-SWALLOW", "Barium Swallow", "20000.00", "Fluoroscopic study of the esophagus with barium"),
    ("RAD-BARIUM-MEAL", "Barium Meal", "22000.00", "Fluoroscopic study of stomach and duodenum with barium"),
    ("RAD-BARIUM-ENEMA", "Barium Enema", "25000.00", "Fluoroscopic study of the colon with barium"),
    ("RAD-IVU", "Intravenous Urography (IVU)", "28000.00", "X-ray study of the urinary system with IV contrast"),
    ("RAD-HSG", "Hysterosalpingography (HSG)", "25000.00", "X-ray study of the uterus and fallopian tubes"),
    ("RAD-FLUORO-GI", "Fluoroscopy GI Study", "20000.00", "Fluoroscopic examination of gastrointestinal tract"),
    ("RAD-BONE-SCAN", "Bone Scan", "45000.00", "Nuclear medicine bone scan"),
    ("RAD-DEXA", "DEXA Bone Density Scan", "18000.00", "Dual-energy X-ray absorptiometry for bone density"),
    ("RAD-PANORAMIC", "Panoramic Dental X-Ray", "8000.00", "Panoramic X-ray of the jaw and teeth"),
    ("RAD-CT-ANGIOGRAPHY", "CT Angiography", "55000.00", "CT scan of blood vessels with contrast"),
    ("RAD-MRI-ANGIOGRAPHY", "MR Angiography", "75000.00", "MRI scan of blood vessels"),
    ("RAD-XRAY-SINUS", "Paranasal Sinuses X-Ray", "8000.00", "X-ray imaging of the paranasal sinuses"),
    ("RAD-XRAY-FACIAL", "Facial Bones X-Ray", "9000.00", "X-ray imaging of facial bones"),
    ("RAD-CT-SINUS", "CT Scan Paranasal Sinuses", "32000.00", "CT scan of the paranasal sinuses"),
    ("RAD-US-GUIDED-BIOPSY", "Ultrasound Guided Biopsy", "35000.00", "Tissue biopsy under ultrasound guidance"),
    ("RAD-US-GUIDED-ASPIRATION", "Ultrasound Guided Aspiration", "28000.00", "Fluid aspiration under ultrasound guidance"),
]

# Write to CSV
with open('radiology_services.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    
    # Write header
    writer.writerow([
        'department', 'service_code', 'name', 'amount', 'description', 
        'category', 'workflow_type', 'requires_visit', 'requires_consultation', 
        'auto_bill', 'bill_timing', 'allowed_roles', 'is_active'
    ])
    
    # Write services
    for service_code, name, amount, description in services:
        writer.writerow([
            'RADIOLOGY', service_code, name, amount, description,
            'RADIOLOGY', 'RADIOLOGY_STUDY', 'TRUE', 'TRUE',
            'TRUE', 'BEFORE', 'DOCTOR', 'TRUE'
        ])

print(f"Generated radiology_services.csv with {len(services)} services")

