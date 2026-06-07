from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MigrationSettings:
    backend_dir: Path
    project_root: Path
    mapping_file: Path
    output_dir: Path
    django_settings_module: str = "core.settings"

    @staticmethod
    def default() -> "MigrationSettings":
        backend_dir = Path(__file__).resolve().parents[2]
        project_root = backend_dir.parent
        output_dir = project_root / "tmp" / "lmc_migration"
        mapping_file = project_root / "docs" / "migration" / "lmc-column-mapping-status.csv"
        return MigrationSettings(
            backend_dir=backend_dir,
            project_root=project_root,
            mapping_file=mapping_file,
            output_dir=output_dir,
        )

