#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from flow_memory_stats import analyze_log_directory, format_log_analysis


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Flow Memory helper logs.")
    parser.add_argument(
        "--project-root",
        default=DEFAULT_PROJECT_ROOT,
        type=Path,
        help="Project root containing flow_memory_logs/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    analysis = analyze_log_directory(args.project_root)
    print(format_log_analysis(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
