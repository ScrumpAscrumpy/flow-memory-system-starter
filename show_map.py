#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flow_memory import DependencyError, ValidationError, format_validation_errors, load_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show transfer nodes and impact rules from the Metro Map.")
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

    map_data = project.map_doc.data

    print("Transfer Nodes")
    transfer_nodes = map_data.get("transfer_nodes", [])
    if not transfer_nodes:
        print("  (none)")
    else:
        for item in transfer_nodes:
            notes = f" | notes: {item['notes']}" if item.get("notes") else ""
            connects = ", ".join(item["connects"])
            print(f"- {item['id']} -> {connects}{notes}")

    print("")
    print("Impact Rules")
    impact_rules = map_data.get("impact_rules", [])
    if not impact_rules:
        print("  (none)")
    else:
        for item in impact_rules:
            notes = f" | notes: {item['notes']}" if item.get("notes") else ""
            affects = ", ".join(item["affects"])
            print(f"- {item['node']} -> {affects}{notes}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
