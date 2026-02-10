# Radiology Test Templates Guide

## Overview

Radiology test templates allow doctors to quickly order common radiology studies (e.g., "Chest X-Ray", "CT Head", "Abdominal Ultrasound") without having to manually enter all the details each time.

## Features

✅ **Pre-configured Studies**: Common studies like Chest X-Ray, CT Head, etc.  
✅ **Quick Selection**: One-click to apply template to order form  
✅ **Editable**: Doctors can modify details after applying template  
✅ **Usage Tracking**: Templates track how often they're used  
✅ **Category Organization**: Templates organized by imaging type (X-Ray, CT, Ultrasound, MRI)  

## How It Works

1. **Doctor opens Radiology Order form** in consultation workspace
2. **Clicks "📋 Use Template"** button
3. **Selects a template** from the list
4. **Template auto-fills** the order form with:
   - Imaging type
   - Body part
   - Study code
   - Default clinical indication
   - Default priority
5. **Doctor can edit** before submitting
6. **Order is created** as normal

## Seeding Common Templates

To populate the database with common radiology study templates, run:

```bash
python manage.py seed_radiology_templates
```

This will create templates for:

### X-Ray Studies
- Chest X-Ray (PA)
- Chest X-Ray (AP)
- Abdominal X-Ray
- Pelvis X-Ray
- Lumbar Spine X-Ray
- Cervical Spine X-Ray
- Skull X-Ray
- Extremity X-Ray

### CT Scans
- CT Head
- CT Chest
- CT Abdomen
- CT Pelvis

### Ultrasound Studies
- Abdominal Ultrasound
- Pelvic Ultrasound
- Obstetric Ultrasound
- Transvaginal Ultrasound
- Renal Ultrasound
- Prostate Ultrasound

### MRI Studies
- MRI Brain
- MRI Spine
- MRI Joint

## Creating Custom Templates

Doctors can create custom templates via:
1. **Django Admin**: `/admin/radiology/radiologytesttemplate/`
2. **API**: `POST /api/v1/radiology-templates/templates/`

### Template Structure

```json
{
  "name": "Chest X-Ray (PA)",
  "category": "X-Ray",
  "description": "Posteroanterior chest X-ray",
  "imaging_type": "XRAY",
  "body_part": "Chest",
  "study_code": "CXR-PA",
  "default_clinical_indication": "Chest pain / Respiratory symptoms",
  "default_priority": "ROUTINE"
}
```

## API Endpoints

- `GET /api/v1/radiology-templates/templates/` - List all templates
- `GET /api/v1/radiology-templates/templates/{id}/` - Get template details
- `POST /api/v1/radiology-templates/templates/` - Create template (Doctor only)
- `POST /api/v1/radiology-templates/templates/{id}/use/` - Use template (increments usage count)

## Frontend Integration

Templates are already integrated in `RadiologyInline` component:
- Templates load automatically when order form is opened
- "📋 Use Template" button appears if templates are available
- Template selection populates the order form
- Doctors can edit before submitting

