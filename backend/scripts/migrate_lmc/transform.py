from __future__ import annotations

import logging
from typing import Any

from .extract import MIGRATION_TABLE_ORDER, STAFF_USER_EXPORT_COLUMNS
from .mapping import MappingRow, group_rows_by_source_table

logger = logging.getLogger(__name__)


def apply_transform_rule(value: Any, transform_rule: str) -> Any:
    """
    Minimal transform-rule dispatcher scaffold.
    Expand with your production conversion functions.
    """
    rule = (transform_rule or "").strip().lower()
    if rule == "trim_titlecase" and isinstance(value, str):
        return value.strip().title()
    if rule == "lowercase_trim_validate_email" and isinstance(value, str):
        return value.strip().lower()
    if rule.startswith("copy_int_as_legacy_id"):
        return value
    return value


def transform_source_data(
    extracted_rows_by_table: dict[str, list[dict[str, Any]]],
    mapping_rows: list[MappingRow],
) -> list[dict[str, Any]]:
    """
    Transform extracted source rows into normalized payload rows:
        {
            "source_table": "...",
            "target_model": "apps.patients.Patient",
            "field_values": {"first_name": "Jane", ...}
        }
    """
    grouped = group_rows_by_source_table(mapping_rows)
    transformed_payloads: list[dict[str, Any]] = []

    table_sequence = list(MIGRATION_TABLE_ORDER) + sorted(
        k for k in extracted_rows_by_table if k not in MIGRATION_TABLE_ORDER
    )
    for source_table in table_sequence:
        table_rows = extracted_rows_by_table.get(source_table, [])
        table_mapping = list(grouped.get(source_table, []))
        if not table_mapping:
            if source_table != "tblUsers":
                continue
            # Allow staff CSV without mapping rows (columns fixed in extract.STAFF_USER_EXPORT_COLUMNS).
            table_mapping = [
                MappingRow(
                    source_table="tblUsers",
                    source_column=c,
                    target_model="apps.users.User",
                    target_field="_legacy",
                    transform_rule="",
                    required_default="",
                    validation_owner="",
                    mapping_status="proposed",
                    notes="",
                )
                for c in STAFF_USER_EXPORT_COLUMNS
            ]
        by_target_model: dict[str, list[MappingRow]] = {}
        for row in table_mapping:
            by_target_model.setdefault(row.target_model, []).append(row)

        for source_row in table_rows:
            for target_model, model_mappings in by_target_model.items():
                field_values: dict[str, Any] = {}
                for m in model_mappings:
                    if source_table == "tblUsers":
                        continue
                    raw_value = source_row.get(m.source_column)
                    field_values[m.target_field] = apply_transform_rule(raw_value, m.transform_rule)

                transformed_payloads.append(
                    {
                        "source_table": source_table,
                        "target_model": target_model,
                        "source_row": source_row,
                        "field_values": field_values,
                    }
                )

        if table_rows:
            added = sum(1 for p in transformed_payloads if p["source_table"] == source_table)
            logger.info("Transform for %s produced %d payload rows.", source_table, added)

    return transformed_payloads

