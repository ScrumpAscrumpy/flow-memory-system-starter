from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency guard
    yaml = None
    Draft202012Validator = None
    IMPORT_ERROR = exc
else:  # pragma: no cover - constant assignment
    IMPORT_ERROR = None


SCHEMA_FILES = {
    "flow_card": "FlowCard.schema.json",
    "node": "Node.schema.json",
    "map": "Map.schema.json",
}

FLOW_EXTENSIONS = ("*.yaml", "*.yml")


class FlowMemoryError(Exception):
    """Base error for Flow Memory tooling."""


class DependencyError(FlowMemoryError):
    """Raised when required Python packages are unavailable."""


class ValidationError(FlowMemoryError):
    """Raised when Flow Memory data fails validation."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("Flow Memory validation failed")
        self.errors = errors


@dataclass
class LoadedDocument:
    path: Path
    data: Any


@dataclass
class ProjectData:
    project_root: Path
    flow_cards: list[LoadedDocument]
    nodes: list[LoadedDocument]
    map_doc: LoadedDocument

    @property
    def flow_cards_by_id(self) -> dict[str, LoadedDocument]:
        return {
            document.data["id"]: document
            for document in self.flow_cards
            if isinstance(document.data, dict) and isinstance(document.data.get("id"), str)
        }

    @property
    def nodes_by_id(self) -> dict[str, LoadedDocument]:
        return {
            document.data["id"]: document
            for document in self.nodes
            if isinstance(document.data, dict) and isinstance(document.data.get("id"), str)
        }


def ensure_dependencies() -> None:
    if IMPORT_ERROR is not None:
        missing = getattr(IMPORT_ERROR, "name", None) or "dependency"
        raise DependencyError(
            f"Missing Python dependency: {missing}. Run `python3 -m pip install -r requirements.txt`."
        )


def load_project(project_root: Path | str) -> ProjectData:
    ensure_dependencies()

    root = Path(project_root).resolve()
    flows_dir = root / "flows"
    cards_dir = flows_dir / "cards"
    nodes_dir = flows_dir / "nodes"
    map_path = flows_dir / "map.yaml"
    schema_dir = root / "schemas"

    required_paths = [flows_dir, cards_dir, nodes_dir, map_path, schema_dir]
    missing_paths = [path for path in required_paths if not path.exists()]
    if missing_paths:
        raise ValidationError([f"Missing required path: {path}" for path in missing_paths])

    validators = {
        key: Draft202012Validator(load_schema(schema_dir / filename))
        for key, filename in SCHEMA_FILES.items()
    }

    errors: list[str] = []
    flow_cards: list[LoadedDocument] = []
    nodes: list[LoadedDocument] = []

    seen_flow_ids: dict[str, Path] = {}
    seen_node_ids: dict[str, Path] = {}

    for path in iter_yaml_files(cards_dir):
        data, schema_errors = collect_schema_errors(path, validators["flow_card"])
        if schema_errors:
            errors.extend(f"{path}: {message}" for message in schema_errors)
            continue
        document = LoadedDocument(path=path, data=data)
        ensure_mapping(document, errors)
        if not isinstance(data, dict):
            continue
        flow_cards.append(document)
        flow_id = data.get("id")
        if isinstance(flow_id, str):
            if flow_id in seen_flow_ids:
                errors.append(f"{path}: duplicate flow ID `{flow_id}` also found in {seen_flow_ids[flow_id]}")
            else:
                seen_flow_ids[flow_id] = path

    for path in iter_yaml_files(nodes_dir):
        data, schema_errors = collect_schema_errors(path, validators["node"])
        if schema_errors:
            errors.extend(f"{path}: {message}" for message in schema_errors)
            continue
        document = LoadedDocument(path=path, data=data)
        ensure_mapping(document, errors)
        if not isinstance(data, dict):
            continue
        nodes.append(document)
        node_id = data.get("id")
        if isinstance(node_id, str):
            if node_id in seen_node_ids:
                errors.append(f"{path}: duplicate node ID `{node_id}` also found in {seen_node_ids[node_id]}")
            else:
                seen_node_ids[node_id] = path

    map_data, map_schema_errors = collect_schema_errors(map_path, validators["map"])
    if map_schema_errors:
        errors.extend(f"{map_path}: {message}" for message in map_schema_errors)
        raise ValidationError(errors)

    map_doc = LoadedDocument(path=map_path, data=map_data)
    ensure_mapping(map_doc, errors)
    errors.extend(validate_cross_references(flow_cards, nodes, map_doc))

    if errors:
        raise ValidationError(errors)

    return ProjectData(
        project_root=root,
        flow_cards=flow_cards,
        nodes=nodes,
        map_doc=map_doc,
    )


def load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def iter_yaml_files(directory: Path) -> Iterable[Path]:
    for pattern in FLOW_EXTENSIONS:
        yield from sorted(directory.glob(pattern))


def format_json_path(parts: Iterable[Any]) -> str:
    location = "$"
    for part in parts:
        if isinstance(part, int):
            location += f"[{part}]"
        else:
            location += f".{part}"
    return location


def collect_schema_errors(path: Path, validator: Draft202012Validator) -> tuple[Any | None, list[str]]:
    errors: list[str] = []
    try:
        data = load_yaml(path)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    except OSError as exc:
        return None, [f"Failed to read file: {exc}"]

    for error in sorted(validator.iter_errors(data), key=lambda item: format_json_path(item.absolute_path)):
        location = format_json_path(error.absolute_path)
        errors.append(f"{location}: {error.message}")

    return data, errors


def normalize_flow_filename(flow_id: str) -> str:
    name = flow_id.removeprefix("flow.")
    return f"{name.replace('.', '-').replace('_', '-')}.yaml"


def normalize_node_filenames(node_id: str) -> set[str]:
    return {
        f"{node_id}.yaml",
        f"{node_id.replace(':', '_')}.yaml",
    }


def ensure_mapping(document: LoadedDocument, errors: list[str]) -> None:
    if not isinstance(document.data, dict):
        errors.append(f"{document.path}: top-level YAML value must be an object")


def add_cross_reference_error(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path}: {message}")


def check_reference(
    errors: list[str],
    source_path: Path,
    label: str,
    value: str,
    known_values: set[str],
) -> None:
    if value not in known_values:
        add_cross_reference_error(errors, source_path, f"{label} references unknown ID `{value}`")


def validate_cross_references(
    flow_cards: list[LoadedDocument],
    nodes: list[LoadedDocument],
    map_doc: LoadedDocument,
) -> list[str]:
    errors: list[str] = []
    known_flow_ids = {
        document.data["id"] for document in flow_cards if isinstance(document.data, dict) and "id" in document.data
    }
    known_node_ids = {
        document.data["id"] for document in nodes if isinstance(document.data, dict) and "id" in document.data
    }

    for document in flow_cards:
        if not isinstance(document.data, dict):
            continue

        flow_id = document.data.get("id")
        if isinstance(flow_id, str):
            expected = normalize_flow_filename(flow_id)
            if document.path.name != expected:
                add_cross_reference_error(
                    errors,
                    document.path,
                    f"expected filename `{expected}` for flow ID `{flow_id}`",
                )

        for entry_point in document.data.get("entry_points", []):
            if isinstance(entry_point, str):
                check_reference(errors, document.path, "entry_points", entry_point, known_node_ids)

        for anchor_node in document.data.get("anchor_nodes", []):
            if isinstance(anchor_node, str):
                check_reference(errors, document.path, "anchor_nodes", anchor_node, known_node_ids)

        for related_flow in document.data.get("related_flows", []):
            if isinstance(related_flow, str):
                check_reference(errors, document.path, "related_flows", related_flow, known_flow_ids)

        for index, step in enumerate(document.data.get("steps", [])):
            if not isinstance(step, dict):
                continue
            for field in ("from", "to", "actor", "target", "store", "service"):
                value = step.get(field)
                if isinstance(value, str):
                    check_reference(errors, document.path, f"steps[{index}].{field}", value, known_node_ids)

        for index, persistence in enumerate(document.data.get("persistence", [])):
            if isinstance(persistence, dict) and isinstance(persistence.get("id"), str):
                check_reference(errors, document.path, f"persistence[{index}].id", persistence["id"], known_node_ids)

        for index, return_path in enumerate(document.data.get("return_paths", [])):
            if not isinstance(return_path, dict):
                continue
            for field in ("from", "to"):
                value = return_path.get(field)
                if isinstance(value, str):
                    check_reference(errors, document.path, f"return_paths[{index}].{field}", value, known_node_ids)

    for document in nodes:
        if not isinstance(document.data, dict):
            continue

        node_id = document.data.get("id")
        if isinstance(node_id, str):
            expected_names = normalize_node_filenames(node_id)
            if document.path.name not in expected_names:
                expected = " or ".join(sorted(expected_names))
                add_cross_reference_error(
                    errors,
                    document.path,
                    f"expected filename `{expected}` for node ID `{node_id}`",
                )

        for owned_flow in document.data.get("owned_by_flows", []):
            if isinstance(owned_flow, str):
                check_reference(errors, document.path, "owned_by_flows", owned_flow, known_flow_ids)

    if isinstance(map_doc.data, dict):
        for index, flow_item in enumerate(map_doc.data.get("flows", [])):
            if not isinstance(flow_item, dict):
                continue
            if isinstance(flow_item.get("id"), str):
                check_reference(errors, map_doc.path, f"flows[{index}].id", flow_item["id"], known_flow_ids)
            for node_id in flow_item.get("nodes", []):
                if isinstance(node_id, str):
                    check_reference(errors, map_doc.path, f"flows[{index}].nodes", node_id, known_node_ids)

        for index, transfer_node in enumerate(map_doc.data.get("transfer_nodes", [])):
            if not isinstance(transfer_node, dict):
                continue
            if isinstance(transfer_node.get("id"), str):
                check_reference(errors, map_doc.path, f"transfer_nodes[{index}].id", transfer_node["id"], known_node_ids)
            for flow_id in transfer_node.get("connects", []):
                if isinstance(flow_id, str):
                    check_reference(errors, map_doc.path, f"transfer_nodes[{index}].connects", flow_id, known_flow_ids)

        for index, impact_rule in enumerate(map_doc.data.get("impact_rules", [])):
            if not isinstance(impact_rule, dict):
                continue
            if isinstance(impact_rule.get("node"), str):
                check_reference(errors, map_doc.path, f"impact_rules[{index}].node", impact_rule["node"], known_node_ids)
            for flow_id in impact_rule.get("affects", []):
                if isinstance(flow_id, str):
                    check_reference(errors, map_doc.path, f"impact_rules[{index}].affects", flow_id, known_flow_ids)

    return errors


def flow_references_node(flow_card: LoadedDocument, node_id: str) -> bool:
    if not isinstance(flow_card.data, dict):
        return False

    direct_lists = (
        flow_card.data.get("entry_points", []),
        flow_card.data.get("anchor_nodes", []),
    )
    if any(node_id in values for values in direct_lists if isinstance(values, list)):
        return True

    for step in flow_card.data.get("steps", []):
        if not isinstance(step, dict):
            continue
        for field in ("from", "to", "actor", "target", "store", "service"):
            if step.get(field) == node_id:
                return True

    for item in flow_card.data.get("persistence", []):
        if isinstance(item, dict) and item.get("id") == node_id:
            return True

    for item in flow_card.data.get("return_paths", []):
        if not isinstance(item, dict):
            continue
        if item.get("from") == node_id or item.get("to") == node_id:
            return True

    return False


def find_flow_ids_for_node(project: ProjectData, node_id: str) -> list[str]:
    flow_ids: set[str] = set()

    for flow_card in project.flow_cards:
        flow_id = flow_card.data.get("id") if isinstance(flow_card.data, dict) else None
        if isinstance(flow_id, str) and flow_references_node(flow_card, node_id):
            flow_ids.add(flow_id)

    node_doc = project.nodes_by_id.get(node_id)
    if node_doc and isinstance(node_doc.data, dict):
        for flow_id in node_doc.data.get("owned_by_flows", []):
            if isinstance(flow_id, str):
                flow_ids.add(flow_id)

    if isinstance(project.map_doc.data, dict):
        for item in project.map_doc.data.get("flows", []):
            if not isinstance(item, dict):
                continue
            flow_id = item.get("id")
            nodes = item.get("nodes", [])
            if isinstance(flow_id, str) and isinstance(nodes, list) and node_id in nodes:
                flow_ids.add(flow_id)

    return sorted(flow_ids)


def format_validation_errors(error: ValidationError) -> str:
    return "\n".join(error.errors)
