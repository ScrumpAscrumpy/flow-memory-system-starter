#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_helper import get_anchor_files, suggest_flows_for_bug


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent


def plan_context_for_issue(
    description: str,
    *,
    project_root: Path | str | None = None,
    limit: int = 3,
) -> dict:
    suggestions = suggest_flows_for_bug(description, project_root=project_root, limit=limit)
    plan = {
        "description": description,
        "flows": [],
        "files_to_read_first": [],
    }

    seen_files: set[str] = set()
    for suggestion in suggestions:
        anchor_files = get_anchor_files(suggestion.flow_id, project_root=project_root)
        plan["flows"].append(
            {
                "flow_id": suggestion.flow_id,
                "name": suggestion.name,
                "status": suggestion.status,
                "score": suggestion.score,
                "matched_terms": suggestion.matched_terms,
                "anchor_files": anchor_files,
            }
        )
        for path in anchor_files:
            if path not in seen_files:
                seen_files.add(path)
                plan["files_to_read_first"].append(path)

    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demonstrate how Codex can use Flow Memory before editing code.")
    parser.add_argument("description", help="Bug description or requirement summary.")
    parser.add_argument(
        "--project-root",
        default=DEFAULT_PROJECT_ROOT,
        type=Path,
        help="Project root containing flows/ and schemas/.",
    )
    parser.add_argument("--limit", type=int, default=3, help="Maximum number of candidate flows to include.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = plan_context_for_issue(args.description, project_root=args.project_root, limit=args.limit)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
