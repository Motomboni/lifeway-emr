"""
Restore SERVER_LIFEWAY_*.bak into Docker SQL Server and export CSVs for migrate_lmc.

Uses `docker exec` + `sqlcmd` inside the container (no SQL Server ODBC drivers required on the host).
CSV files are written under `/var/opt/mssql/data/lifeway_csv_export` in the container, then copied to the host with `docker cp`.

Prerequisites:
  - Docker Desktop
  - From repo root: `docker compose -f docker-compose.lifeway-mssql.yml up -d`

Usage (from repo root):
  python backend/scripts/migrate_lifeway/restore_export.py

Optional env:
  LIFEWAY_BAK_FILENAME           (default: SERVER_LIFEWAY_FULL_20260508_120000.bak)
  LIFEWAY_CSV_OUT_DIR            (default: <repo>/tmp/lifeway_csv; should match compose bind mount)
  LIFEWAY_MSSQL_SA_PASSWORD      (default: LifewayRestore1! — must match compose)
  LIFEWAY_DOCKER_CONTAINER        (default: lifeway-mssql)
  LIFEWAY_SQL_READY_TIMEOUT_SEC  (default: 600)
  LIFEWAY_SQL_READY_POLL_SEC     (default: 5)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from migrate_lmc.lifeway_appointment_sql import LIFEWAY_OPD_APPOINTMENT_SELECT_BODY
from migrate_lmc.lifeway_patient_visits_sql import LIFEWAY_PATIENT_VISITS_SELECT_BODY
from migrate_lmc.lifeway_patient_payment_sql import LIFEWAY_PATIENT_PAYMENT_SELECT_BODY
from migrate_lmc.lifeway_temp_receipt_sql import LIFEWAY_TEMP_RECEIPT_SELECT_BODY
from migrate_lmc.lifeway_drug_prescription_lines_sql import LIFEWAY_DRUG_PRESCRIPTION_LINES_SELECT_BODY
from migrate_lmc.lifeway_vital_sign_sql import LIFEWAY_VITAL_SIGN_SELECT_BODY
from migrate_lmc.lifeway_lab_request_sql import LIFEWAY_LAB_REQUEST_SELECT_BODY
from migrate_lmc.lifeway_lab_result_sql import LIFEWAY_LAB_RESULT_SELECT_BODY
from migrate_lmc.lifeway_radiology_request_sql import LIFEWAY_RAD_REQUEST_SELECT_BODY
from migrate_lmc.lifeway_radiology_result_sql import LIFEWAY_RAD_RESULT_SELECT_BODY

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_SA_PASSWORD = "LifewayRestore1!"
DEFAULT_BAK = "SERVER_LIFEWAY_FULL_20260508_120000.bak"


CONTAINER_EXPORT_DIR = "/var/opt/mssql/data/lifeway_csv_export"


def _docker_exec(
    container: str,
    args: list[str],
    timeout: int = 7200,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", container] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _docker_cp_from_container(container: str, container_path: str, host_path: Path) -> None:
    host_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["docker", "cp", f"{container}:{container_path}", str(host_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"docker cp failed ({container_path} -> {host_path}):\n{proc.stderr}\n{proc.stdout}")


def _docker_exec_sqlcmd(
    container: str,
    password: str,
    extra_args: list[str],
    timeout: int = 7200,
) -> subprocess.CompletedProcess:
    base = [
        "docker",
        "exec",
        container,
        "/opt/mssql-tools18/bin/sqlcmd",
        "-C",
        "-S",
        "localhost",
        "-U",
        "sa",
        "-P",
        password,
    ]
    return subprocess.run(
        base + extra_args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _wait_for_sql(container: str, password: str, ready_sec: int, poll_sec: int) -> None:
    attempts = max(1, ready_sec // poll_sec)
    print(f"Waiting for SQL Server in {container} (up to {ready_sec}s)...")
    for i in range(attempts):
        proc = _docker_exec_sqlcmd(
            container,
            password,
            ["-Q", "SELECT 1", "-W", "-h", "-1"],
            timeout=30,
        )
        if proc.returncode == 0 and "1" in proc.stdout:
            print("SQL Server is accepting connections.")
            return
        time.sleep(poll_sec)
        if (i + 1) % 12 == 0:
            print(f"  still waiting... ({(i + 1) * poll_sec}s)")
    raise SystemExit(
        f"SQL Server in container {container} did not become ready within {ready_sec}s. "
        "Check `docker logs {container}`.".replace("{container}", container)
    )


def _filelistonly_from_docker(container: str, password: str, bak_in_container: str) -> list[tuple[str, str]]:
    proc = _docker_exec_sqlcmd(
        container,
        password,
        [
            "-d",
            "master",
            "-Q",
            f"SET NOCOUNT ON; RESTORE FILELISTONLY FROM DISK = N'{bak_in_container}'",
            "-s",
            "|",
            "-W",
            "-w",
            "65535",
            "-h",
            "-1",
        ],
        timeout=600,
    )
    if proc.returncode != 0:
        raise SystemExit(f"FILELISTONLY failed:\n{proc.stdout}\n{proc.stderr}")
    rows_out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "(rows affected)" in line.lower():
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            logical, type_val = parts[0], parts[2]
            if logical and type_val:
                rows_out.append((logical, type_val))
    if not rows_out:
        raise SystemExit(f"No rows parsed from FILELISTONLY. Raw stdout:\n{proc.stdout}")
    return rows_out


def _restore_sql(bak_path: str, logical_rows: list[tuple[str, str]]) -> str:
    data_dir = "/var/opt/mssql/data/"
    move_clauses: list[str] = []
    for logical, type_val in logical_rows:
        tv = str(type_val).strip().upper()
        ext = "ldf" if tv.startswith("L") else "mdf"
        safe = "".join(ch if ch.isalnum() else "_" for ch in logical)[:40]
        dest = f"{data_dir}lifeway_restore_{safe}.{ext}"
        move_clauses.append(f"MOVE N'{logical}' TO N'{dest}'")
    move_sql = ", ".join(move_clauses)
    return (
        f"USE [master]; RESTORE DATABASE [LIFEWAY] FROM DISK = N'{bak_path}' "
        f"WITH {move_sql}, REPLACE, RECOVERY;"
    )


def _run_restore(container: str, password: str, sql: str) -> None:
    proc = _docker_exec_sqlcmd(
        container,
        password,
        ["-d", "master", "-Q", sql],
        timeout=7200,
    )
    if proc.returncode != 0:
        raise SystemExit(f"RESTORE failed (code {proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    print("RESTORE completed.")


def _export_via_sqlcmd(
    container: str,
    password: str,
    query: str,
    container_out_posix: str,
    host_path: Path,
    csv_header_line: str,
) -> int:
    """
    Write query results as comma-separated (header row) to container_out, then copy to host_path.
    """
    # sqlcmd -Q is safest as a single line on Windows/docker exec argument passing.
    query_one_line = " ".join(query.split())
    _docker_exec(
        container,
        ["/bin/sh", "-c", f"mkdir -p {CONTAINER_EXPORT_DIR} && rm -f {container_out_posix}"],
        timeout=60,
    )
    proc: subprocess.CompletedProcess | None = None
    for attempt in (1, 2):
        proc = _docker_exec_sqlcmd(
            container,
            password,
            [
                "-d",
                "LIFEWAY",
                "-Q",
                query_one_line,
                "-o",
                container_out_posix,
                "-h",
                "-1",
                "-s",
                ",",
                "-W",
                "-f",
                "65001",
            ],
            timeout=7200,
        )
        if proc.returncode == 0:
            break
        if attempt == 1:
            print(
                f"Export attempt 1 failed for {container_out_posix} (exit {proc.returncode}); retrying after 3s...",
                file=sys.stderr,
            )
            time.sleep(3)
            _docker_exec(
                container,
                ["/bin/sh", "-c", f"rm -f {container_out_posix}"],
                timeout=60,
            )
    assert proc is not None
    if proc.returncode != 0:
        msg = (
            f"Export failed for {container_out_posix} (sqlcmd exit code {proc.returncode}).\n"
            f"--- sqlcmd stdout ({len(proc.stdout)} chars) ---\n{proc.stdout or '(empty)'}\n"
            f"--- sqlcmd stderr ({len(proc.stderr)} chars) ---\n{proc.stderr or '(empty)'}\n"
            "Tip: test `docker exec <container> /opt/mssql-tools18/bin/sqlcmd ... -d LIFEWAY -Q \"SELECT DB_NAME()\"` "
            "with the same SA password as LIFEWAY_MSSQL_SA_PASSWORD.\n"
            "If this was the first export right after RESTORE, run restore_export again (or wait a few seconds and retry)."
        )
        print(msg, file=sys.stderr)
        raise SystemExit(msg)
    _docker_cp_from_container(container, container_out_posix, host_path)
    _prepend_csv_header_line(host_path, csv_header_line)
    return 0


def _sanitize_sqlcmd_csv_body(body: str) -> str:
    """sqlcmd may append '(N rows affected)' lines to the output file."""
    lines: list[str] = []
    for ln in body.splitlines():
        t = ln.strip()
        if not t:
            continue
        if re.match(r"^\(\d+ rows affected\)$", t, flags=re.IGNORECASE):
            continue
        if "rows affected" in t.lower():
            continue
        lines.append(ln)
    return "\n".join(lines)


def _prepend_csv_header_line(host_path: Path, header_line: str) -> None:
    """sqlcmd -h -1 omits column headers; prepend one header row for migrate_lmc."""
    body = _sanitize_sqlcmd_csv_body(host_path.read_text(encoding="utf-8-sig", errors="replace").strip())
    if not body:
        host_path.write_text(header_line + "\n", encoding="utf-8")
        return
    host_path.write_text(header_line + "\n" + body + "\n", encoding="utf-8")


def _count_data_rows_csv(host_path: Path) -> int:
    if not host_path.exists():
        return 0
    text = host_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return max(0, len(lines) - 1)


EXPORTS: list[tuple[str, str, str]] = [
    (
        "tblUsers.csv",
        "UserID,UserName,FullName,Description,Active,Designation,StaffCategory,CanConsult",
        """
SELECT
    CAST(u.UserID AS int) AS UserID,
    LTRIM(RTRIM(u.UserName)) AS UserName,
    LTRIM(RTRIM(ISNULL(u.FullName, N''))) AS FullName,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(u.Description, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(200)
    ) AS Description,
    CAST(ISNULL(u.Active, 1) AS int) AS Active,
    LTRIM(RTRIM(ISNULL(s.Designation, N''))) AS Designation,
    LTRIM(RTRIM(ISNULL(s.StaffCategory, N''))) AS StaffCategory,
    CAST(ISNULL(s.CanConsult, 0) AS int) AS CanConsult
FROM dbo.tblUsers u
LEFT JOIN dbo.tblStaff s ON s.StaffID = u.StaffID
WHERE u.UserName IS NOT NULL AND LTRIM(RTRIM(u.UserName)) <> N''
ORDER BY u.UserID ASC
""".strip(),
    ),
    (
        "tblOutPatientRecord.csv",
        "PatientID,Surname,Othernames,Sex,DOB,PhoneNo,Email,Address",
        """
SELECT
    CAST(OutPatientID AS int) AS PatientID,
    CAST(SurName AS nvarchar(255)) AS Surname,
    CAST(OtherNames AS nvarchar(255)) AS Othernames,
    CAST(Sex AS nvarchar(20)) AS Sex,
    CAST(DateOfBirth AS datetime) AS DOB,
    CAST(COALESCE(HomeTel, OfficeTel, NextOfKinTel, N'') AS nvarchar(50)) AS PhoneNo,
    CAST(Email AS nvarchar(255)) AS Email,
    CAST(
        REPLACE(REPLACE(REPLACE(ISNULL(HomeAddress, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ')
        AS nvarchar(max)
    ) AS Address
FROM dbo.tblOutPatientRecord
WHERE OutPatientID IS NOT NULL
ORDER BY OutPatientID ASC
""".strip(),
    ),
    (
        "tblPatientVisits.csv",
        "VisitID,PatientID,ClinicID,ClinicName,Date,VisitType,Status,PaymentStatus,ChiefComplaint,Reason,"
        "VisitNotes,HPC,PMH,FHx,Exam,Assessment,TreatPlan,ResultsText,Treatment,Summary,FollowUp,IMH,DH,"
        "Weight,Temperature,LegacyDoctor",
        ("SELECT\n" + LIFEWAY_PATIENT_VISITS_SELECT_BODY).strip(),
    ),
    (
        "tblPatientPayment.csv",
        "PatientPayID,PatientID,PaymentDate,LegacyStatus,ReceiptNo,PayAmount,ServiceLine,DiagnosisLine,HMOCode,PayerName",
        ("SELECT\n" + LIFEWAY_PATIENT_PAYMENT_SELECT_BODY).strip(),
    ),
    (
        "tblTempReceipt.csv",
        "TempReceiptID,GridReceiptID,ReceiptNo,PatientID,LineDate,ServiceLine,FieldName,LineAmount",
        ("SELECT\n" + LIFEWAY_TEMP_RECEIPT_SELECT_BODY).strip(),
    ),
    (
        "tblLabRequest.csv",
        "RequestID,PatientID,VisitID,DateRequested,Sender,Status,Diagnosis,TestsRequested",
        ("SELECT\n" + LIFEWAY_LAB_REQUEST_SELECT_BODY).strip(),
    ),
    (
        "tblLabResult.csv",
        "RequestID,PatientID,Date,AuthorizedBy,HeaderNotes,ResultData",
        ("SELECT\n" + LIFEWAY_LAB_RESULT_SELECT_BODY).strip(),
    ),
    (
        "tblRadRequest.csv",
        "RequestID,PatientID,VisitID,Date,Sender,Status,Diagnosis,Investigations",
        ("SELECT\n" + LIFEWAY_RAD_REQUEST_SELECT_BODY).strip(),
    ),
    (
        "tblRadResult.csv",
        "RequestID,PatientID,Date,ReportBy,ReportText",
        ("SELECT\n" + LIFEWAY_RAD_RESULT_SELECT_BODY).strip(),
    ),
    (
        "tblVitalSign.csv",
        "VSID,VisitID,RecordedAt,Temperature,BloodPressure,Pulse,Resp,SPO2,Wt,Ht",
        ("SELECT\n" + LIFEWAY_VITAL_SIGN_SELECT_BODY).strip(),
    ),
    (
        "tblOPDAppointment.csv",
        "AppointmentID,PatientID,Clinic,DoctorID,DoctorName,AppointmentDate,Status,VisitID,Reason,Notes,Duration",
        ("SELECT\n" + LIFEWAY_OPD_APPOINTMENT_SELECT_BODY).strip(),
    ),
    (
        "tblPhamDrugItem.csv",
        "DrugItemID,DrugName,UnitPrice,Cost",
        """
SELECT
    CAST(DrugItemID AS int) AS DrugItemID,
    CAST(REPLACE(REPLACE(REPLACE(ISNULL(Name, N''), N',', N';'), CHAR(10), N' '), CHAR(13), N' ') AS nvarchar(255)) AS DrugName,
    CAST(ISNULL(Sell, Cost) AS decimal(18, 2)) AS UnitPrice,
    CAST(Cost AS decimal(18, 2)) AS Cost
FROM dbo.tblPhamDrugItem
WHERE DrugItemID IS NOT NULL AND LTRIM(RTRIM(ISNULL(Name, N''))) <> N''
ORDER BY DrugItemID ASC
""".strip(),
    ),
    (
        "tblDrugPresItems.csv",
        "PresItemID,PrescriptionID,PatientID,PrescriptionDate,Sender,DrugItemID,DrugName,QtyIssued,ItemNotes",
        ("SELECT\n" + LIFEWAY_DRUG_PRESCRIPTION_LINES_SELECT_BODY).strip(),
    ),
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Restore LIFEWAY backup and/or export CSV tables for migrate_lmc.")
    parser.add_argument(
        "--only",
        action="append",
        metavar="FILE.csv",
        help="Export only these CSV file names (repeatable). Skips RESTORE when used with --skip-restore.",
    )
    parser.add_argument(
        "--skip-restore",
        action="store_true",
        help="Do not RESTORE the .bak; export from the existing LIFEWAY database in the container.",
    )
    args = parser.parse_args()

    container = os.environ.get("LIFEWAY_DOCKER_CONTAINER", "lifeway-mssql").strip()
    password = os.environ.get("LIFEWAY_MSSQL_SA_PASSWORD", DEFAULT_SA_PASSWORD)
    bak_name = os.environ.get("LIFEWAY_BAK_FILENAME", DEFAULT_BAK)
    bak_in_container = f"/backup/{bak_name}"
    out_dir = Path(os.environ.get("LIFEWAY_CSV_OUT_DIR", str(PROJECT_ROOT / "tmp" / "lifeway_csv"))).resolve()
    ready_sec = int(os.environ.get("LIFEWAY_SQL_READY_TIMEOUT_SEC", "600"))
    poll_sec = int(os.environ.get("LIFEWAY_SQL_READY_POLL_SEC", "5"))

    out_dir.mkdir(parents=True, exist_ok=True)

    _wait_for_sql(container, password, ready_sec, poll_sec)

    if not args.skip_restore:
        print("Reading backup file list from", bak_in_container)
        logical_rows = _filelistonly_from_docker(container, password, bak_in_container)
        print("Logical files:", logical_rows)

        restore_sql = _restore_sql(bak_in_container, logical_rows)
        print("Running RESTORE DATABASE [LIFEWAY] ...")
        _run_restore(container, password, restore_sql)
        # Brief pause: first sqlcmd -o export can rarely fail immediately post-RESTORE while files settle.
        time.sleep(2)

        chk = _docker_exec_sqlcmd(
            container,
            password,
            ["-Q", "SELECT CASE WHEN DB_ID(N'LIFEWAY') IS NULL THEN 0 ELSE 1 END", "-W", "-h", "-1"],
            timeout=60,
        )
        if chk.returncode != 0 or "1" not in chk.stdout:
            raise SystemExit(f"Database LIFEWAY not found after RESTORE. Output:\n{chk.stdout}\n{chk.stderr}")
    else:
        chk = _docker_exec_sqlcmd(
            container,
            password,
            ["-Q", "SELECT CASE WHEN DB_ID(N'LIFEWAY') IS NULL THEN 0 ELSE 1 END", "-W", "-h", "-1"],
            timeout=60,
        )
        if chk.returncode != 0 or "1" not in chk.stdout:
            raise SystemExit(
                f"Database LIFEWAY not found in container {container}. "
                "Run without --skip-restore first, or restore manually."
            )
        print("Skipping RESTORE; exporting from existing LIFEWAY database.")

    exports = EXPORTS
    if args.only:
        only_set = {name.strip().lower() for name in args.only}
        exports = [item for item in EXPORTS if item[0].lower() in only_set]
        if not exports:
            known = ", ".join(name for name, _, _ in EXPORTS)
            raise SystemExit(f"No matching exports for --only. Known files: {known}")

    total = 0
    for fname, csv_header, query in exports:
        host_path = out_dir / fname
        container_out_posix = str(PurePosixPath(CONTAINER_EXPORT_DIR) / fname)
        print(f"Exporting -> {fname} ...")
        _export_via_sqlcmd(container, password, query, container_out_posix, host_path, csv_header)
        n = _count_data_rows_csv(host_path)
        print(f"  wrote {n} data rows -> {host_path}")
        total += n

    print("Done. Total data rows exported:", total)
    print("Run migration (from backend/):")
    print(f'  python scripts/migrate_lmc/run_pipeline.py --source csv --csv-dir "{out_dir}" --dry-run --status proposed')
    return 0


if __name__ == "__main__":
    sys.exit(main())
