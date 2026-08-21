#!/bin/zsh
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "UIU Exam Widget macOS installer must be run on macOS."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3 first, then run this installer again."
  exit 1
fi

SOURCE_DIR="${0:A:h}"
APP_DATA="$HOME/Library/Application Support/UIU Exam Widget"
RUNTIME_DIR="$APP_DATA/runtime"
APP_BUNDLE="$HOME/Applications/UIU Exam Widget.app"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST="$LAUNCH_AGENTS/com.uiu.examwidget.menubar.plist"
LOG_DIR="$HOME/Library/Logs/UIU Exam Widget"

mkdir -p "$RUNTIME_DIR" "$HOME/Applications" "$LAUNCH_AGENTS" "$LOG_DIR"

# Copy only runtime sources. Saved routine files live one level above runtime and
# are intentionally not overwritten during upgrades.
for file in main.py models.py examcon.py storage.py paths.py menubar.py requirements.txt; do
  cp "$SOURCE_DIR/$file" "$RUNTIME_DIR/$file"
done

python3 -m venv "$RUNTIME_DIR/.venv"
"$RUNTIME_DIR/.venv/bin/python" -m pip install --upgrade pip
"$RUNTIME_DIR/.venv/bin/pip" install -r "$RUNTIME_DIR/requirements.txt"
"$RUNTIME_DIR/.venv/bin/python" -m playwright install chromium

# Create a lightweight native .app bundle whose executable starts the PySide GUI.
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

cat > "$APP_BUNDLE/Contents/Info.plist" <<'PLISTAPP'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>UIU Exam Widget</string>
  <key>CFBundleDisplayName</key>
  <string>UIU Exam Widget</string>
  <key>CFBundleIdentifier</key>
  <string>com.uiu.examwidget</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>UIU Exam Widget</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLISTAPP

cat > "$APP_BUNDLE/Contents/MacOS/UIU Exam Widget" <<'LAUNCHER'
#!/bin/zsh
RUNTIME="$HOME/Library/Application Support/UIU Exam Widget/runtime"
exec "$RUNTIME/.venv/bin/python" "$RUNTIME/main.py"
LAUNCHER
chmod +x "$APP_BUNDLE/Contents/MacOS/UIU Exam Widget"

# Start the native AppKit menu-bar helper at login.
cat > "$PLIST" <<PLISTAGENT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.uiu.examwidget.menubar</string>
  <key>ProgramArguments</key>
  <array>
    <string>$RUNTIME_DIR/.venv/bin/python</string>
    <string>$RUNTIME_DIR/menubar.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$RUNTIME_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/menubar.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/menubar-error.log</string>
</dict>
</plist>
PLISTAGENT

UID_NUM="$(id -u)"
launchctl bootout "gui/$UID_NUM" "$PLIST" >/dev/null 2>&1 || true
if ! launchctl bootstrap "gui/$UID_NUM" "$PLIST"; then
  # Compatibility fallback for older launchctl behavior.
  launchctl load -w "$PLIST" || true
fi
launchctl kickstart -k "gui/$UID_NUM/com.uiu.examwidget.menubar" >/dev/null 2>&1 || true

open "$APP_BUNDLE"

echo
echo "Installed UIU Exam Widget for macOS."
echo "App:      $APP_BUNDLE"
echo "Menu bar: starts automatically at login"
echo "Data:     $APP_DATA"
echo
echo "Click the menu-bar exam text to open the full routine window."
