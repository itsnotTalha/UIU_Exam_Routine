#!/bin/zsh
set -euo pipefail

APP_DATA="$HOME/Library/Application Support/UIU Exam Widget"
APP_BUNDLE="$HOME/Applications/UIU Exam Widget.app"
PLIST="$HOME/Library/LaunchAgents/com.uiu.examwidget.menubar.plist"
UID_NUM="$(id -u)"

launchctl bootout "gui/$UID_NUM" "$PLIST" >/dev/null 2>&1 || true
launchctl unload -w "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
rm -rf "$APP_BUNDLE"
rm -rf "$APP_DATA/runtime"

if [[ "${1:-}" == "--delete-data" ]]; then
  rm -rf "$APP_DATA"
  echo "Application and saved routine data removed."
else
  echo "Application removed. Saved routine data was preserved."
  echo "To remove it too: ./uninstall-macos.sh --delete-data"
fi
