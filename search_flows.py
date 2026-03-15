#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flow_memory import DependencyError, ValidationError, format_validation_errors, load_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search Flow Cards by keyword in ID, name, or goal.")
    parser.add_argument("keyword", help="Case-insensitive keyword to search for.")
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

    keyword = args.keyword.casefold()
    matches = []
    for document in project.flow_cards:
        flow_id = str(document.data["id"])
        name = str(document.data["name"])
        goal = str(document.data["goal"])
        haystack = f"{name}\n{goal}".casefold()
        if keyword in haystack:
            matches.append((flow_id, name, document.data["status"], goal))

    if not matches:
        print(f"No flows matched `{args.keyword}`.")
        return 0

    for flow_id, name, status, goal in sorted(matches):
        print(f"{flow_id} | {name} | {status}")
        print(f"  goal: {goal}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
