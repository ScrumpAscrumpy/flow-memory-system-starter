#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flow_memory import (
    DependencyError,
    ValidationError,
    find_flow_ids_for_node,
    format_validation_errors,
    load_project,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List flows that reference a specific node ID.")
    parser.add_argument("node_id", help="Node ID to search for.")
    parser.add_argument(
        "--project-root",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Project root containing flows/ and schemas/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project = load_project(args.project_root)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(format_validation_errors(exc), file=sys.stderr)
        return 1

    flow_ids = find_flow_ids_for_node(project, args.node_id)
    if not flow_ids:
        print(f"No flows reference `{args.node_id}`.")
        return 0

    for flow_id in flow_ids:
        flow_card = project.flow_cards_by_id.get(flow_id)
        if flow_card and isinstance(flow_card.data, dict):
            print(f"{flow_id} | {flow_card.data['name']} | {flow_card.data['status']}")
        else:
            print(flow_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
