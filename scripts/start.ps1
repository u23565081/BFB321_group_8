param([switch]$MySQL)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($MySQL) {
    docker compose up --build
    exit $LASTEXITCODE
}

if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
$env:FLASK_ENV = "development"
& ".\.venv\Scripts\python.exe" database\seed.py
& ".\.venv\Scripts\python.exe" run.py

