from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MappingRow:
    source_table: str
    source_column: str
    target_model: str
    target_field: str
    transform_rule: str
    required_default: str
    validation_owner: str
    mapping_status: str
    notes: str


def load_mapping_rows(mapping_file: Path) -> list[MappingRow]:
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

    rows: list[MappingRow] = []
    with mapping_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                MappingRow(
                    source_table=(raw.get("source_table") or "").strip(),
                    source_column=(raw.get("source_column") or "").strip(),
                    target_model=(raw.get("target_model") or "").strip(),
                    target_field=(raw.get("target_field") or "").strip(),
                    transform_rule=(raw.get("transform_rule") or "").strip(),
                    required_default=(raw.get("required_default") or "").strip(),
                    validation_owner=(raw.get("validation_owner") or "").strip(),
                    mapping_status=(raw.get("mapping_status") or "").strip().lower(),
                    notes=(raw.get("notes") or "").strip(),
                )
            )
    return rows


def filter_rows_by_status(rows: Iterable[MappingRow], status: str) -> list[MappingRow]:
    normalized = status.strip().lower()
    if normalized == "all":
        return list(rows)
    return [r for r in rows if r.mapping_status == normalized]


def group_rows_by_source_table(rows: Iterable[MappingRow]) -> dict[str, list[MappingRow]]:
    grouped: dict[str, list[MappingRow]] = {}
    for row in rows:
        grouped.setdefault(row.source_table, []).append(row)
    return grouped

