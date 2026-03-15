from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from flow_memory import ensure_dependencies, yaml


CONFIG_FILENAME = ".flow_memory_config.yaml"
SCHEMA_FILENAMES = (
    "FlowCard.schema.json",
    "Node.schema.json",
    "Map.schema.json",
)


@dataclass
class AppConfig:
    config_path: Path
    flow_memory_project_root: Path | None
    code_root: Path | None


@dataclass
class InitializationResult:
    created: list[Path]
    skipped: list[Path]


def find_missing_flow_memory_components(target_root: Path | str) -> list[str]:
    root = Path(target_root).resolve()
    missing: list[str] = []

    required_paths = {
        "flows/": root / "flows",
        "flows/cards/": root / "flows" / "cards",
        "flows/nodes/": root / "flows" / "nodes",
        "flows/map.yaml": root / "flows" / "map.yaml",
        "schemas/": root / "schemas",
    }
    for label, path in required_paths.items():
        if not path.exists():
            missing.append(label)

    for schema_name in SCHEMA_FILENAMES:
        schema_path = root / "schemas" / schema_name
        if not schema_path.exists():
            missing.append(f"schemas/{schema_name}")

    return missing


def load_app_config(base_dir: Path | str) -> AppConfig:
    ensure_dependencies()

    root = Path(base_dir).resolve()
    config_path = root / CONFIG_FILENAME
    if not config_path.exists():
        return AppConfig(config_path=config_path, flow_memory_project_root=None, code_root=None)

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    project_value = raw.get("flow_memory_project_root")
    code_value = raw.get("code_root")
    return AppConfig(
        config_path=config_path,
        flow_memory_project_root=Path(project_value).expanduser().resolve() if project_value else None,
        code_root=Path(code_value).expanduser().resolve() if code_value else None,
    )


def save_app_config(
    base_dir: Path | str,
    *,
    flow_memory_project_root: Path | str | None,
    code_root: Path | str | None,
) -> Path:
    ensure_dependencies()

    root = Path(base_dir).resolve()
    config_path = root / CONFIG_FILENAME
    payload = {
        "flow_memory_project_root": str(Path(flow_memory_project_root).resolve()) if flow_memory_project_root else None,
        "code_root": str(Path(code_root).resolve()) if code_root else None,
    }
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    return config_path


def initialize_flow_memory_project(
    target_root: Path | str,
    *,
    source_root: Path | str,
) -> InitializationResult:
    root = Path(target_root).resolve()
    source = Path(source_root).resolve()

    created: list[Path] = []
    skipped: list[Path] = []

    flows_dir = root / "flows"
    cards_dir = flows_dir / "cards"
    nodes_dir = flows_dir / "nodes"
    schemas_dir = root / "schemas"

    for directory in (flows_dir, cards_dir, nodes_dir, schemas_dir):
        if directory.exists():
            skipped.append(directory)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)

    map_path = flows_dir / "map.yaml"
    if map_path.exists():
        skipped.append(map_path)
    else:
        map_path.write_text(
            "version: 1\n"
            "flows: []\n"
            "transfer_nodes: []\n"
            "impact_rules: []\n"
            "notes: Initial Metro Map for Flow Memory System v1.\n",
            encoding="utf-8",
        )
        created.append(map_path)

    conventions_path = flows_dir / "conventions.md"
    if conventions_path.exists():
        skipped.append(conventions_path)
    else:
        conventions_path.write_text(
            "# Flow Memory Conventions\n\n"
            "Use this file to record project-specific naming rules, exceptions, "
            "or workflow notes that differ from the default Flow Memory System conventions.\n",
            encoding="utf-8",
        )
        created.append(conventions_path)

    source_schema_dir = source / "schemas"
    for schema_name in SCHEMA_FILENAMES:
        source_path = source_schema_dir / schema_name
        target_path = schemas_dir / schema_name
        if target_path.exists():
            skipped.append(target_path)
            continue
        shutil.copy2(source_path, target_path)
        created.append(target_path)

    return InitializationResult(created=created, skipped=skipped)
