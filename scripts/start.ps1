param([switch]$MySQL)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($MySQL) {
    docker compose up --build
    exit $LASTEXITCODE
}

Write-Host "[1/4] Preparing the Python environment..."

$VenvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $PythonExe = $null
    $PythonArgs = @()

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        $PythonExe = $PythonCommand.Source
    } else {
        $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($PythonLauncher) {
            $PythonExe = $PythonLauncher.Source
            $PythonArgs = @("-3")
        }
    }

    if (-not $PythonExe) {
        Write-Host ""
        Write-Host "Python was not found on this computer." -ForegroundColor Red
        Write-Host "Install Python 3.12 or newer from https://www.python.org/downloads/windows/"
        Write-Host "During installation, select 'Add Python to PATH'. Then reopen PowerShell and run this command again."
        exit 1
    }

    if (Test-Path ".venv") {
        $IncompleteVenv = ".venv-incomplete-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Move-Item -LiteralPath ".venv" -Destination $IncompleteVenv
        Write-Host "An incomplete .venv folder was moved to $IncompleteVenv."
    }

    & $PythonExe @PythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        throw "The Python environment could not be created. Please check the Python installation and try again."
    }
}

Write-Host "[2/4] Installing the required packages..."
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt

Write-Host "[3/4] Loading the demonstration data..."
$env:FLASK_ENV = "development"
& ".\.venv\Scripts\python.exe" database\seed.py

Write-Host "[4/4] Starting StockWise Soweto..."
Write-Host "Open http://127.0.0.1:5000 in your browser."
Write-Host "Shop owner login: owner@demo.co.za / demo2026"
Write-Host "Administrator login: admin@demo.co.za / admin2026"
Write-Host "Press Ctrl+C to stop the application."
& ".\.venv\Scripts\python.exe" run.py
