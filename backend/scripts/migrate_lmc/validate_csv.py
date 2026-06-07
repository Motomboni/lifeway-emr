from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .extract import MIGRATION_TABLE_ORDER, STAFF_USER_EXPORT_COLUMNS, VERTICAL_SLICE_TABLES
from .mapping import MappingRow


@dataclass(frozen=True)
class CsvValidationResult:
    table: str
    file_path: Path
    exists: bool
    row_count: int
    missing_headers: list[str]


def validate_csv_inputs(csv_dir: Path, mapping_rows: list[MappingRow]) -> list[CsvValidationResult]:
    rows_by_table: dict[str, list[MappingRow]] = {}
    for row in mapping_rows:
        rows_by_table.setdefault(row.source_table, []).append(row)

    results: list[CsvValidationResult] = []
    for table in MIGRATION_TABLE_ORDER:
        if table not in VERTICAL_SLICE_TABLES:
            continue
        if table == "tblUsers":
            expected_headers = sorted(STAFF_USER_EXPORT_COLUMNS)
        else:
            expected_headers = sorted({r.source_column for r in rows_by_table.get(table, []) if r.source_column})
        file_path = csv_dir / f"{table}.csv"
        if not file_path.exists():
            results.append(
                CsvValidationResult(
                    table=table,
                    file_path=file_path,
                    exists=False,
                    row_count=0,
                    missing_headers=expected_headers,
                )
            )
            continue

        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            actual_headers = set(reader.fieldnames or [])
            missing = [h for h in expected_headers if h not in actual_headers]
            row_count = sum(1 for _ in reader)

        results.append(
            CsvValidationResult(
                table=table,
                file_path=file_path,
                exists=True,
                row_count=row_count,
                missing_headers=missing,
            )
        )

    return results

