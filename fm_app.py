#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog

from ai_helper import describe_flow, describe_flow_steps, load_flow, suggest_flows_for_bug
from flow_memory import DependencyError, ValidationError, find_flow_ids_for_node, load_project
from flow_memory_setup import (
    find_missing_flow_memory_components,
    initialize_flow_memory_project,
    load_app_config,
    save_app_config,
)
from flow_memory_stats import analyze_log_directory, format_log_analysis


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent


def ensure_supported_tk_runtime() -> None:
    executable = Path(sys.executable).resolve()
    is_apple_clt_python = str(executable).startswith("/Library/Developer/CommandLineTools/")
    tk_version = getattr(tk, "TkVersion", 0)

    if platform.system() == "Darwin" and is_apple_clt_python and tk_version < 8.6:
        raise RuntimeError(
            "The current Python runtime uses Apple's bundled Tk 8.5, which crashes on this macOS version.\n\n"
            f"Current interpreter: {executable}\n\n"
            "Please run the app with the project virtual environment instead:\n"
            "  ./.venv/bin/python fm_app.py\n"
            "or:\n"
            "  ./run_fm_app.command\n\n"
            "If the virtual environment does not exist yet, create it with a Homebrew Python:\n"
            "  /opt/homebrew/bin/python3.13 -m venv .venv\n"
            "  ./.venv/bin/python -m pip install -r requirements.txt"
        )


class SelectionDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        prompt: str,
        options: list[tuple[str, str]],
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result: str | None = None

        tk.Label(self, text=prompt, justify=tk.LEFT, anchor="w").pack(
            fill=tk.X, padx=12, pady=(12, 6)
        )

        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            frame,
            width=72,
            height=min(max(len(options), 8), 14),
            yscrollcommand=scrollbar.set,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        for item_id, item_name in options:
            label = f"{item_id} | {item_name}" if item_name else item_id
            self.listbox.insert(tk.END, label)

        self._ids = [item_id for item_id, _ in options]

        button_row = tk.Frame(self)
        button_row.pack(fill=tk.X, padx=12, pady=(0, 12))
        tk.Button(button_row, text="OK / 确定", command=self._on_confirm).pack(side=tk.LEFT)
        tk.Button(button_row, text="Cancel / 取消", command=self._on_cancel).pack(side=tk.LEFT, padx=(8, 0))

        self.listbox.bind("<Double-Button-1>", lambda _event: self._on_confirm())
        self.listbox.bind("<Return>", lambda _event: self._on_confirm())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        if options:
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def _on_confirm(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.result = self._ids[selection[0]]
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    @classmethod
    def choose(
        cls,
        parent: tk.Misc,
        *,
        title: str,
        prompt: str,
        options: list[tuple[str, str]],
    ) -> str | None:
        dialog = cls(parent, title=title, prompt=prompt, options=options)
        parent.wait_window(dialog)
        return dialog.result


class FlowMemoryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Flow Memory System")
        self.geometry("980x680")
        self.minsize(820, 520)

        self.project_root: Path | None = None
        self.code_root: Path | None = None
        self.project_data = None

        self._build_menu()
        self._build_layout()
        self._load_startup_configuration()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        project_menu = tk.Menu(menubar, tearoff=0)
        project_menu.add_command(label="Import Project / 导入项目", command=self.import_project)
        project_menu.add_command(label="Open... / 打开项目", command=self.choose_project)
        project_menu.add_command(label="Set Code Directory / 设置代码目录", command=self.choose_code_directory)
        project_menu.add_command(label="Initialize Flow Memory / 初始化 Flow Memory", command=self.initialize_project)
        project_menu.add_command(label="Reload / 重新加载", command=self.validate_project)
        project_menu.add_separator()
        project_menu.add_command(label="Exit / 退出", command=self.destroy)
        menubar.add_cascade(label="Project / 项目", menu=project_menu)

        self.config(menu=menubar)

    def _build_layout(self) -> None:
        top = tk.Frame(self, padx=12, pady=10)
        top.pack(fill=tk.X)

        self.project_var = tk.StringVar(value="Project / 项目: (not loaded)")
        self.code_var = tk.StringVar(value="Code Directory / 代码目录: (not set)")
        self.status_var = tk.StringVar(value="Ready / 就绪")

        tk.Label(
            top,
            textvariable=self.project_var,
            anchor="w",
            justify=tk.LEFT,
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill=tk.X)
        tk.Label(top, textvariable=self.code_var, anchor="w", justify=tk.LEFT).pack(fill=tk.X, pady=(2, 0))
        tk.Label(top, textvariable=self.status_var, anchor="w", justify=tk.LEFT).pack(fill=tk.X, pady=(4, 0))

        buttons = tk.Frame(self, padx=12, pady=4)
        buttons.pack(fill=tk.X)

        primary_row = tk.Frame(buttons)
        primary_row.pack(fill=tk.X, pady=(0, 2))

        import_button = tk.Button(
            primary_row,
            text="Import Project / 导入项目",
            command=self.import_project,
            font=("TkDefaultFont", 10, "bold"),
            width=22,
        )
        import_button.pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Button(
            primary_row,
            text="Validate Project / 验证项目",
            command=self.validate_project,
        ).pack(side=tk.LEFT, padx=(0, 8), pady=4)
        tk.Button(
            primary_row,
            text="View Savings Stats / 查看节省统计",
            command=self.view_savings_stats,
        ).pack(side=tk.LEFT, padx=(0, 8), pady=4)

        secondary_row = tk.Frame(buttons)
        secondary_row.pack(fill=tk.X)

        button_specs = [
            ("List Flows / 列出流程", self.list_flows),
            ("Inspect Flow / 查看流程", self.inspect_flow),
            ("Describe Flow / 文字链路", self.describe_flow_view),
            ("Find Flow for Node / 查找流程(节点)", self.find_flow_for_node),
            ("Show Map / 显示地图", self.show_map),
            ("Suggest Flows / 推荐流程", self.suggest_flows),
        ]
        for label, command in button_specs:
            tk.Button(secondary_row, text=label, command=command).pack(side=tk.LEFT, padx=(0, 8), pady=4)

        self.output = scrolledtext.ScrolledText(self, wrap=tk.WORD, padx=12, pady=12)
        self.output.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

    def append_output(self, text: str = "") -> None:
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def clear_output(self) -> None:
        self.output.delete("1.0", tk.END)

    def _set_project_context(self, *, project_root: Path, code_root: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        self.code_root = (code_root or project_root).resolve()
        self.project_data = None
        self.project_var.set(f"Project / 项目: {self.project_root}")
        self.code_var.set(f"Code Directory / 代码目录: {self.code_root}")
        self._save_config()

    def _save_config(self) -> None:
        save_app_config(
            DEFAULT_PROJECT_ROOT,
            flow_memory_project_root=self.project_root,
            code_root=self.code_root,
        )

    def _load_startup_configuration(self) -> None:
        try:
            config = load_app_config(DEFAULT_PROJECT_ROOT)
        except DependencyError:
            config = None

        if config:
            if config.flow_memory_project_root and (config.flow_memory_project_root / "flows").is_dir():
                self.project_root = config.flow_memory_project_root
                self.project_var.set(f"Project / 项目: {self.project_root}")
            if config.code_root and config.code_root.exists():
                self.code_root = config.code_root
                self.code_var.set(f"Code Directory / 代码目录: {self.code_root}")

        self._load_default_project()

    def _load_default_project(self) -> None:
        if self.project_root is not None:
            self.append_output(f"Loaded configured project / 已加载配置项目: {self.project_root}")
            if self.validate_project(silent=True):
                return
            invalid_project = self.project_root
            self.project_root = None
            if self.code_root == invalid_project:
                self.code_root = None
                self.code_var.set("Code Directory / 代码目录: (not set)")
            self.project_var.set("Project / 项目: (not loaded)")
            self.append_output("")
            self.append_output(
                f"Configured project is invalid, falling back to local defaults / 配置项目无效，回退到本地默认目录: {invalid_project}"
            )

        candidates = [DEFAULT_PROJECT_ROOT, Path.cwd()]
        for candidate in candidates:
            if (candidate / "flows").is_dir() and (candidate / "schemas").is_dir():
                self.project_root = candidate.resolve()
                self.code_root = self.project_root
                self.project_var.set(f"Project / 项目: {self.project_root}")
                self.code_var.set(f"Code Directory / 代码目录: {self.code_root}")
                self.append_output(f"Loaded default project / 已加载默认项目: {self.project_root}")
                self._save_config()
                self.validate_project(silent=True)
                return

        self.append_output(
            "No default Flow Memory project found. Use Import Project / 导入项目 or Project / 项目 -> Open... / 打开项目."
        )

    def _handle_error(self, exc: Exception, *, title: str) -> None:
        if isinstance(exc, DependencyError):
            message = str(exc)
        elif isinstance(exc, ValidationError):
            message = "\n".join(exc.errors)
        else:
            message = str(exc)

        self.status_var.set("Operation failed / 操作失败")
        messagebox.showerror(title, message, parent=self)

    def _require_project(self) -> bool:
        if self.project_root is None:
            messagebox.showwarning(
                "No Project / 未打开项目",
                "Please import or open a project that contains flows/ and schemas/ first.\n请先导入或打开包含 flows/ 和 schemas/ 的项目目录。",
                parent=self,
            )
            return False
        return True

    def _ensure_loaded(self) -> bool:
        if not self._require_project():
            return False
        if self.project_data is None:
            self.validate_project(silent=True)
        return self.project_data is not None

    def _finish_project_load(self, heading: str, notes: list[str] | None = None) -> None:
        self.clear_output()
        self.append_output(heading)
        self.append_output("")
        self.append_output(f"Project / 项目: {self.project_root}")
        self.append_output(f"Code Directory / 代码目录: {self.code_root}")

        if notes:
            self.append_output("")
            for note in notes:
                self.append_output(note)

        if self.project_data is None:
            return

        self.append_output("")
        self.append_output(
            f"Validation successful / 验证成功: {len(self.project_data.flow_cards)} 条流程, "
            f"{len(self.project_data.nodes)} 个节点"
        )

    def _open_or_initialize_directory(self, selected: Path, *, heading: str) -> None:
        selected = selected.resolve()
        missing_components = find_missing_flow_memory_components(selected)
        notes: list[str] = []

        if missing_components:
            missing_text = ", ".join(missing_components)
            should_initialize = messagebox.askyesno(
                "Initialize Flow Memory? / 是否初始化 Flow Memory？",
                "The selected directory does not contain a complete Flow Memory layout.\n"
                "所选目录缺少完整的 Flow Memory 结构。\n\n"
                f"Missing / 缺少: {missing_text}\n\n"
                "Initialize the required flows/ and schemas/ files now?\n"
                "现在是否自动初始化所需的 flows/ 和 schemas/？",
                parent=self,
            )
            if not should_initialize:
                self.status_var.set("Import canceled / 已取消导入")
                self.clear_output()
                self.append_output(heading)
                self.append_output("")
                self.append_output(f"Selected directory / 已选择目录: {selected}")
                self.append_output(f"Missing components / 缺少组件: {missing_text}")
                self.append_output("Initialization skipped / 已跳过初始化。")
                return

            try:
                result = initialize_flow_memory_project(selected, source_root=DEFAULT_PROJECT_ROOT)
            except Exception as exc:
                self._handle_error(exc, title="Initialize Flow Memory / 初始化 Flow Memory")
                return

            notes.append(f"Initialized Flow Memory / 已初始化 Flow Memory: {selected}")
            notes.append(f"Missing components / 原缺少组件: {missing_text}")
            if result.created:
                notes.append("Created / 已创建:")
                notes.extend(f"- {path}" for path in result.created)
            if result.skipped:
                notes.append("Skipped / 已跳过:")
                notes.extend(f"- {path}" for path in result.skipped)
        else:
            notes.append("Existing Flow Memory structure detected / 已检测到现有 Flow Memory 结构。")

        self._set_project_context(project_root=selected, code_root=selected)
        if self.validate_project(silent=True):
            self.status_var.set("Project ready / 项目已就绪")
            self._finish_project_load(heading, notes)
            return

        existing_output = self.output.get("1.0", tk.END).strip()
        self.clear_output()
        self.append_output(heading)
        self.append_output("")
        self.append_output(f"Project / 项目: {self.project_root}")
        self.append_output(f"Code Directory / 代码目录: {self.code_root}")
        if notes:
            self.append_output("")
            for note in notes:
                self.append_output(note)
        if existing_output:
            self.append_output("")
            self.append_output(existing_output)
        self.status_var.set("Project validation failed / 项目验证失败")

    def import_project(self) -> None:
        selected = filedialog.askdirectory(
            parent=self,
            title="Import project root / 导入项目根目录",
            initialdir=str(self.code_root or self.project_root or DEFAULT_PROJECT_ROOT),
        )
        if not selected:
            return

        self._open_or_initialize_directory(
            Path(selected),
            heading="Import Project / 导入项目",
        )

    def choose_project(self) -> None:
        selected = filedialog.askdirectory(
            parent=self,
            title="Select Flow Memory project root / 选择项目根目录",
            initialdir=str(self.project_root or DEFAULT_PROJECT_ROOT),
        )
        if not selected:
            return

        self._open_or_initialize_directory(
            Path(selected),
            heading="Open Project / 打开项目",
        )

    def choose_code_directory(self) -> None:
        initial_dir = str(self.code_root or self.project_root or DEFAULT_PROJECT_ROOT)
        selected = filedialog.askdirectory(
            parent=self,
            title="Select code directory / 选择代码目录",
            initialdir=initial_dir,
        )
        if not selected:
            return

        self.code_root = Path(selected).resolve()
        self.code_var.set(f"Code Directory / 代码目录: {self.code_root}")
        self.status_var.set("Code directory selected / 已选择代码目录")
        self.append_output(f"Code directory / 代码目录: {self.code_root}")
        self._save_config()

    def initialize_project(self) -> None:
        selected = filedialog.askdirectory(
            parent=self,
            title="Select target directory to initialize / 选择要初始化的目录",
            initialdir=str(self.project_root or DEFAULT_PROJECT_ROOT),
        )
        if not selected:
            return

        target = Path(selected).resolve()
        try:
            result = initialize_flow_memory_project(target, source_root=DEFAULT_PROJECT_ROOT)
        except Exception as exc:
            self._handle_error(exc, title="Initialize Flow Memory / 初始化 Flow Memory")
            return

        self._set_project_context(project_root=target, code_root=target)

        self.clear_output()
        self.append_output(f"Initialized Flow Memory in / 已初始化: {target}")
        self.append_output("")
        self.append_output("Created / 已创建:")
        if result.created:
            for path in result.created:
                self.append_output(f"- {path}")
        else:
            self.append_output("(none / 无)")
        self.append_output("")
        self.append_output("Skipped / 已跳过:")
        if result.skipped:
            for path in result.skipped:
                self.append_output(f"- {path}")
        else:
            self.append_output("(none / 无)")

        if self.validate_project(silent=True):
            self.status_var.set("Flow Memory initialized / 已完成初始化")
        else:
            self.status_var.set("Flow Memory initialized, validation failed / 已初始化，但验证失败")

    def validate_project(self, silent: bool = False) -> bool:
        if not self._require_project():
            return False

        try:
            self.project_data = load_project(self.project_root)
        except (DependencyError, ValidationError) as exc:
            self.project_data = None
            if silent:
                self.clear_output()
                self.append_output("Validation failed / 验证失败：")
                if isinstance(exc, ValidationError):
                    for line in exc.errors:
                        self.append_output(line)
                else:
                    self.append_output(str(exc))
            else:
                self._handle_error(exc, title="Validation Error / 验证错误")
            return False
        except Exception as exc:
            self.project_data = None
            message = f"Unexpected validation error: {exc}"
            if silent:
                self.clear_output()
                self.append_output("Validation failed / 验证失败：")
                self.append_output(message)
            else:
                self._handle_error(exc, title="Validation Error / 验证错误")
            return False

        flow_count = len(self.project_data.flow_cards)
        node_count = len(self.project_data.nodes)
        self.status_var.set(f"Validation successful / 验证成功: {flow_count} 条流程, {node_count} 个节点")

        if not silent:
            self.clear_output()
            self.append_output(f"Project / 项目: {self.project_root}")
            self.append_output(f"Validation successful / 验证成功: {flow_count} 条流程, {node_count} 个节点")
        return True

    def list_flows(self) -> None:
        if not self._ensure_loaded():
            return

        self.clear_output()
        self.append_output("All Flows / 全部流程")
        self.append_output("")
        for document in sorted(self.project_data.flow_cards, key=lambda item: item.data["id"]):
            data = document.data
            self.append_output(f"- {data['id']}: {data['name']} ({data['status']})")

        self.append_output("")
        self.append_output("Flow ID 可用于“查看流程”等功能。")
        self.status_var.set(f"Listed {len(self.project_data.flow_cards)} flow(s) / 已列出流程")

    def _choose_flow_id(self) -> str | None:
        if not self._ensure_loaded():
            return None

        options = [
            (flow_id, str(document.data.get("name", "")))
            for flow_id, document in sorted(self.project_data.flow_cards_by_id.items())
        ]
        if not options:
            messagebox.showinfo("No Flows / 没有流程", "No Flow Cards are defined in this project.\n当前项目没有 Flow Card。", parent=self)
            return None

        return SelectionDialog.choose(
            self,
            title="Inspect Flow / 查看流程",
            prompt="Select a Flow ID to inspect.\n请选择要查看的流程：",
            options=options,
        )

    def _choose_node_id(self) -> str | None:
        if not self._ensure_loaded():
            return None

        options = [
            (node_id, str(document.data.get("name", "")))
            for node_id, document in sorted(self.project_data.nodes_by_id.items())
        ]
        if not options:
            messagebox.showinfo("No Nodes / 没有节点", "No Node files are defined in this project.\n当前项目没有 Node 定义。", parent=self)
            return None

        return SelectionDialog.choose(
            self,
            title="Find Flow for Node / 查找流程(节点)",
            prompt="Select a Node ID to find related flows.\n请选择要查询的节点：",
            options=options,
        )

    def _build_flow_text_diagram(self, flow_data: dict[str, object]) -> list[str]:
        lines: list[str] = []
        entry_points = flow_data.get("entry_points", [])
        if isinstance(entry_points, list) and entry_points:
            lines.append("Flow Path / 流程路径")
            for entry in entry_points:
                if isinstance(entry, str):
                    lines.append(entry)

        for step in flow_data.get("steps", []):
            if not isinstance(step, dict):
                continue
            action = str(step.get("action", ""))
            actor = str(step.get("actor", "")) if step.get("actor") else ""
            target = str(step.get("target", "")) if step.get("target") else ""
            store = str(step.get("store", "")) if step.get("store") else ""
            service = str(step.get("service", "")) if step.get("service") else ""

            parts = [action]
            if actor:
                parts.append(f"by {actor}")
            if target:
                parts.append(f"-> {target}")
            if store or service:
                side = " / ".join(value for value in (store, service) if value)
                parts.append(f"=> {side}")

            lines.append(f"  ↓ ({' '.join(parts)})")

        for return_path in flow_data.get("return_paths", []):
            if not isinstance(return_path, dict):
                continue
            source = str(return_path.get("from", ""))
            target = str(return_path.get("to", ""))
            if source or target:
                lines.append(f"  ↩ return / 返回: {source} -> {target}")

        return lines

    def inspect_flow(self) -> None:
        flow_id = self._choose_flow_id()
        if not flow_id:
            return

        try:
            flow_data = load_flow(flow_id, project_root=self.project_root)
        except (DependencyError, ValidationError, KeyError) as exc:
            self._handle_error(exc, title="Inspect Flow / 查看流程")
            return

        self.clear_output()
        self.append_output(f"Inspect Flow / 查看流程: {flow_id}")
        self.append_output("")
        self.append_output("Flow Narrative / 文字版链路")
        self.append_output(describe_flow(flow_data, self.project_data))
        detail_lines = describe_flow_steps(flow_data, self.project_data)
        if detail_lines:
            self.append_output("")
            self.append_output("Step Details / 分步骤说明")
            for line in detail_lines:
                self.append_output(line)
        self.append_output("")
        for line in self._build_flow_text_diagram(flow_data):
            self.append_output(line)
        if flow_data.get("anchor_files"):
            self.append_output("")
            self.append_output("Anchor Files / 锚点文件")
            for path in flow_data["anchor_files"]:
                self.append_output(f"- {path}")
        self.append_output("")
        self.append_output("Full JSON / 完整 JSON")
        self.append_output(json.dumps(flow_data, indent=2, ensure_ascii=False))
        self.status_var.set(f"Loaded flow / 已加载流程: {flow_id}")

    def describe_flow_view(self) -> None:
        flow_id = self._choose_flow_id()
        if not flow_id:
            return

        try:
            flow_data = load_flow(flow_id, project_root=self.project_root)
        except (DependencyError, ValidationError, KeyError) as exc:
            self._handle_error(exc, title="Describe Flow / 文字链路")
            return

        self.clear_output()
        self.append_output(f"Describe Flow / 文字链路: {flow_id}")
        self.append_output("")
        self.append_output("Current Flow Narrative / 当前链路描述")
        self.append_output(describe_flow(flow_data, self.project_data))

        detail_lines = describe_flow_steps(flow_data, self.project_data)
        if detail_lines:
            self.append_output("")
            self.append_output("Step Details / 分步骤说明")
            for line in detail_lines:
                self.append_output(line)

        self.status_var.set(f"Described flow / 已生成文字链路: {flow_id}")

    def find_flow_for_node(self) -> None:
        node_id = self._choose_node_id()
        if not node_id:
            return

        flow_ids = find_flow_ids_for_node(self.project_data, node_id)
        self.clear_output()
        if not flow_ids:
            self.append_output(f"No flows reference {node_id}.\n没有流程引用节点 {node_id}。")
            self.status_var.set("No matching flows / 没有匹配流程")
            return

        node_doc = self.project_data.nodes_by_id.get(node_id)
        node_name = str(node_doc.data.get("name", "")) if node_doc else ""
        self.append_output(f"Flows using node / 使用该节点的流程: {node_id}")
        if node_name:
            self.append_output(f"Node Name / 节点名称: {node_name}")
        self.append_output("")
        for flow_id in flow_ids:
            flow_doc = self.project_data.flow_cards_by_id.get(flow_id)
            name = str(flow_doc.data.get("name", "")) if flow_doc else ""
            status = str(flow_doc.data.get("status", "")) if flow_doc else ""
            self.append_output(f"- {flow_id}: {name} ({status})")

        self.status_var.set(f"Found {len(flow_ids)} flow(s) / 已找到相关流程")

    def show_map(self) -> None:
        if not self._ensure_loaded():
            return

        map_data = self.project_data.map_doc.data
        transfer_nodes = map_data.get("transfer_nodes", [])
        impact_rules = map_data.get("impact_rules", [])

        self.clear_output()
        self.append_output("Show Map / 显示地图")
        self.append_output("")
        self.append_output("Transfer Nodes / 换乘节点")
        if transfer_nodes:
            for item in transfer_nodes:
                notes = f" | notes / 说明: {item['notes']}" if item.get("notes") else ""
                self.append_output(f"- {item['id']} -> {', '.join(item['connects'])}{notes}")
        else:
            self.append_output("(none / 无)")

        self.append_output("")
        self.append_output("Impact Rules / 影响规则")
        if impact_rules:
            for item in impact_rules:
                notes = f" | notes / 说明: {item['notes']}" if item.get("notes") else ""
                self.append_output(f"- {item['node']} -> {', '.join(item['affects'])}{notes}")
        else:
            self.append_output("(none / 无)")

        self.status_var.set(
            f"Loaded map / 已加载地图: {len(transfer_nodes)} 个换乘节点, {len(impact_rules)} 条影响规则"
        )

    def view_savings_stats(self) -> None:
        if not self._require_project():
            return

        analysis = analyze_log_directory(self.project_root)
        self.clear_output()
        self.append_output(format_log_analysis(analysis))

        if analysis.total_records:
            self.status_var.set(f"Loaded savings stats / 已加载节省统计: {analysis.total_records} 条日志")
        else:
            self.status_var.set("No savings stats yet / 暂无节省统计")

    def suggest_flows(self) -> None:
        if not self._require_project():
            return

        description = simpledialog.askstring(
            "Suggest Flows / 推荐流程",
            "Describe the bug or requirement in your own words.\n请用自己的话描述问题或需求：",
            parent=self,
        )
        if not description:
            return

        try:
            suggestions = suggest_flows_for_bug(description, project_root=self.project_root)
        except (DependencyError, ValidationError) as exc:
            self._handle_error(exc, title="Suggest Flows / 推荐流程")
            return

        self.clear_output()
        if not suggestions:
            self.append_output("No matching flows found.\n没有找到匹配的流程。")
            self.status_var.set("No matching flows / 没有匹配流程")
            return

        self.append_output(f"Suggestions / 推荐结果: {description}")
        self.append_output("")
        for item in suggestions:
            matched_terms = ", ".join(item.matched_terms) if item.matched_terms else "(none)"
            self.append_output(
                f"- {item.flow_id}: {item.name} ({item.status}) | score={item.score} | matched={matched_terms}"
            )
            if item.anchor_files:
                self.append_output("  Anchor Files / 锚点文件：")
                for path in item.anchor_files:
                    self.append_output(f"    {path}")
            self.append_output("")

        self.status_var.set(f"Generated {len(suggestions)} suggestion(s) / 已生成推荐流程")


def main() -> None:
    ensure_supported_tk_runtime()
    app = FlowMemoryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
