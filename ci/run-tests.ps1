$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -U pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m playwright install chromium

New-Item -ItemType Directory -Force -Path reports | Out-Null
$env:USE_MOCK_DATA = "1"
$env:CI = "1"

& .\.venv\Scripts\python.exe -m pytest tests/unit --junitxml=reports/unit.xml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& .\.venv\Scripts\python.exe -m pytest tests/e2e --junitxml=reports/e2e.xml
exit $LASTEXITCODE
