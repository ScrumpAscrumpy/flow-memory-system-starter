#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/macos/FlowMemorySystemLauncher.applescript"
TARGET_APP="$SCRIPT_DIR/Flow Memory System.app"
TMP_APP="$SCRIPT_DIR/Flow Memory System.tmp.app"

if [[ ! -f "$SOURCE_FILE" ]]; then
  echo "Missing AppleScript source: $SOURCE_FILE"
  exit 1
fi

/bin/rm -rf "$TMP_APP"
/usr/bin/osacompile -o "$TMP_APP" "$SOURCE_FILE"
/bin/rm -rf "$TARGET_APP"
/bin/mv "$TMP_APP" "$TARGET_APP"

echo "Built app:"
echo "  $TARGET_APP"
