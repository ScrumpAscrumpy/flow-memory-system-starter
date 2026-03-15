#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from flow_memory import DependencyError, ProjectData, ValidationError, load_project


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIRNAME = "flow_memory_logs"
TOKEN_RE = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "after",
    "all",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "not",
    "of",
    "on",
    "or",
    "the",
    "to",
    "user",
    "with",
}

TERM_ALIASES = {
    "save": {"persist", "saved"},
    "saved": {"save", "persist"},
    "persist": {"save", "saved", "storage"},
    "refresh": {"reload", "update", "hydrate"},
    "reload": {"refresh", "load"},
    "delete": {"remove", "deleted"},
    "remove": {"delete", "deleted"},
    "record": {"records", "text_record"},
    "records": {"record", "text_record"},
    "list": {"record_list", "page.records_list"},
    "button": {"ui"},
    "editor": {"page.records_editor"},
    "refreshes": {"refresh"},
    "保存": {"save", "persist", "saved"},
    "刷新": {"refresh", "reload", "update"},
    "按钮": {"button", "ui"},
    "列表": {"list", "record_list"},
    "记录": {"record", "records", "text_record"},
    "新建": {"create", "new", "record"},
    "创建": {"create", "new"},
    "删除": {"delete", "remove"},
    "更新": {"update", "refresh"},
}

PHRASE_ALIASES = {
    "没有作用": {"refresh", "button"},
    "不更新": {"update", "refresh"},
    "未更新": {"update", "refresh"},
    "不生效": {"refresh", "button"},
    "not working": {"refresh", "button"},
    "does not work": {"refresh", "button"},
    "not reflected": {"delete", "refresh"},
    "列表不更新": {"list", "update", "refresh"},
    "保存后列表不更新": {"save", "list", "update", "refresh"},
}

FIELD_WEIGHTS = {
    "id": 1,
    "name": 4,
    "goal": 4,
    "watch_points": 3,
    "common_failures": 5,
    "triggers": 2,
    "entry_points": 1,
    "anchor_nodes": 1,
    "notes": 1,
}

WORD_TRANSLATIONS = {
    "home": "首页",
    "index": "首页",
    "route": "页面",
    "page": "页面",
    "record": "记录",
    "records": "记录",
    "list": "列表",
    "editor": "编辑",
    "save": "保存",
    "saved": "已保存",
    "delete": "删除",
    "deleted": "已删除",
    "refresh": "刷新",
    "reload": "重新加载",
    "back": "返回",
    "input": "输入",
    "button": "按钮",
    "text": "文本",
    "repository": "仓库",
    "service": "服务",
    "state": "状态",
    "entity": "实体",
    "persistence": "存储",
    "create": "创建",
    "new": "新建",
    "to": "到",
    "form": "表单",
    "editorpage": "编辑页面",
    "listpage": "列表页面",
}
WORD_RE = re.compile(r"[A-Za-z]+|\d+|[\u4e00-\u9fff]+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class FlowSuggestion:
    flow_id: str
    name: str
    status: str
    score: int
    matched_terms: list[str]
    anchor_files: list[str]


def _contains_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


def _split_words(raw: str) -> list[str]:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    normalized = re.sub(r"[_:.\-\/]+", " ", normalized)
    return [word.casefold() for word in WORD_RE.findall(normalized)]


def _translate_words(words: list[str]) -> list[str]:
    translated: list[str] = []
    for word in words:
        if len(word) == 1 and word.isalpha():
            translated.append(word.upper())
            continue
        translated.append(WORD_TRANSLATIONS.get(word, word))
    return translated


def _join_display_words(words: list[str]) -> str:
    if not words:
        return ""
    if all(_contains_cjk(word) or (len(word) == 1 and word.isalnum()) for word in words):
        return "".join(words)
    return " ".join(words)


def _friendly_label_for_node(node_id: str, project: ProjectData | None = None) -> str:
    node_type = ""
    raw_name = ""
    document = project.nodes_by_id.get(node_id) if project is not None else None
    if document and isinstance(document.data, dict):
        raw_name = str(document.data.get("name", "")).strip()
        node_type = str(document.data.get("type", "")).strip()

    if raw_name and _contains_cjk(raw_name):
        return raw_name

    if not node_type and "." in node_id:
        node_type, _, remainder = node_id.partition(".")
    elif not node_type and ":" in node_id:
        node_type, _, remainder = node_id.partition(":")
    else:
        remainder = node_id

    words = _split_words(raw_name or remainder)
    translated_words = _translate_words(words)

    if node_type in {"route", "page"}:
        meaningful = [word for word in translated_words if word not in {"页面", "页", "route", "page"}]
        if any(word == "首页" for word in meaningful):
            return "首页"
        body = _join_display_words(meaningful) or _join_display_words(translated_words) or node_id
        if len(body) <= 2 and body.isalnum():
            return f"页面{body}"
        return f"{body}页面"

    if node_type == "ui":
        if words and words[-1] == "button":
            body_words = translated_words[:-1]
            body = _join_display_words(body_words)
            if len(body_words) == 1 and len(body) == 1 and body.isalnum():
                return f"按钮{body}"
            return f"{body}按钮" if body else "按钮"
        if words and words[-1] == "input":
            body = _join_display_words(translated_words[:-1])
            return f"{body}输入框" if body else "输入框"
        body = _join_display_words(translated_words)
        return body or node_id

    suffix_map = {
        "state": "状态",
        "service": "服务",
        "entity": "",
        "persistence": "存储",
    }
    suffix = suffix_map.get(node_type, "")
    body_words = [
        word for word in translated_words if word not in {"状态", "服务", "实体", "存储"}
    ]
    body = _join_display_words(body_words) or _join_display_words(translated_words)
    if suffix and body.endswith(suffix):
        return body
    if suffix:
        return f"{body}{suffix}"
    return body or raw_name or node_id


def _append_unique(chain: list[str], value: str | None) -> None:
    if not value:
        return
    if not chain or chain[-1] != value:
        chain.append(value)


def _build_flow_chain(flow_data: dict[str, Any]) -> list[str]:
    chain: list[str] = []
    for entry in flow_data.get("entry_points", []):
        if isinstance(entry, str):
            _append_unique(chain, entry)

    for step in flow_data.get("steps", []):
        if not isinstance(step, dict):
            continue
        _append_unique(chain, step.get("from") if isinstance(step.get("from"), str) else None)
        _append_unique(chain, step.get("actor") if isinstance(step.get("actor"), str) else None)
        if isinstance(step.get("to"), str):
            _append_unique(chain, step["to"])
        elif isinstance(step.get("target"), str):
            _append_unique(chain, step["target"])

    for return_path in flow_data.get("return_paths", []):
        if not isinstance(return_path, dict):
            continue
        _append_unique(chain, return_path.get("from") if isinstance(return_path.get("from"), str) else None)
        trigger = return_path.get("trigger")
        if isinstance(trigger, str):
            _append_unique(chain, trigger)
        _append_unique(chain, return_path.get("to") if isinstance(return_path.get("to"), str) else None)

    return chain


def describe_flow(
    flow_data: dict[str, Any],
    project: ProjectData | None = None,
) -> str:
    chain = _build_flow_chain(flow_data)
    if not chain:
        return "当前 Flow 没有可描述的跳转链路。"

    labels: list[str] = []
    for node_id in chain:
        label = _friendly_label_for_node(node_id, project)
        if not labels or labels[-1] != label:
            labels.append(label)
    return " → ".join(labels) + "。"


def describe_flow_steps(
    flow_data: dict[str, Any],
    project: ProjectData | None = None,
) -> list[str]:
    lines: list[str] = []
    step_index = 1

    for step in flow_data.get("steps", []):
        if not isinstance(step, dict):
            continue
        from_label = _friendly_label_for_node(step["from"], project) if isinstance(step.get("from"), str) else ""
        actor_label = _friendly_label_for_node(step["actor"], project) if isinstance(step.get("actor"), str) else ""
        target_value = step.get("to") if isinstance(step.get("to"), str) else step.get("target")
        target_label = _friendly_label_for_node(target_value, project) if isinstance(target_value, str) else ""
        action = str(step.get("action", "")).strip()

        if from_label and actor_label and target_label:
            lines.append(f"{step_index}. 从{from_label}点击或触发{actor_label}，到达{target_label}。")
        elif actor_label and target_label:
            lines.append(f"{step_index}. 通过{actor_label}操作，进入{target_label}。")
        elif target_label:
            lines.append(f"{step_index}. 执行{action or '该步骤'}，进入{target_label}。")
        elif actor_label:
            lines.append(f"{step_index}. 执行{action or '该步骤'}，涉及{actor_label}。")
        else:
            lines.append(f"{step_index}. 执行{action or '该步骤'}。")
        step_index += 1

    for return_path in flow_data.get("return_paths", []):
        if not isinstance(return_path, dict):
            continue
        from_label = _friendly_label_for_node(return_path["from"], project) if isinstance(return_path.get("from"), str) else ""
        trigger_label = _friendly_label_for_node(return_path["trigger"], project) if isinstance(return_path.get("trigger"), str) else ""
        to_label = _friendly_label_for_node(return_path["to"], project) if isinstance(return_path.get("to"), str) else ""

        if from_label and trigger_label and to_label:
            lines.append(f"{step_index}. 从{from_label}通过{trigger_label}返回到{to_label}。")
        elif from_label and to_label:
            lines.append(f"{step_index}. 从{from_label}返回到{to_label}。")
        step_index += 1

    return lines


def _resolve_project_root(project_root: Path | str | None = None) -> Path:
    return Path(project_root or DEFAULT_PROJECT_ROOT).resolve()


def _load(project_root: Path | str | None = None) -> ProjectData:
    root = _resolve_project_root(project_root)
    return load_project(root)


def _log_event(
    *,
    action: str,
    project_root: Path,
    input_value: str,
    matched_flow_count: int,
    anchor_file_count: int,
    elapsed_ms: float,
    success: bool,
    flow_ids: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    timestamp = datetime.now().astimezone()
    logs_dir = project_root / LOGS_DIRNAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{timestamp.date().isoformat()}.jsonl"

    payload: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "action": action,
        "project_root": str(project_root),
        "input": input_value,
        "input_length_chars": len(input_value),
        "matched_flow_count": matched_flow_count,
        "anchor_file_count": anchor_file_count,
        "elapsed_ms": round(elapsed_ms, 3),
        "success": success,
    }
    if flow_ids is not None:
        payload["flow_ids"] = flow_ids
    if extra:
        payload.update(extra)

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _build_log_extra(
    base: dict[str, Any] | None = None,
    *,
    context_file_count: int | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    extra: dict[str, Any] = dict(base or {})
    if context_file_count is not None:
        extra["context_file_count"] = context_file_count

    for key, value in (metrics or {}).items():
        if value is None:
            continue
        extra[key] = value

    return extra or None


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall(text.casefold())
        if len(token) > 1 and token not in STOPWORDS
    }


def _expand_terms(terms: set[str], raw_text: str) -> set[str]:
    expanded = set(terms)
    for term in list(terms):
        expanded.update(TERM_ALIASES.get(term, set()))

    lowered = raw_text.casefold()
    for phrase, aliases in PHRASE_ALIASES.items():
        if phrase in lowered:
            expanded.update(aliases)

    return expanded


def _value_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_value_to_text(item) for item in value if item is not None)
    if isinstance(value, dict):
        return " ".join(_value_to_text(item) for item in value.values() if item is not None)
    return ""


def _flow_score(flow_data: dict[str, Any], query_terms: set[str], raw_description: str) -> tuple[int, list[str]]:
    score = 0
    matched_terms: set[str] = set()

    for field, weight in FIELD_WEIGHTS.items():
        value = flow_data.get(field)
        if value is None:
            continue
        field_terms = _expand_terms(_tokenize(_value_to_text(value)), _value_to_text(value))
        overlap = query_terms & field_terms
        if overlap:
            score += len(overlap) * weight
            matched_terms.update(overlap)

    description = raw_description.casefold().strip()
    for field in ("name", "goal"):
        value = str(flow_data.get(field, "")).casefold()
        if description and description in value:
            score += 6

    for item in flow_data.get("common_failures", []):
        if isinstance(item, str) and description and description in item.casefold():
            score += 8

    return score, sorted(matched_terms)


def _load_flow_data(flow_id: str, project_root: Path | str | None = None) -> tuple[ProjectData, dict[str, Any]]:
    project = _load(project_root)
    document = project.flow_cards_by_id.get(flow_id)
    if document is None:
        raise KeyError(f"Unknown flow ID: {flow_id}")
    return project, document.data


def load_flow(
    flow_id: str,
    project_root: Path | str | None = None,
    *,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_root = _resolve_project_root(project_root)
    started = time.perf_counter()
    try:
        project, flow_data = _load_flow_data(flow_id, resolved_root)
    except Exception:
        _log_event(
            action="load_flow",
            project_root=resolved_root,
            input_value=flow_id,
            matched_flow_count=0,
            anchor_file_count=0,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            success=False,
        )
        raise

    anchor_files = list(flow_data.get("anchor_files", []))
    _log_event(
        action="load_flow",
        project_root=resolved_root,
        input_value=flow_id,
        matched_flow_count=1,
        anchor_file_count=len(anchor_files),
        elapsed_ms=(time.perf_counter() - started) * 1000,
        success=True,
        flow_ids=[flow_id],
        extra=_build_log_extra(
            {"status": flow_data.get("status", "")},
            context_file_count=len(anchor_files),
            metrics=metrics,
        ),
    )
    return flow_data


def get_anchor_files(
    flow_id: str,
    project_root: Path | str | None = None,
    *,
    metrics: dict[str, Any] | None = None,
) -> list[str]:
    resolved_root = _resolve_project_root(project_root)
    started = time.perf_counter()
    try:
        _project, flow_data = _load_flow_data(flow_id, resolved_root)
    except Exception:
        _log_event(
            action="get_anchor_files",
            project_root=resolved_root,
            input_value=flow_id,
            matched_flow_count=0,
            anchor_file_count=0,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            success=False,
        )
        raise

    anchor_files = list(flow_data.get("anchor_files", []))
    _log_event(
        action="get_anchor_files",
        project_root=resolved_root,
        input_value=flow_id,
        matched_flow_count=1,
        anchor_file_count=len(anchor_files),
        elapsed_ms=(time.perf_counter() - started) * 1000,
        success=True,
        flow_ids=[flow_id],
        extra=_build_log_extra(
            {"status": flow_data.get("status", "")},
            context_file_count=len(anchor_files),
            metrics=metrics,
        ),
    )
    return anchor_files


def print_anchor_files(flow_id: str, project_root: Path | str | None = None) -> list[str]:
    anchor_files = get_anchor_files(flow_id, project_root)
    for path in anchor_files:
        print(path)
    return anchor_files


def suggest_flows_for_bug(
    description: str,
    project_root: Path | str | None = None,
    limit: int = 3,
    *,
    metrics: dict[str, Any] | None = None,
) -> list[FlowSuggestion]:
    resolved_root = _resolve_project_root(project_root)
    started = time.perf_counter()
    try:
        project = _load(resolved_root)
        query_terms = _expand_terms(_tokenize(description), description)
        if not query_terms and description.strip():
            query_terms = {description.casefold().strip()}
        if not query_terms:
            _log_event(
                action="suggest_flows_for_bug",
                project_root=resolved_root,
                input_value=description,
                matched_flow_count=0,
                anchor_file_count=0,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                success=True,
                flow_ids=[],
                extra=_build_log_extra({"limit": limit}, context_file_count=0, metrics=metrics),
            )
            return []

        suggestions: list[FlowSuggestion] = []
        for document in project.flow_cards:
            if not isinstance(document.data, dict):
                continue
            score, matched_terms = _flow_score(document.data, query_terms, description)
            if score <= 0:
                continue
            suggestions.append(
                FlowSuggestion(
                    flow_id=str(document.data["id"]),
                    name=str(document.data["name"]),
                    status=str(document.data["status"]),
                    score=score,
                    matched_terms=matched_terms,
                    anchor_files=list(document.data.get("anchor_files", [])),
                )
            )

        suggestions.sort(key=lambda item: (-item.score, item.flow_id))
        trimmed = suggestions[:limit]
    except Exception:
        _log_event(
            action="suggest_flows_for_bug",
            project_root=resolved_root,
            input_value=description,
            matched_flow_count=0,
            anchor_file_count=0,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            success=False,
            flow_ids=[],
            extra=_build_log_extra({"limit": limit}, context_file_count=0, metrics=metrics),
        )
        raise

    unique_anchor_files = {path for item in trimmed for path in item.anchor_files}
    _log_event(
        action="suggest_flows_for_bug",
        project_root=resolved_root,
        input_value=description,
        matched_flow_count=len(trimmed),
        anchor_file_count=len(unique_anchor_files),
        elapsed_ms=(time.perf_counter() - started) * 1000,
        success=True,
        flow_ids=[item.flow_id for item in trimmed],
        extra=_build_log_extra(
            {"limit": limit},
            context_file_count=len(unique_anchor_files),
            metrics=metrics,
        ),
    )
    return trimmed


def suggest_files_for_bug(
    description: str,
    project_root: Path | str | None = None,
    limit: int = 3,
) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    for suggestion in suggest_flows_for_bug(description, project_root=project_root, limit=limit):
        for path in suggestion.anchor_files:
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _print_validation_error(exc: ValidationError) -> None:
    for error in exc.errors:
        print(error, file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local helper for simulating Flow Memory AI behavior.")
    parser.add_argument(
        "--project-root",
        default=DEFAULT_PROJECT_ROOT,
        type=Path,
        help="Project root containing flows/ and schemas/.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser("load", help="Load a Flow Card and print its JSON.")
    load_parser.add_argument("flow_id", help="Flow ID to load.")

    files_parser = subparsers.add_parser("files", help="Print anchor_files for a Flow Card.")
    files_parser.add_argument("flow_id", help="Flow ID to inspect.")

    suggest_parser = subparsers.add_parser("suggest", help="Suggest flows and anchor files for a bug description.")
    suggest_parser.add_argument("description", help="Bug description or requirement summary.")
    suggest_parser.add_argument("--limit", type=int, default=3, help="Maximum number of matching flows to return.")

    describe_parser = subparsers.add_parser("describe", help="Describe a flow as a human-readable narrative.")
    describe_parser.add_argument("flow_id", help="Flow ID to describe.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "load":
            flow_data = load_flow(args.flow_id, project_root=args.project_root)
            print(json.dumps(flow_data, indent=2))
            return 0

        if args.command == "files":
            print_anchor_files(args.flow_id, project_root=args.project_root)
            return 0

        if args.command == "suggest":
            suggestions = suggest_flows_for_bug(
                args.description,
                project_root=args.project_root,
                limit=args.limit,
            )
            if not suggestions:
                print("No matching flows found.")
                return 0

            for suggestion in suggestions:
                print(
                    f"{suggestion.flow_id} | {suggestion.name} | {suggestion.status} | "
                    f"score={suggestion.score} | matched={', '.join(suggestion.matched_terms)}"
                )
                for path in suggestion.anchor_files:
                    print(f"  {path}")
            return 0

        if args.command == "describe":
            project, flow_data = _load_flow_data(args.flow_id, args.project_root)
            print(describe_flow(flow_data, project))
            detail_lines = describe_flow_steps(flow_data, project)
            if detail_lines:
                print("")
                for line in detail_lines:
                    print(line)
            return 0

    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValidationError as exc:
        _print_validation_error(exc)
        return 1
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
