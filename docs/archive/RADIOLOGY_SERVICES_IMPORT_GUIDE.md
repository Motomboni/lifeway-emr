# Radiology Services Import Guide

## 📋 Overview
This guide explains how to import the comprehensive radiology services catalog into your EMR system.

## 📂 File Location
**File**: `backend/radiology_services.csv`

## 📊 Services Included (82 Total)

### X-Ray Services (21)
- **Chest**: PA, Lateral
- **Spine**: Cervical, Thoracic, Lumbar
- **Extremities**: Shoulder, Elbow, Wrist, Hand, Hip, Knee, Ankle, Foot, Forearm, Leg
- **Other**: Skull, Abdomen, Pelvis, Ribs, Clavicle, Sinuses, Facial Bones
- **Dental**: Panoramic

**Price Range**: ₦7,500 - ₦10,000

### CT Scan Services (11)
- **Head/Brain**: Plain, with Contrast
- **Body**: Chest, Abdomen, Pelvis, Abdomen & Pelvis
- **Spine**: Cervical, Lumbar
- **Special**: CT Urography, CT Angiography, CT Sinuses

**Price Range**: ₦32,000 - ₦55,000

### MRI Scan Services (12)
- **Brain**: Plain, with Contrast
- **Spine**: Cervical, Thoracic, Lumbar, Whole Spine
- **Joints**: Shoulder, Knee, Ankle, Wrist
- **Body**: Pelvis, Abdomen
- **Special**: MR Angiography

**Price Range**: ₦55,000 - ₦120,000

### Ultrasound Services (18)
- **General**: Abdomen, Pelvis, Breast, Thyroid, Neck
- **Obstetric**: 1st, 2nd, 3rd Trimester
- **Gynecological**: Transvaginal
- **Urological**: Renal, KUB, Scrotal, Prostate
- **Vascular**: Carotid Doppler, DVT Doppler
- **Cardiac**: Echocardiography
- **Other**: Soft Tissue, Musculoskeletal

**Price Range**: ₦10,000 - ₦25,000

### Mammography Services (3)
- Bilateral, Unilateral, Diagnostic

**Price Range**: ₦12,000 - ₦20,000

### Fluoroscopy/Contrast Studies (6)
- Barium Swallow, Meal, Enema
- IVU (Intravenous Urography)
- HSG (Hysterosalpingography)
- General GI Fluoroscopy

**Price Range**: ₦20,000 - ₦28,000

### Special Procedures (11)
- Bone Scan (Nuclear Medicine)
- DEXA Bone Density Scan
- Ultrasound Guided Biopsy
- Ultrasound Guided Aspiration

**Price Range**: ₦18,000 - ₦45,000

## 🚀 How to Import

### Step 1: Navigate to Backend Directory
```bash
cd "C:\Users\Damian Motomboni\Desktop\Modern EMR\backend"
```

### Step 2: Run Import Command
```bash
python manage.py import_service_catalog radiology_services.csv
```

### Step 3: Verify Import
```bash
python manage.py shell -c "from apps.billing.service_catalog_models import ServiceCatalog; print('Radiology Services:', ServiceCatalog.objects.filter(department='RADIOLOGY').count())"
```

**Expected Result**: Should show 82 radiology services (or 83 if you kept the existing one)

## 📝 CSV Format Details

Each service has the following fields:
- **Department**: RADIOLOGY
- **Service Code**: Unique identifier (e.g., RAD-XRAY-CHEST-PA)
- **Service Name**: Descriptive name shown to users
- **Amount**: Price in Naira
- **Description**: Detailed description of the service
- **Category**: RADIOLOGY
- **Workflow Type**: RADIOLOGY_STUDY
- **Requires Visit**: TRUE (all radiology services require a visit)
- **Requires Consultation**: TRUE (requires doctor's order)
- **Auto Bill**: TRUE (automatically creates billing line item)
- **Bill Timing**: BEFORE (bill before service)
- **Allowed Roles**: DOCTOR (only doctors can order)
- **Is Active**: TRUE (service is active and available)

## ✅ Post-Import Verification

### 1. Check via Admin Panel
- Navigate to: `http://localhost:3002/admin/billing/servicecatalog/`
- Filter by Department: RADIOLOGY
- Verify all 82 services are listed

### 2. Test in Frontend
1. Login as a doctor
2. Navigate to any patient consultation
3. Click "🔍 Order Services from Catalog"
4. Search for "X-Ray", "CT", "MRI", "Ultrasound", etc.
5. Verify services appear in search results

### 3. Test Complete Workflow
1. Order a radiology service (e.g., "Chest X-Ray PA")
2. **Consultation**: Service appears in RadiologyInline section
3. **Billing**: Service appears in Billing & Payments → Charges → Radiology section
4. **Radiology Tech**: Order appears in Radiology Orders page
5. **Report**: Tech can post report
6. **Doctor**: Can view report in consultation workspace

## 💡 Customization Tips

### Adjusting Prices
Edit the CSV file and change the `Amount` column values. Prices are in Naira.

### Adding More Services
Add new rows following the same format. Ensure:
- Unique `Service Code` (use RAD- prefix)
- `Department` = RADIOLOGY
- `Workflow Type` = RADIOLOGY_STUDY
- `Requires Visit` = TRUE
- `Requires Consultation` = TRUE

### Deactivating Services
Change `Is Active` from TRUE to FALSE for services you don't want to offer.

## 📊 Pricing Guidelines

The prices in the CSV are based on typical Nigerian private hospital rates:

- **X-Rays**: ₦7,500 - ₦10,000
- **Ultrasound**: ₦10,000 - ₦25,000
- **CT Scans**: ₦32,000 - ₦55,000
- **MRI Scans**: ₦55,000 - ₦120,000
- **Special Procedures**: ₦18,000 - ₦45,000

**Note**: Adjust these prices according to your facility's rates and location.

## 🔄 Re-importing / Updating

If you need to update prices or details:

1. **Modify the CSV** with your changes
2. **Re-run the import** command
3. The system will **update existing services** if the Service Code matches

## 🎯 Next Steps

After import:
1. ✅ Verify all services imported correctly
2. ✅ Adjust prices if needed
3. ✅ Test ordering workflow
4. ✅ Test radiology tech reporting workflow
5. ✅ Test billing integration
6. ✅ Train staff on using the system

## 🆘 Troubleshooting

### Import Fails
- Check CSV format matches template
- Ensure no duplicate Service Codes
- Verify all required fields are present

### Services Don't Appear in Search
- Check `Is Active` = TRUE
- Verify `Department` = RADIOLOGY
- Clear browser cache and refresh

### Can't Order Service
- Ensure user is logged in as DOCTOR
- Verify visit is OPEN
- Check consultation exists

## 📞 Support

For issues or questions, refer to:
- `SERVICE_CATALOG_WORKFLOW_GUIDE.md`
- `SERVICE_CATALOG_IMPORT_GUIDE.md`
- `RADIOLOGY_SERVICE_CATALOG_FIX.md`

