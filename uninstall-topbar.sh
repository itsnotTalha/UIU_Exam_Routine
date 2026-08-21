#!/usr/bin/env bash
set -euo pipefail
UUID="uiu-exam-indicator@local"
gnome-extensions disable "$UUID" >/dev/null 2>&1 || true
rm -rf "$HOME/.local/share/gnome-shell/extensions/$UUID"
rm -f "$HOME/.local/bin/uiu-exam-widget"
echo "UIU Exam Indicator removed."
