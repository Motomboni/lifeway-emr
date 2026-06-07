from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from migrate_lmc.common import ensure_output_dir, setup_django, setup_logging
from migrate_lmc.extract import SOURCE_TABLE_TO_TARGET_MODEL, extract_source_data
from migrate_lmc.load import load_transformed_data
from migrate_lmc.mapping import filter_rows_by_status, load_mapping_rows
from migrate_lmc.reconcile import write_reconciliation_report
from migrate_lmc.settings import MigrationSettings
from migrate_lmc.transform import transform_source_data
from migrate_lmc.validate_csv import validate_csv_inputs

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CSV-driven LMC migration scaffold.")
    parser.add_argument(
        "--mapping-file",
        type=str,
        default="",
        help="Path to mapping CSV. Defaults to docs/migration/lmc-column-mapping-status.csv",
    )
    parser.add_argument(
        "--status",
        type=str,
        default="all",
        choices=["all", "proposed", "confirmed"],
        help="Filter mapping rows by mapping_status.",
    )
    parser.add_argument(
        "--limit-per-table",
        type=int,
        default=200,
        help="Extraction limit per source table (stub parameter).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Transform/load without writing records.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="auto",
        choices=["auto", "mssql", "file", "csv"],
        help="Extraction source mode: auto, live mssql, file-based SQL dump parsing, or CSV files.",
    )
    parser.add_argument(
        "--sql-file",
        type=str,
        default="",
        help="Path to legacy SQL dump file (used with --source file or auto).",
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default="",
        help="Directory containing per-table CSV files (used with --source csv or auto).",
    )
    parser.add_argument(
        "--validate-csv-only",
        action="store_true",
        help="Validate CSV files (headers + row counts) and exit without running migration.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()

    settings = MigrationSettings.default()
    if args.mapping_file:
        settings = MigrationSettings(
            backend_dir=settings.backend_dir,
            project_root=settings.project_root,
            mapping_file=Path(args.mapping_file).resolve(),
            output_dir=settings.output_dir,
            django_settings_module=settings.django_settings_module,
        )

    ensure_output_dir(settings.output_dir)
    setup_django(settings)

    rows = load_mapping_rows(settings.mapping_file)
    selected_rows = filter_rows_by_status(rows, args.status)
    logger.info("Loaded %d mappings (status=%s).", len(selected_rows), args.status)

    sql_file = Path(args.sql_file).resolve() if args.sql_file else (settings.project_root / "LMC.sql")
    csv_dir = Path(args.csv_dir).resolve() if args.csv_dir else None

    if args.source == "csv" or args.validate_csv_only:
        if not csv_dir:
            raise RuntimeError("CSV validation/source requires --csv-dir.")
        validation = validate_csv_inputs(csv_dir, selected_rows)
        for r in validation:
            if not r.exists:
                logger.error("Missing CSV file for %s: %s", r.table, r.file_path)
                continue
            if r.missing_headers:
                logger.error(
                    "CSV header mismatch for %s (%s). Missing headers: %s",
                    r.table,
                    r.file_path,
                    ", ".join(r.missing_headers),
                )
            else:
                logger.info("CSV validated for %s (%d data rows): %s", r.table, r.row_count, r.file_path)

        if args.validate_csv_only:
            logger.info("CSV validation complete (--validate-csv-only).")
            return

    extracted = extract_source_data(
        selected_rows,
        limit_per_table=args.limit_per_table,
        source=args.source,
        sql_file=sql_file,
        csv_dir=csv_dir,
    )
    transformed = transform_source_data(extracted, selected_rows)
    loaded_counts = load_transformed_data(transformed, dry_run=args.dry_run)

    source_counts = {table: len(records) for table, records in extracted.items()}
    reconcile_source: dict[str, int] = {}
    for table, n in source_counts.items():
        key = SOURCE_TABLE_TO_TARGET_MODEL.get(table, table)
        reconcile_source[key] = reconcile_source.get(key, 0) + n
    reconcile_file = settings.output_dir / "reconciliation.csv"
    write_reconciliation_report(reconcile_file, reconcile_source, loaded_counts)

    summary = {
        "mapping_file": str(settings.mapping_file),
        "status_filter": args.status,
        "dry_run": bool(args.dry_run),
        "source_mode": args.source,
        "sql_file": str(sql_file),
        "csv_dir": str(csv_dir) if csv_dir else None,
        "mapping_rows": len(selected_rows),
        "source_tables": len(extracted),
        "transformed_payloads": len(transformed),
        "loaded_counts": loaded_counts,
        "reconciliation_report": str(reconcile_file),
    }
    summary_file = settings.output_dir / "run_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Run summary written: %s", summary_file)


if __name__ == "__main__":
    main()

