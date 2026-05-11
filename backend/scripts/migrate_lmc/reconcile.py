from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def write_reconciliation_report(
    output_file: Path,
    source_counts: dict[str, int],
    loaded_counts: dict[str, int],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["entity", "source_count", "loaded_count", "difference"])

        keys = sorted(set(source_counts.keys()) | set(loaded_counts.keys()))
        for key in keys:
            source = source_counts.get(key, 0)
            loaded = loaded_counts.get(key, 0)
            writer.writerow([key, source, loaded, source - loaded])

    logger.info("Wrote reconciliation report: %s", output_file)

