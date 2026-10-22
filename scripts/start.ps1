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
    function Test-PythonCandidate {
        param(
            [string]$Executable,
            [string[]]$PrefixArguments = @()
        )

        if (-not $Executable) { return $false }

        try {
            & $Executable @PrefixArguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" *> $null
            return $LASTEXITCODE -eq 0
        } catch {
            return $false
        }
    }

    $PythonExe = $null
    $PythonArgs = @()

    # Prefer the Windows Python launcher because it is not confused with the
    # Microsoft Store app-execution alias named python.exe.
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PythonLauncher -and (Test-PythonCandidate -Executable $PythonLauncher.Source -PrefixArguments @("-3"))) {
        $PythonExe = $PythonLauncher.Source
        $PythonArgs = @("-3")
    }

    if (-not $PythonExe) {
        foreach ($CommandName in @("python", "python3")) {
            $PythonCommand = Get-Command $CommandName -ErrorAction SilentlyContinue
            if ($PythonCommand -and (Test-PythonCandidate -Executable $PythonCommand.Source)) {
                $PythonExe = $PythonCommand.Source
                break
            }
        }
    }

    if (-not $PythonExe) {
        $KnownPythonPaths = @()
        if ($env:LOCALAPPDATA) {
            $KnownPythonPaths += Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -File -ErrorAction SilentlyContinue
        }
        if ($env:ProgramFiles) {
            $KnownPythonPaths += Get-ChildItem -Path (Join-Path $env:ProgramFiles "Python*\python.exe") -File -ErrorAction SilentlyContinue
        }

        foreach ($PythonFile in ($KnownPythonPaths | Sort-Object FullName -Descending)) {
            if (Test-PythonCandidate -Executable $PythonFile.FullName) {
                $PythonExe = $PythonFile.FullName
                break
            }
        }
    }

    if (-not $PythonExe) {
        Write-Host ""
        Write-Host "A working Python 3.12 or newer installation was not found." -ForegroundColor Red
        Write-Host "The 'python' command may currently be the Microsoft Store shortcut rather than Python itself."
        Write-Host ""
        Write-Host "Please complete these steps:"
        Write-Host "  1. Download Python from https://www.python.org/downloads/windows/"
        Write-Host "  2. Open the downloaded installer."
        Write-Host "  3. Select 'Add python.exe to PATH', then choose 'Install Now'."
        Write-Host "  4. Close PowerShell, open it again in this folder and rerun the start command."
        exit 1
    }

    $SelectedPythonVersion = & $PythonExe @PythonArgs --version 2>&1
    Write-Host "Using $SelectedPythonVersion"

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
