$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "UIU Exam Widget - Windows installer" -ForegroundColor Cyan

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Args = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Args = @() }
    }
    throw "Python 3 was not found. Install Python 3.10+ from python.org, enable 'Add Python to PATH', then run this installer again."
}

$PythonLauncher = Find-Python
if (-not (Test-Path (Join-Path $Root ".venv"))) {
    Write-Host "Creating virtual environment..."
    & $PythonLauncher.Command @($PythonLauncher.Args) -m venv (Join-Path $Root ".venv")
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
$PythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment creation failed." }

Write-Host "Installing Python packages..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host "Installing Playwright Chromium..."
& $Python -m playwright install chromium

$WshShell = New-Object -ComObject WScript.Shell
$Icon = Join-Path $Root "assets\uiu-exam-widget.ico"
$MainPy = Join-Path $Root "main.py"

# Start automatically with Windows in tray mode.
$StartupDir = [Environment]::GetFolderPath("Startup")
$StartupShortcut = $WshShell.CreateShortcut((Join-Path $StartupDir "UIU Exam Widget.lnk"))
$StartupShortcut.TargetPath = $PythonW
$StartupShortcut.Arguments = '"' + $MainPy + '" --tray'
$StartupShortcut.WorkingDirectory = $Root
$StartupShortcut.IconLocation = $Icon
$StartupShortcut.Description = "UIU Exam Widget tray indicator"
$StartupShortcut.Save()

# Start Menu shortcut opens/raises the full GUI.
$Programs = [Environment]::GetFolderPath("Programs")
$MenuShortcut = $WshShell.CreateShortcut((Join-Path $Programs "UIU Exam Widget.lnk"))
$MenuShortcut.TargetPath = $PythonW
$MenuShortcut.Arguments = '"' + $MainPy + '"'
$MenuShortcut.WorkingDirectory = $Root
$MenuShortcut.IconLocation = $Icon
$MenuShortcut.Description = "Open UIU Exam Widget"
$MenuShortcut.Save()

# Desktop shortcut for convenience.
$Desktop = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $Desktop "UIU Exam Widget.lnk"))
$DesktopShortcut.TargetPath = $PythonW
$DesktopShortcut.Arguments = '"' + $MainPy + '"'
$DesktopShortcut.WorkingDirectory = $Root
$DesktopShortcut.IconLocation = $Icon
$DesktopShortcut.Description = "Open UIU Exam Widget"
$DesktopShortcut.Save()

Write-Host "Starting the tray indicator..."
Start-Process -FilePath $PythonW -ArgumentList ('"' + $MainPy + '" --tray') -WorkingDirectory $Root

Write-Host ""
Write-Host "Installed successfully." -ForegroundColor Green
Write-Host "A UIU icon should appear in the Windows system tray."
Write-Host "Click it to open the full routine window."
