#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing virtual environment: $PYTHON_BIN"
  echo "Create it with:"
  echo "  /opt/homebrew/bin/python3.13 -m venv \"$SCRIPT_DIR/.venv\""
  echo "  \"$SCRIPT_DIR/.venv/bin/python\" -m pip install -r \"$SCRIPT_DIR/requirements.txt\""
  read -k 1 '?Press any key to close...'
  echo
  exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" "$SCRIPT_DIR/fm_app.py"
