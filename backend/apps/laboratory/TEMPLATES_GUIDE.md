# Lab Test Templates Guide

## Overview

Lab test templates allow doctors to quickly order common lab test combinations (e.g., "Complete Blood Count", "Liver Function Tests") without having to type each test individually.

## Features

✅ **Pre-configured Test Panels**: Common combinations like CBC, LFT, BMP, etc.  
✅ **Quick Selection**: One-click to apply template to order form  
✅ **Editable**: Doctors can modify tests and clinical indication after applying template  
✅ **Usage Tracking**: Templates track how often they're used  
✅ **Category Organization**: Templates organized by category (Hematology, Chemistry, etc.)  

## How It Works

1. **Doctor opens Lab Order form** in consultation workspace
2. **Clicks "📋 Use Template"** button
3. **Selects a template** from the list
4. **Template auto-fills** the order form with:
   - Test names (comma-separated)
   - Default clinical indication
5. **Doctor can edit** before submitting
6. **Order is created** as normal

## Seeding Common Templates

To populate the database with common lab test templates, run:

```bash
python manage.py seed_lab_templates
```

This will create templates for:
- Complete Blood Count (CBC)
- Liver Function Tests (LFT)
- Basic Metabolic Panel (BMP)
- Comprehensive Metabolic Panel (CMP)
- Lipid Profile
- Thyroid Function Tests
- Renal Function Tests
- Diabetes Panel
- Urine Analysis
- Pregnancy Test
- Malaria Test
- HIV Screening
- Hepatitis Panel
- Blood Group & Crossmatch
- Coagulation Profile

## Creating Custom Templates

Doctors can create custom templates via:
1. **Django Admin**: `/admin/laboratory/labtesttemplate/`
2. **API**: `POST /api/v1/lab-templates/templates/`

### Template Structure

```json
{
  "name": "Complete Blood Count (CBC)",
  "category": "Hematology",
  "description": "Basic blood panel",
  "tests": ["CBC", "Hemoglobin", "Hematocrit", "WBC Count"],
  "default_clinical_indication": "Routine checkup"
}
```

## API Endpoints

- `GET /api/v1/lab-templates/templates/` - List all templates
- `GET /api/v1/lab-templates/templates/{id}/` - Get template details
- `POST /api/v1/lab-templates/templates/` - Create template (Doctor only)
- `POST /api/v1/lab-templates/templates/{id}/use/` - Use template (increments usage count)

## Frontend Integration

Templates are already integrated in `LabInline` component:
- Templates load automatically when order form is opened
- "📋 Use Template" button appears if templates are available
- Template selection populates the order form
- Doctors can edit before submitting

