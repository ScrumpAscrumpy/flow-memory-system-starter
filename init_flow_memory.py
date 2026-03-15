#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from flow_memory_setup import initialize_flow_memory_project


DEFAULT_SOURCE_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize Flow Memory structure in a target project directory.")
    parser.add_argument("target_root", type=Path, help="Target project directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = initialize_flow_memory_project(args.target_root, source_root=DEFAULT_SOURCE_ROOT)

    print(f"Initialized Flow Memory in {args.target_root.resolve()}")
    print("")
    print("Created:")
    if result.created:
        for path in result.created:
            print(f"- {path}")
    else:
        print("- (none)")

    print("")
    print("Skipped:")
    if result.skipped:
        for path in result.skipped:
            print(f"- {path}")
    else:
        print("- (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
