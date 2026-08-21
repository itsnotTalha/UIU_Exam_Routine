#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
UUID="uiu-exam-indicator@local"
EXT_SRC="$PROJECT_DIR/gnome-extension"
EXT_DST="$HOME/.local/share/gnome-shell/extensions/$UUID"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/uiu-exam-widget"

if ! command -v gnome-shell >/dev/null 2>&1; then
  echo "GNOME Shell was not found. This top-bar extension requires Ubuntu GNOME."
  exit 1
fi

SHELL_MAJOR="$(gnome-shell --version | grep -oE '[0-9]+' | head -n1 || true)"
if [[ -z "$SHELL_MAJOR" ]]; then
  echo "Could not detect the GNOME Shell version."
  exit 1
fi

if (( SHELL_MAJOR < 45 )); then
  echo "GNOME Shell $SHELL_MAJOR detected. This build targets GNOME 45 or newer."
  exit 1
fi

mkdir -p "$EXT_DST" "$BIN_DIR"
rm -rf "$EXT_DST"/*
cp "$EXT_SRC/extension.js" "$EXT_SRC/stylesheet.css" "$EXT_DST/"

cat > "$EXT_DST/metadata.json" <<EOF
{
  "uuid": "$UUID",
  "name": "UIU Exam Indicator",
  "description": "Shows the next UIU exam beside the GNOME clock and opens the UIU Exam Widget when clicked.",
  "shell-version": ["$SHELL_MAJOR"]
}
EOF

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
cd "$PROJECT_DIR"
if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/main.py"
else
  exec python3 "$PROJECT_DIR/main.py"
fi
EOF
chmod +x "$LAUNCHER"

# Opening the app once migrates an existing v1 cache into panel-cache.json.
"$LAUNCHER" >/dev/null 2>&1 &
sleep 1

set +e
gnome-extensions disable "$UUID" >/dev/null 2>&1
gnome-extensions enable "$UUID"
ENABLE_STATUS=$?
set -e

if [[ $ENABLE_STATUS -ne 0 ]]; then
  echo
  echo "The extension files were installed, but GNOME has not discovered them yet."
  echo "Log out and back in once, then run:"
  echo "  gnome-extensions enable $UUID"
else
  echo
  echo "UIU Exam Indicator enabled."
fi

echo "It should appear immediately to the LEFT of the center clock."
echo "Click the indicator to open/raise the full UIU Exam Widget."
