param(
    [switch]$RemoveData
)

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Startup = Join-Path ([Environment]::GetFolderPath("Startup")) "UIU Exam Widget.lnk"
$Programs = Join-Path ([Environment]::GetFolderPath("Programs")) "UIU Exam Widget.lnk"
$Desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "UIU Exam Widget.lnk"
Remove-Item $Startup -Force
Remove-Item $Programs -Force
Remove-Item $Desktop -Force

# Stop only instances whose command line points to this project folder.
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -like "*$Root*main.py*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

if ($RemoveData) {
    $DataDir = Join-Path $env:LOCALAPPDATA "UIU Exam Widget"
    Remove-Item $DataDir -Recurse -Force
    Write-Host "Shortcuts removed and saved routine data deleted."
} else {
    Write-Host "Shortcuts removed. Saved routine data was kept."
    Write-Host "Run: powershell -ExecutionPolicy Bypass -File .\uninstall-windows.ps1 -RemoveData"
    Write-Host "if you also want to remove cached routine data."
}
