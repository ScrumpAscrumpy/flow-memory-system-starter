# Flow Memory System

Flow Memory System is a starter toolkit for documenting a codebase as business flows instead of only folders and files. It helps human contributors and AI coding agents work from the same structured view of routes, pages, actions, shared services, persistence points, and cross-flow impact.

[中文说明](README.zh-CN.md)

## Template Layout

```text
flow-memory-system/
  docs/
    USER_GUIDE.md
    STARTER_GUIDE.md
    SCREENSHOTS.md
    screenshots/
  flows/
    cards/
    nodes/
    map.yaml
    conventions.md
  schemas/
    FlowCard.schema.json
    Node.schema.json
    Map.schema.json
  CODEX_ONBOARDING_PROMPT.md
  fm_app.py
  flow_memory.py
  ai_helper.py
  validate.py
```

## What This Repository Provides

- Example `flows/` and `schemas/` data so the system runs immediately
- Python validation and query helpers
- A Tkinter desktop GUI for non-technical users
- Plain-language flow narration for route and jump logic
- A reusable onboarding prompt for AI agents

## Quick Start

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Validate the example project:

```bash
python3 validate.py
```

Launch the GUI:

```bash
python3 fm_app.py
```

Generate a plain-language flow narrative:

```bash
python3 ai_helper.py describe flow.text_record_lifecycle
```

## Documentation

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): end-user and GUI guide
- [docs/STARTER_GUIDE.md](docs/STARTER_GUIDE.md): how to adopt Flow Memory in a new repository
- [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md): real screenshots and UI walkthrough
- [CODEX_ONBOARDING_PROMPT.md](CODEX_ONBOARDING_PROMPT.md): onboarding prompt for AI agents

## Notes for Public Reuse

- Local logs, virtual environments, local configuration, private planning files, and the built macOS `.app` bundle are ignored by Git.
- The repository is intended to be reused as a starter, not as a production SaaS service.

## Safety and Platform

This project is built to help Codex and similar AI coding agents manage files, flows, and task context more clearly. It does not upload your repository data to a hosted cloud service or require a remote account to work. The system runs locally in your project workspace. Some optional local artifacts, such as `flows/` documents or `flow_memory_logs/`, may be written inside your own project folder, but they stay on your machine unless you choose to commit or share them.

The current packaged desktop launcher is macOS-oriented. The Python source can still be adapted to other platforms, but the polished desktop workflow in this repository is currently focused on macOS.
