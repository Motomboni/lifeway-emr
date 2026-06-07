from __future__ import annotations

import logging
import os
import re
import csv
from pathlib import Path
from typing import Any

from .lifeway_appointment_sql import LIFEWAY_OPD_APPOINTMENT_SELECT_BODY
from .lifeway_patient_visits_sql import LIFEWAY_PATIENT_VISITS_SELECT_BODY
from .lifeway_patient_payment_sql import LIFEWAY_PATIENT_PAYMENT_SELECT_BODY
from .lifeway_temp_receipt_sql import LIFEWAY_TEMP_RECEIPT_SELECT_BODY
from .lifeway_drug_prescription_lines_sql import LIFEWAY_DRUG_PRESCRIPTION_LINES_SELECT_BODY
from .lifeway_vital_sign_sql import LIFEWAY_VITAL_SIGN_SELECT_BODY
from .lifeway_lab_request_sql import LIFEWAY_LAB_REQUEST_SELECT_BODY
from .lifeway_lab_result_sql import LIFEWAY_LAB_RESULT_SELECT_BODY
from .lifeway_radiology_request_sql import LIFEWAY_RAD_REQUEST_SELECT_BODY
from .lifeway_radiology_result_sql import LIFEWAY_RAD_RESULT_SELECT_BODY
from .mapping import MappingRow, group_rows_by_source_table

logger = logging.getLogger(__name__)


def _normalize_csv_cell(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.strip().upper() == "NULL":
        return None
    return value


# Extraction and downstream load order: staff first (for legacy UserID -> Django PK), then clinical slice.
MIGRATION_TABLE_ORDER: tuple[str, ...] = (
    "tblUsers",
    "tblOutPatientRecord",
    "tblPatientVisits",
    "tblPatientPayment",
    "tblTempReceipt",
    "tblLabRequest",
    "tblLabResult",
    "tblRadRequest",
    "tblRadResult",
    "tblVitalSign",
    "tblOPDAppointment",
    "tblPhamDrugItem",
    "tblDrugPresItems",
)
VERTICAL_SLICE_TABLES = frozenset(MIGRATION_TABLE_ORDER)

# CSV columns for tblUsers export (see restore_export / lmc-csv-export-queries); not all appear in mapping CSV.
STAFF_USER_EXPORT_COLUMNS: tuple[str, ...] = (
    "UserID",
    "UserName",
    "FullName",
    "Description",
    "Active",
    "Designation",
    "StaffCategory",
    "CanConsult",
)

# Used by run_pipeline reconciliation so source row counts align with loaded_counts keys.
SOURCE_TABLE_TO_TARGET_MODEL: dict[str, str] = {
    "tblUsers": "apps.users.User",
    "tblOutPatientRecord": "apps.patients.Patient",
    "tblPatientVisits": "apps.visits.Visit",
    "tblPatientPayment": "apps.billing.Payment",
    "tblTempReceipt": "apps.billing.VisitCharge",
    "tblLabRequest": "apps.laboratory.LabOrder",
    "tblLabResult": "apps.laboratory.LabResult",
    "tblRadRequest": "apps.radiology.RadiologyRequest",
    "tblRadResult": "apps.radiology.RadiologyRequest",
    "tblVitalSign": "apps.clinical.VitalSigns",
    "tblOPDAppointment": "apps.appointments.Appointment",
    "tblPhamDrugItem": "apps.pharmacy.Drug",
    "tblDrugPresItems": "apps.pharmacy.Prescription",
}

PRIMARY_KEY_BY_TABLE = {
    "tblUsers": "UserID",
    "tblOutPatientRecord": "PatientID",
    "tblPatientVisits": "VisitID",
    "tblPatientPayment": "PatientPayID",
    "tblTempReceipt": "TempReceiptID",
    "tblLabRequest": "RequestID",
    "tblLabResult": "RequestID",
    "tblRadRequest": "RequestID",
    "tblRadResult": "RequestID",
    "tblVitalSign": "VSID",
    "tblOPDAppointment": "AppointmentID",
    "tblPhamDrugItem": "DrugItemID",
}


def _primary_key_column(source_table: str) -> str | None:
    """
    LIFEWAY physical PK for outpatients is OutPatientID; CSV exports alias to PatientID.
    Live MSSQL extraction uses mapping column names; use OutPatientID for ordering when requested.
    """
    pk = PRIMARY_KEY_BY_TABLE.get(source_table)
    if not pk:
        return None
    if os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        if source_table == "tblOutPatientRecord":
            return "OutPatientID"
    return pk


def _mssql_select_columns(source_table: str, cols: list[str]) -> list[str]:
    """
    Map logical CSV column names to LIFEWAY physical columns for live ODBC reads.
    """
    if source_table == "tblLabRequest":
        cols = [c for c in cols if c != "TestsRequested"]
    if source_table == "tblLabResult":
        cols = [c for c in cols if c not in ("ResultData", "HeaderNotes")]
    if source_table == "tblRadRequest":
        cols = [c for c in cols if c != "Investigations"]
    if source_table == "tblRadResult":
        cols = [c for c in cols if c == "__none__"]
    if source_table == "tblPatientPayment":
        cols = [c for c in cols if c == "__none__"]
    if source_table == "tblTempReceipt":
        cols = [c for c in cols if c == "__none__"]
    if source_table == "tblDrugPresItems":
        cols = [c for c in cols if c == "__none__"]
    if os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() != "lifeway":
        return cols
    lifeway_renames: dict[str, str] = {}
    if source_table == "tblOutPatientRecord":
        lifeway_renames = {
            "PatientID": "OutPatientID",
            "Surname": "SurName",
            "Othernames": "OtherNames",
            "DOB": "DateOfBirth",
            "Address": "HomeAddress",
        }
    if source_table == "tblPatientVisits":
        lifeway_renames = {"PatientID": "OutPatientID"}
    if source_table == "tblOPDAppointment":
        lifeway_renames = {
            "AppointmentID": "AppID",
            "PatientID": "OutPatientID",
        }
    if source_table == "tblPhamDrugItem":
        lifeway_renames = {"DrugName": "Name", "UnitPrice": "Sell"}
    out: list[str] = []
    for c in cols:
        phys = lifeway_renames.get(c, c)
        if phys not in out:
            out.append(phys)
    if source_table == "tblPhamDrugItem" and "Sell" in out and "Cost" not in out:
        out.append("Cost")
    return out


def _lifeway_logicalize_row(source_table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Normalize ODBC row keys to the same logical names used by CSV exports and load.py."""
    if os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() != "lifeway":
        return dict(row)
    phys_to_log: dict[str, str] = {}
    if source_table == "tblOutPatientRecord":
        phys_to_log = {
            "OutPatientID": "PatientID",
            "SurName": "Surname",
            "OtherNames": "Othernames",
            "DateOfBirth": "DOB",
            "HomeAddress": "Address",
        }
    elif source_table == "tblPatientVisits":
        phys_to_log = {"OutPatientID": "PatientID"}
    elif source_table == "tblPatientPayment":
        out = dict(row)
        try:
            if out.get("PatientID") is not None and int(out["PatientID"]) == 0:
                out["PatientID"] = None
        except (TypeError, ValueError):
            pass
        return out
    elif source_table == "tblTempReceipt":
        out = dict(row)
        try:
            if out.get("PatientID") is not None and int(out["PatientID"]) == 0:
                out["PatientID"] = None
        except (TypeError, ValueError):
            pass
        return out
    elif source_table == "tblDrugPresItems":
        out = dict(row)
        try:
            if out.get("PatientID") is not None and int(out["PatientID"]) == 0:
                out["PatientID"] = None
        except (TypeError, ValueError):
            pass
        return out
    elif source_table == "tblOPDAppointment":
        phys_to_log = {"AppID": "AppointmentID", "OutPatientID": "PatientID"}
    elif source_table == "tblPhamDrugItem":
        phys_to_log = {"Name": "DrugName", "Sell": "UnitPrice", "Cost": "_CostRaw"}
    elif source_table == "tblLabRequest":
        out = dict(row)
        try:
            if out.get("VisitID") is not None and int(out["VisitID"]) == 0:
                out["VisitID"] = None
        except (TypeError, ValueError):
            pass
        return out
    out: dict[str, Any] = {}
    for k, v in row.items():
        nk = phys_to_log.get(k, k)
        out[nk] = v
    if source_table == "tblPhamDrugItem":
        if out.get("UnitPrice") in (None, ""):
            out["UnitPrice"] = out.pop("_CostRaw", None)
        else:
            out.pop("_CostRaw", None)
    return out


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _build_connection():
    """
    Build pyodbc connection using either:
    - LMC_MSSQL_CONN_STR (full ODBC connection string), OR
    - LMC_MSSQL_SERVER + LMC_MSSQL_DATABASE (+ username/password or trusted connection).
    """
    try:
        import pyodbc  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "pyodbc is required for live MSSQL extraction. Install with 'pip install pyodbc'."
        ) from exc

    full_conn_str = os.environ.get("LMC_MSSQL_CONN_STR", "").strip()
    if full_conn_str:
        return pyodbc.connect(full_conn_str)

    server = os.environ.get("LMC_MSSQL_SERVER", "").strip()
    database = os.environ.get("LMC_MSSQL_DATABASE", "").strip()
    driver = os.environ.get("LMC_MSSQL_DRIVER", "ODBC Driver 17 for SQL Server").strip()
    username = os.environ.get("LMC_MSSQL_USERNAME", "").strip()
    password = os.environ.get("LMC_MSSQL_PASSWORD", "").strip()
    trusted = os.environ.get("LMC_MSSQL_TRUSTED_CONNECTION", "true").strip().lower() in {"1", "true", "yes"}

    if not server or not database:
        raise RuntimeError(
            "Missing MSSQL connection settings. Set LMC_MSSQL_CONN_STR "
            "or set LMC_MSSQL_SERVER and LMC_MSSQL_DATABASE."
        )

    if username and password:
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
            f"UID={username};PWD={password};TrustServerCertificate=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
            f"Trusted_Connection={'yes' if trusted else 'no'};TrustServerCertificate=yes;"
        )
    return pyodbc.connect(conn_str)


def _extract_table_rows(cursor: Any, source_table: str, source_columns: list[str], limit_per_table: int) -> list[dict[str, Any]]:
    cols = _dedupe_preserve_order(source_columns)
    if not cols:
        return []

    if source_table == "tblUsers":
        query = """
        SELECT TOP (?)
            u.[UserID],
            LTRIM(RTRIM(u.[UserName])) AS UserName,
            LTRIM(RTRIM(ISNULL(u.[FullName], N''))) AS FullName,
            REPLACE(REPLACE(REPLACE(ISNULL(u.[Description], N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS Description,
            CAST(ISNULL(u.[Active], 1) AS int) AS Active,
            LTRIM(RTRIM(ISNULL(s.[Designation], N''))) AS Designation,
            LTRIM(RTRIM(ISNULL(s.[StaffCategory], N''))) AS StaffCategory,
            CAST(ISNULL(s.[CanConsult], 0) AS int) AS CanConsult
        FROM [dbo].[tblUsers] u
        LEFT JOIN [dbo].[tblStaff] s ON s.[StaffID] = u.[StaffID]
        WHERE u.[UserName] IS NOT NULL AND LTRIM(RTRIM(u.[UserName])) <> N''
        ORDER BY u.[UserID] ASC;
        """
        logger.info("Extracting %s rows from tblUsers+tblStaff join", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records: list[dict[str, Any]] = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblOPDAppointment" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_OPD_APPOINTMENT_SELECT_BODY
        logger.info("Extracting %s rows from tblOPDAppointment (ToSee -> Staff -> User DoctorID)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblPatientVisits" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_PATIENT_VISITS_SELECT_BODY
        logger.info("Extracting %s rows from tblPatientVisits+tblChargeItem (ClinicName)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblPatientPayment" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_PATIENT_PAYMENT_SELECT_BODY
        logger.info("Extracting %s rows from tblPatientPayment (legacy payments)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblTempReceipt" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_TEMP_RECEIPT_SELECT_BODY
        logger.info("Extracting %s rows from tblTempReceipt+tblReceiptGrid (receipt lines)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblDrugPresItems" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_DRUG_PRESCRIPTION_LINES_SELECT_BODY
        logger.info("Extracting %s rows from tblDrugPresItems (prescription lines)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblVitalSign" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_VITAL_SIGN_SELECT_BODY
        logger.info("Extracting %s rows from tblVitalSign (resolved VisitID)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblLabRequest" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_LAB_REQUEST_SELECT_BODY
        logger.info("Extracting %s rows from tblLabRequest (STRING_AGG tests)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblLabResult" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_LAB_RESULT_SELECT_BODY
        logger.info("Extracting %s rows from tblLabResult (per RequestID, STRING_AGG details)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblRadRequest" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_RAD_REQUEST_SELECT_BODY
        logger.info("Extracting %s rows from tblRadRequest (with aggregated Investigations)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    if source_table == "tblRadResult" and os.environ.get("LEGACY_DB_VENDOR", "").strip().lower() == "lifeway":
        query = "SELECT TOP (?)\n" + LIFEWAY_RAD_RESULT_SELECT_BODY
        logger.info("Extracting %s rows from tblRadResult (aggregated report text by RequestID)", limit_per_table)
        cursor.execute(query, limit_per_table)
        column_names = [d[0] for d in cursor.description]
        records = []
        for row in cursor.fetchall():
            raw = dict(zip(column_names, row))
            records.append(_lifeway_logicalize_row(source_table, raw))
        return records

    pk_logical = PRIMARY_KEY_BY_TABLE.get(source_table)
    pk_phys = _primary_key_column(source_table) or pk_logical
    physical_cols = _mssql_select_columns(source_table, cols)
    if pk_phys and pk_phys not in physical_cols:
        cols_for_select = [pk_phys, *physical_cols]
    else:
        cols_for_select = physical_cols

    select_cols_sql = ", ".join(f"[{c}]" for c in cols_for_select)
    order_sql = f" ORDER BY [{pk_phys}] ASC" if pk_phys else ""
    query = f"SELECT TOP (?) {select_cols_sql} FROM [dbo].[{source_table}]{order_sql};"

    logger.info("Extracting %s rows from %s", limit_per_table, source_table)
    cursor.execute(query, limit_per_table)
    column_names = [d[0] for d in cursor.description]
    records: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        raw = dict(zip(column_names, row))
        records.append(_lifeway_logicalize_row(source_table, raw))
    return records


def _split_sql_csv(expr: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    in_quote = False
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "'":
            current.append(ch)
            if in_quote and i + 1 < len(expr) and expr[i + 1] == "'":
                current.append("'")
                i += 2
                continue
            in_quote = not in_quote
            i += 1
            continue
        if ch == "," and not in_quote:
            items.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    if current:
        items.append("".join(current).strip())
    return items


def _parse_tsql_literal(token: str) -> Any:
    t = token.strip()
    if not t:
        return None
    if t.upper() == "NULL":
        return None
    if t.startswith("N'") and t.endswith("'"):
        inner = t[2:-1].replace("''", "'")
        return inner
    if t.startswith("'") and t.endswith("'"):
        inner = t[1:-1].replace("''", "'")
        return inner
    if re.fullmatch(r"-?\d+", t):
        try:
            return int(t)
        except ValueError:
            return t
    if re.fullmatch(r"-?\d+\.\d+", t):
        try:
            return float(t)
        except ValueError:
            return t
    return t


def _extract_from_sql_file(
    sql_file: Path,
    grouped_rows: dict[str, list[MappingRow]],
    limit_per_table: int,
) -> dict[str, list[dict[str, Any]]]:
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")

    content = sql_file.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, list[dict[str, Any]]] = {}
    for source_table, rows in grouped_rows.items():
        out[source_table] = []

    for source_table in MIGRATION_TABLE_ORDER:
        if source_table not in grouped_rows:
            continue
        rows = grouped_rows[source_table]
        if source_table not in VERTICAL_SLICE_TABLES:
            continue

        mapped_cols = _dedupe_preserve_order([r.source_column for r in rows])
        if not mapped_cols:
            continue

        # Matches:
        # INSERT INTO [dbo].[tblX] ([A],[B],...) VALUES (..)
        # INSERT INTO dbo.tblX (A,B,...) VALUES (..)
        pattern = re.compile(
            rf"INSERT\s+INTO\s+(?:\[dbo\]\.\[{re.escape(source_table)}\]|dbo\.{re.escape(source_table)})\s*"
            r"\((?P<cols>.*?)\)\s*VALUES\s*\((?P<vals>.*?)\)",
            re.IGNORECASE | re.DOTALL,
        )
        matches = list(pattern.finditer(content))
        if not matches:
            logger.warning(
                "No INSERT rows found for %s in %s (likely schema-only export).",
                source_table,
                sql_file,
            )
            continue

        for m in matches[:limit_per_table]:
            raw_cols = _split_sql_csv(m.group("cols"))
            raw_vals = _split_sql_csv(m.group("vals"))
            cols = [c.strip().strip("[]") for c in raw_cols]
            vals = [_parse_tsql_literal(v) for v in raw_vals]
            row_dict = dict(zip(cols, vals))
            filtered = {col: row_dict.get(col) for col in mapped_cols}
            out[source_table].append(filtered)

        logger.info("Parsed %d rows from %s via SQL file.", len(out[source_table]), source_table)
    return out


def _extract_from_csv_dir(
    csv_dir: Path,
    grouped_rows: dict[str, list[MappingRow]],
    limit_per_table: int,
) -> dict[str, list[dict[str, Any]]]:
    if not csv_dir.exists() or not csv_dir.is_dir():
        raise FileNotFoundError(f"CSV directory not found: {csv_dir}")

    out: dict[str, list[dict[str, Any]]] = {}
    for source_table, rows in grouped_rows.items():
        out[source_table] = []

    for source_table in MIGRATION_TABLE_ORDER:
        if source_table not in grouped_rows:
            continue
        rows = grouped_rows[source_table]
        if source_table not in VERTICAL_SLICE_TABLES:
            continue

        if source_table == "tblUsers":
            mapped_cols = list(STAFF_USER_EXPORT_COLUMNS)
        else:
            mapped_cols = _dedupe_preserve_order([r.source_column for r in rows])
        if not mapped_cols:
            continue

        candidates = [
            csv_dir / f"{source_table}.csv",
            csv_dir / f"{source_table.lower()}.csv",
            csv_dir / f"{source_table.upper()}.csv",
        ]
        csv_file = next((p for p in candidates if p.exists()), None)
        if not csv_file:
            logger.warning(
                "CSV file not found for %s in %s. Expected one of: %s",
                source_table,
                csv_dir,
                ", ".join(str(p.name) for p in candidates),
            )
            continue

        with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= limit_per_table:
                    break
                filtered: dict[str, Any] = {}
                for col in mapped_cols:
                    filtered[col] = _normalize_csv_cell(row.get(col))
                out[source_table].append(filtered)

        logger.info("Parsed %d rows from CSV for %s (%s).", len(out[source_table]), source_table, csv_file)

    return out


def extract_source_data(
    mapping_rows: list[MappingRow],
    limit_per_table: int = 200,
    source: str = "mssql",
    sql_file: Path | None = None,
    csv_dir: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Extract legacy rows from SQL Server for first vertical slice tables only:
    - tblUsers (LIFEWAY: join tblStaff)
    - tblOutPatientRecord, tblPatientVisits (LIFEWAY: ClinicName + OP narrative columns for Consultation mapping in load.py)
    - tblPatientPayment (LIFEWAY: legacy patient payments; see lifeway_patient_payment_sql.py)
    - tblTempReceipt (LIFEWAY: POS receipt lines via tblReceiptGrid join; see lifeway_temp_receipt_sql.py)
    - tblDrugPresItems (LIFEWAY: prescription lines; see lifeway_drug_prescription_lines_sql.py)
    - tblLabRequest (LIFEWAY + LEGACY_DB_VENDOR=lifeway: TestsRequested STRING_AGG from details + tblLabTest)
    - tblLabResult (LIFEWAY: one row per RequestID, detail lines from tblLabResultDetails)
    - tblRadRequest (LIFEWAY: investigations aggregated from tblRadRequestDetails + tblChargeItem)
    - tblRadResult (LIFEWAY: report text aggregated from tblRadResult.RTBNotes by RequestID)
    - tblVitalSign (LIFEWAY + LEGACY_DB_VENDOR=lifeway: VisitID resolved via patient + same-day visit)
    - tblOPDAppointment (LIFEWAY + LEGACY_DB_VENDOR=lifeway: DoctorID from ToSee via staff/users)

    Other mapped tables are returned as empty until extraction is implemented.
    Return shape:
        {
            "tblOutPatientRecord": [{"PatientID": 1, "Surname": "Doe", ...}, ...],
            ...
        }
    """
    grouped = group_rows_by_source_table(mapping_rows)
    extracted: dict[str, list[dict[str, Any]]] = {}

    for source_table in grouped.keys():
        extracted[source_table] = []

    if source == "file":
        if not sql_file:
            raise RuntimeError("source=file requires sql_file path.")
        file_rows = _extract_from_sql_file(sql_file=sql_file, grouped_rows=grouped, limit_per_table=limit_per_table)
        extracted.update(file_rows)
        return extracted

    if source == "csv":
        if not csv_dir:
            raise RuntimeError("source=csv requires csv_dir path.")
        csv_rows = _extract_from_csv_dir(csv_dir=csv_dir, grouped_rows=grouped, limit_per_table=limit_per_table)
        extracted.update(csv_rows)
        return extracted

    if source not in {"mssql", "auto"}:
        raise ValueError(f"Unsupported source mode: {source}")

    if source == "auto":
        if csv_dir and csv_dir.exists():
            logger.info("Auto source: using CSV directory extraction (%s).", csv_dir)
            csv_rows = _extract_from_csv_dir(csv_dir=csv_dir, grouped_rows=grouped, limit_per_table=limit_per_table)
            extracted.update(csv_rows)
            return extracted
        if sql_file and sql_file.exists():
            logger.info("Auto source: using SQL file extraction (%s).", sql_file)
            file_rows = _extract_from_sql_file(sql_file=sql_file, grouped_rows=grouped, limit_per_table=limit_per_table)
            extracted.update(file_rows)
            return extracted

    conn = _build_connection()
    try:
        cursor = conn.cursor()
        for source_table in MIGRATION_TABLE_ORDER:
            rows = grouped.get(source_table, [])
            if source_table == "tblUsers":
                columns = list(STAFF_USER_EXPORT_COLUMNS)
            else:
                columns = [r.source_column for r in rows]
            if source_table in VERTICAL_SLICE_TABLES:
                extracted[source_table] = _extract_table_rows(
                    cursor=cursor,
                    source_table=source_table,
                    source_columns=columns,
                    limit_per_table=limit_per_table,
                )
                logger.info(
                    "Extracted %d rows from %s (%d mapped columns).",
                    len(extracted[source_table]),
                    source_table,
                    len(_dedupe_preserve_order(columns)),
                )
            else:
                logger.info("Skipping live extraction for %s; table not in first vertical slice.", source_table)
    finally:
        conn.close()

    return extracted
