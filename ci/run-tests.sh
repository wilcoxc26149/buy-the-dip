#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium

mkdir -p reports
export USE_MOCK_DATA=1
export CI=1

.venv/bin/python -m pytest tests/unit --junitxml=reports/unit.xml
.venv/bin/python -m pytest tests/e2e --junitxml=reports/e2e.xml
