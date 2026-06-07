# LMC Migration Scripts (Scaffold)

This folder contains a CSV-driven migration scaffold for moving legacy LMC MSSQL data into the Django/PostgreSQL EMR.

## Files

- `settings.py` - runtime configuration and paths
- `mapping.py` - parse/filter column mapping CSV rows
- `extract.py` - extract legacy rows (stub)
- `transform.py` - transform rows by mapping rules (stub + examples)
- `load.py` - load rows into Django models (stub)
- `reconcile.py` - compare source/target counts and write report
- `run_pipeline.py` - orchestration entrypoint

## Mapping input

Default mapping file:

- `docs/migration/lmc-column-mapping-status.csv`

Expected minimum columns:

- `source_table`
- `source_column`
- `target_model`
- `target_field`
- `transform_rule`
- `required_default`
- `validation_owner`
- `mapping_status`
- `notes`

## Usage

From `backend/`:

```bash
python scripts/migrate_lmc/run_pipeline.py --dry-run
```

File-based extraction from legacy SQL dump (no MSSQL server required):

```bash
python scripts/migrate_lmc/run_pipeline.py --dry-run --status proposed --source file --sql-file ../LMC.sql
```

CSV-based extraction from exported table files (no MSSQL server required):

```bash
python scripts/migrate_lmc/run_pipeline.py --dry-run --status proposed --source csv --csv-dir ../tmp/lmc_csv
```

Validate CSV headers + row counts only (no migration run):

```bash
python scripts/migrate_lmc/run_pipeline.py --source csv --csv-dir ../tmp/lmc_csv --validate-csv-only
```

Run only confirmed mappings:

```bash
python scripts/migrate_lmc/run_pipeline.py --status confirmed --dry-run
```

Override mapping file:

```bash
python scripts/migrate_lmc/run_pipeline.py --mapping-file ../docs/migration/lmc-column-mapping-status.csv
```

## Important

This scaffold now includes:

- **live extraction** via `pyodbc` for first vertical-slice tables
- **file-based extraction** by parsing `INSERT INTO ... VALUES ...` from `LMC.sql`
- **csv-based extraction** from per-table CSV files

Supported first vertical-slice tables (load order):

- `tblUsers` → `User` (staff)
- `tblOutPatientRecord` → `Patient`
- `tblPatientVisits` → `Visit` (OP narrative columns also populate `Consultation` when present)
- `tblPatientPayment` → `Payment` (visit resolved by patient + nearest payment date; requires `migration_receptionist`)
- `tblTempReceipt` → `VisitCharge` (receipt lines from `tblTempReceipt` + `tblReceiptGrid`; category inferred from service text)
- `tblLabRequest` / `tblLabResult` → `LabOrder` / `LabResult`
- `tblRadRequest` / `tblRadResult` → `RadiologyRequest` (results update `report` when present)
- `tblVitalSign` → `VitalSigns`
- `tblOPDAppointment` → `Appointment`
- `tblPhamDrugItem` → `Drug` (catalog)
- `tblDrugPresItems` → `Prescription` (one row per line; after drug catalog; `is_emergency=True` for legacy import)

LIFEWAY automation: from repo root, `docker compose -f docker-compose.lifeway-mssql.yml up -d`, then
`python backend/scripts/migrate_lifeway/restore_export.py` exports CSVs to `tmp/lifeway_csv/` using `docker exec` + `sqlcmd` (no SQL Server ODBC drivers required on the host). The first container boot can take several minutes; healthcheck uses `sqlcmd -C` (trust server certificate).
Before loading appointments or patient payments, run `python manage.py ensure_migration_seed_users` (creates `migration_doctor`, `migration_pharmacist`, and `migration_receptionist`).

Optional env for loaders: `LEGACY_PATIENT_ID_PREFIX` (default `LIFEWAYLEG`), live ODBC `LEGACY_DB_VENDOR=lifeway` for column/PK remapping in `extract.py`.

SQLite: for large runs, `setup_django` sets `PRAGMA busy_timeout` (override with `MIGRATE_LMC_SQLITE_BUSY_TIMEOUT_MS`, default `120000`) plus WAL — prefer PostgreSQL for production-sized imports.

All other mapped tables are still skipped (returned empty) until expanded.

For CSV mode, expected filenames inside `--csv-dir` match `extract.MIGRATION_TABLE_ORDER`, for example:

- `tblUsers.csv`
- `tblOutPatientRecord.csv`
- `tblPatientVisits.csv`
- `tblPatientPayment.csv`
- `tblTempReceipt.csv`
- `tblLabRequest.csv`, `tblLabResult.csv`, `tblRadRequest.csv`, `tblRadResult.csv`, `tblVitalSign.csv`
- `tblOPDAppointment.csv`
- `tblPhamDrugItem.csv`
- `tblDrugPresItems.csv`

## SQL Server connection environment

Set either:

- `LMC_MSSQL_CONN_STR` (full ODBC connection string), or
- `LMC_MSSQL_SERVER` + `LMC_MSSQL_DATABASE` (+ optional auth vars below)

Optional vars:

- `LMC_MSSQL_DRIVER` (default: `ODBC Driver 17 for SQL Server`)
- `LMC_MSSQL_USERNAME`
- `LMC_MSSQL_PASSWORD`
- `LMC_MSSQL_TRUSTED_CONNECTION` (default: `true`)

You also need:

```bash
pip install pyodbc
```

