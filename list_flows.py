#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flow_memory import DependencyError, ValidationError, format_validation_errors, load_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Flow Cards with ID, name, and status.")
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

    if not project.flow_cards:
        print("No Flow Cards found.")
        return 0

    rows = [
        (
            str(document.data["id"]),
            str(document.data["name"]),
            str(document.data["status"]),
        )
        for document in sorted(project.flow_cards, key=lambda item: item.data["id"])
    ]

    id_width = max(len("ID"), *(len(row[0]) for row in rows))
    name_width = max(len("Name"), *(len(row[1]) for row in rows))
    status_width = max(len("Status"), *(len(row[2]) for row in rows))

    print(f"{'ID':<{id_width}}  {'Name':<{name_width}}  {'Status':<{status_width}}")
    print(f"{'-' * id_width}  {'-' * name_width}  {'-' * status_width}")
    for flow_id, name, status in rows:
        print(f"{flow_id:<{id_width}}  {name:<{name_width}}  {status:<{status_width}}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
