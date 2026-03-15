from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOGS_DIRNAME = "flow_memory_logs"
METRIC_LABELS = {
    "matched_flow_count": "avg matched flows / 平均命中流程数",
    "anchor_file_count": "avg anchor files / 平均返回锚点文件数",
    "context_file_count": "avg context files / 平均上下文文件数",
    "elapsed_ms": "avg elapsed ms / 平均耗时(ms)",
    "input_tokens": "avg input tokens / 平均输入 tokens",
    "output_tokens": "avg output tokens / 平均输出 tokens",
    "total_tokens": "avg total tokens / 平均总 tokens",
}


@dataclass
class MetricSummary:
    average: float
    samples: int


@dataclass
class ActionStats:
    action: str
    calls: int
    successes: int
    metrics: dict[str, MetricSummary]


@dataclass
class LogAnalysis:
    project_root: Path
    logs_dir: Path
    logs_dir_exists: bool
    total_records: int
    actions: list[ActionStats]


def _coerce_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def load_log_records(logs_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(logs_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
    return records


def analyze_log_directory(project_root: Path | str) -> LogAnalysis:
    root = Path(project_root).resolve()
    logs_dir = root / LOGS_DIRNAME
    if not logs_dir.exists():
        return LogAnalysis(
            project_root=root,
            logs_dir=logs_dir,
            logs_dir_exists=False,
            total_records=0,
            actions=[],
        )

    records = load_log_records(logs_dir)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("action", "unknown"))].append(record)

    action_stats: list[ActionStats] = []
    for action in sorted(grouped):
        items = grouped[action]
        metrics: dict[str, MetricSummary] = {}
        for field in METRIC_LABELS:
            values = [_coerce_numeric(item.get(field)) for item in items]
            present_values = [value for value in values if value is not None]
            if not present_values:
                continue
            metrics[field] = MetricSummary(
                average=sum(present_values) / len(present_values),
                samples=len(present_values),
            )

        action_stats.append(
            ActionStats(
                action=action,
                calls=len(items),
                successes=sum(1 for item in items if item.get("success") is True),
                metrics=metrics,
            )
        )

    return LogAnalysis(
        project_root=root,
        logs_dir=logs_dir,
        logs_dir_exists=True,
        total_records=len(records),
        actions=action_stats,
    )


def format_log_analysis(analysis: LogAnalysis) -> str:
    lines = [
        "Flow Memory Savings Stats / 节省统计",
        f"Project / 项目: {analysis.project_root}",
        f"Logs Directory / 日志目录: {analysis.logs_dir}",
    ]

    if not analysis.logs_dir_exists:
        lines.append("")
        lines.append("No logs directory found yet. Run helper actions first to collect usage data.")
        lines.append("还没有日志目录。请先使用辅助功能，系统才会开始记录使用数据。")
        return "\n".join(lines)

    lines.append(f"Log records / 日志条数: {analysis.total_records}")
    if analysis.total_records == 0:
        lines.append("")
        lines.append("No log records found yet.")
        lines.append("还没有日志记录。")
        return "\n".join(lines)

    for action in analysis.actions:
        lines.append("")
        lines.append(action.action)
        success_rate = (action.successes / action.calls) * 100 if action.calls else 0.0
        lines.append(f"  calls / 调用次数: {action.calls}")
        lines.append(
            f"  success rate / 成功率: {action.successes}/{action.calls} ({success_rate:.1f}%)"
        )
        for field, label in METRIC_LABELS.items():
            summary = action.metrics.get(field)
            if summary is None:
                continue
            suffix = f" ({summary.samples} record(s))" if summary.samples != action.calls else ""
            lines.append(f"  {label}: {summary.average:.2f}{suffix}")

    return "\n".join(lines)
