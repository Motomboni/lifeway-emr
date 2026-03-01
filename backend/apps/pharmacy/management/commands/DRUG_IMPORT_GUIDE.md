# Drug Catalog Import Guide

Import drugs from a CSV or Excel file into the Drug Catalog.

## Supported formats

- **CSV** (`.csv`) – comma or semicolon separated
- **Excel** (`.xlsx`, `.xls`)

## Usage (remote EMR / Docker)

### 1. Prepare your file

Create a CSV or Excel file with drugs. Example CSV:

```csv
name,generic_name,drug_code,drug_class,dosage_forms,common_dosages,cost_price,sales_price,description,current_stock,unit,reorder_level
Paracetamol,Acetaminophen,PARA-500,Analgesic,Tablet,500mg,50.00,100.00,Pain reliever,500,tablets,50
Amoxicillin,Amoxicillin,AMOX-250,Antibiotic,Capsule,250mg 500mg,80.00,150.00,Antibiotic,200,capsules,30
```

### 2. Copy file to server

Upload the file to your server (e.g. via SCP, SFTP, or drag-and-drop):

```bash
scp drugs.csv user@your-server:~/lifeway-emr/
```

### 3. Run import in Docker

**Option A – File in project folder (recommended)**

If `drugs.csv` is in your project root (e.g. `~/lifeway-emr/drugs.csv`), run with a one-off container and volume mount:

```bash
cd ~/lifeway-emr
docker compose -f docker-compose.standalone.yml run --rm \
  -v $(pwd)/drugs.csv:/app/drugs.csv \
  app python backend/manage.py import_drug_catalog /app/drugs.csv
```

**Option B – File already copied into container**

```bash
docker cp drugs.csv lifeway-emr-app-1:/app/drugs.csv
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /app/drugs.csv
```

**Option C – Exec with file on host path**

If your compose mounts the project directory, use the path inside the container that maps to it.

```bash
# Dry run (preview without saving)
docker compose -f docker-compose.standalone.yml run --rm -v $(pwd)/drugs.csv:/app/drugs.csv app python backend/manage.py import_drug_catalog /app/drugs.csv --dry-run

# Actual import
docker compose -f docker-compose.standalone.yml run --rm -v $(pwd)/drugs.csv:/app/drugs.csv app python backend/manage.py import_drug_catalog /app/drugs.csv

# With inventory (creates stock records)
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /path/to/drugs.csv --with-inventory

# Update existing drugs by name
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /path/to/drugs.csv --update

# Specify user (default: first superuser)
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /path/to/drugs.csv --user Ezealisiobi
```

### 4. If file is inside the container

If you copied the file into the app container or mounted volume:

```bash
# Copy into container first (from host)
docker cp drugs.csv lifeway-emr-app-1:/app/drugs.csv

# Then run
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /app/drugs.csv
```

### 5. Using a volume mount

Add a volume in `docker-compose.standalone.yml` to access files from host:

```yaml
app:
  volumes:
    - media_data:/app/backend/media
    - ./uploads:/app/uploads  # optional: mount ./uploads on host
```

Then place `drugs.csv` in `./uploads/` and run:

```bash
docker compose -f docker-compose.standalone.yml exec app python backend/manage.py import_drug_catalog /app/uploads/drugs.csv
```

## Column mappings

| Column (any of) | Description |
|-----------------|-------------|
| name, drug name | **Required.** Drug name |
| generic_name, generic | Generic / active ingredient |
| drug_code, code, ndc | Unique code |
| drug_class, class | e.g. Antibiotic, Analgesic |
| dosage_forms, form | e.g. Tablet, Capsule |
| common_dosages | e.g. 250mg, 500mg |
| cost_price, cost | Purchase price |
| sales_price, price | Selling price |
| description | Notes |
| current_stock, stock | For `--with-inventory` |
| unit | e.g. tablets, units |
| reorder_level | For `--with-inventory` |
| is_active, active | true/false (default: true) |

## Sample template

A sample `drugs_import_template.csv` is in this folder. Copy and edit it for your list.
