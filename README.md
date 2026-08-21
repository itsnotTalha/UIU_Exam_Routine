# UIU Exam Widget — macOS v1.0

Native macOS edition of the UIU ExamCon routine app.

## What it does

- Logs into UIU ExamCon using Student or Faculty mode.
- Resolves a student's exact room from the published ID ranges.
- Saves the routine locally but never stores the UCAM password.
- Restores the routine after restart until **Clear Saved Routine** is pressed.
- Shows the full PySide6 routine window.
- Adds a native AppKit item to the macOS menu bar.
- Menu bar shows only the current/next exam:
  - `CSE 425 · 1d 22h · R307`
  - `CSE 425 · LIVE 1h 18m · R307`
  - `✓ You're good now` when all saved exams are finished.
- Clicking the menu-bar item opens or raises the full GUI.

## Install

Requirements: macOS 12+ and Python 3.

```zsh
chmod +x install-macos.sh uninstall-macos.sh
./install-macos.sh
```

The installer creates:

- `~/Applications/UIU Exam Widget.app`
- a login menu-bar helper via `~/Library/LaunchAgents/com.uiu.examwidget.menubar.plist`
- runtime files under `~/Library/Application Support/UIU Exam Widget/runtime`

Saved routine/cache files live under:

```text
~/Library/Application Support/UIU Exam Widget/
```

## Development run

```zsh
chmod +x setup-macos-dev.sh run-macos.sh run-menubar-macos.sh
./setup-macos-dev.sh
./run-macos.sh
```

In another Terminal window:

```zsh
./run-menubar-macos.sh
```

## Uninstall

Keep the saved routine/cache:

```zsh
./uninstall-macos.sh
```

Remove the app and all saved data:

```zsh
./uninstall-macos.sh --delete-data
```

## Notes

The menu-bar helper uses native AppKit through PyObjC, not a GNOME extension. macOS places custom status items on the right side of the menu bar alongside other status icons.
