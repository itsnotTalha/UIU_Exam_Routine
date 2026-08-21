@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo UIU Exam Widget is not installed yet.
  echo Run install-windows.bat first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "main.py" --tray
