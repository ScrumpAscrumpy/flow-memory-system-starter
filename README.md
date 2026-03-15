# Flow Memory System

Flow Memory System is a lightweight toolkit for documenting a codebase as business flows instead of only folders and files. It gives developers and AI coding assistants a shared memory layer for finding the right files, understanding shared nodes, and making safer changes.

## What Is Included

- `flows/`: example Flow Cards, Nodes, and Metro Map data
- `schemas/`: JSON Schema files for Flow Card, Node, and Map validation
- `flow_memory.py`: YAML loading and validation
- `ai_helper.py`: helper functions for flow lookup, anchor file suggestions, and human-readable flow descriptions
- `fm_app.py`: Tkinter desktop GUI
- `validate.py`: CLI validation entry point
- `analyze_logs.py`: log analysis for usage and efficiency metrics
- `build_mac_app.command`: rebuild the macOS app launcher

## Common Tasks

Validate the current project:

```bash
python3 validate.py
```

Launch the GUI:

```bash
python3 fm_app.py
```

Describe a flow as a plain-language chain:

```bash
python3 ai_helper.py describe flow.text_record_lifecycle
```

Rebuild the macOS app launcher:

```bash
./build_mac_app.command
```

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md): bilingual end-user guide
- [fornewprojectREADME.md](fornewprojectREADME.md): onboarding notes for teams adopting Flow Memory in a new repository
- [CODEX_ONBOARDING_PROMPT.md](CODEX_ONBOARDING_PROMPT.md): prompt template for AI agents working in a new project

## Repository Hygiene

This public repository intentionally excludes local configuration, virtual environments, logs, and internal design documents. If you reuse this project as a starter, keep your own private planning documents outside version control or add them to `.gitignore`.
