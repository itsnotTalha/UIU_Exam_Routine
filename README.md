# UIU Exam Widget — Windows v1.0

Windows edition of the UIU ExamCon routine app.


## Important Windows tray behavior

Standard Windows 10/11 system-tray icons cannot permanently display a long text string beside the clock the way a GNOME panel extension can. This version therefore uses:

- a colored UIU tray icon,
- a detailed hover tooltip,
- a context menu showing the next exam / room / time-left,
- click-to-open full GUI.

Urgency colors:

- Blue: more than 3 days away
- Amber: 1–3 days
- Orange: under 24 hours
- Red: under 6 hours
- Bright red: under 1 hour or exam in progress
- Green check: all saved exams are over

## Install

Requirements: Windows 10/11 and Python 3.10+.

1. Extract the ZIP to a permanent folder. Do not delete/move the folder after installation because the Windows shortcuts point to it.
2. Double-click:

```text
install-windows.bat
```

The installer will:

- create `.venv`,
- install PySide6 / Playwright / BeautifulSoup,
- install Playwright Chromium,
- add a Startup shortcut for tray mode,
- add Start Menu and Desktop shortcuts,
- start the tray indicator.

If Python is missing, install Python 3 from python.org and enable **Add Python to PATH**.

## Manual commands

Open/raise full GUI:

```text
run-windows.bat
```

Start tray helper:

```text
start-tray-windows.bat
```

Debug with a visible console:

```text
run-windows-debug.bat
```

## Saved data

Routine data is stored in:

```text
%LOCALAPPDATA%\UIU Exam Widget\
```

This includes the routine cache and normalized tray cache. The UCAM password is not stored.

## Uninstall startup integration

Double-click:

```text
uninstall-windows.bat
```

This removes the Startup / Start Menu / Desktop shortcuts but keeps cached routine data.

To remove data too:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall-windows.ps1 -RemoveData
```

## Notes

Windows may place the tray icon under the `^` hidden-icons menu initially. You can drag it onto the visible taskbar tray area from Windows tray settings.
