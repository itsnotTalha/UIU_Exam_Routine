@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo UIU Exam Widget is not installed yet.
  echo Run install-windows.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "main.py"
pause
