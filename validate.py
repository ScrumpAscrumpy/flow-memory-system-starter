#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flow_memory import DependencyError, ValidationError, format_validation_errors, load_project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Flow Memory YAML files.")
    parser.add_argument(
        "project_root",
        nargs="?",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Project root containing flows/ and schemas/ (defaults to this script's directory).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        project = load_project(args.project_root.resolve())
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(format_validation_errors(exc), file=sys.stderr)
        return 1

    print(
        f"Validation passed: {len(project.flow_cards)} flow card(s), "
        f"{len(project.nodes)} node(s), and 1 map file checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
