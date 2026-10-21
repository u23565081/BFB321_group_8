#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
export FLASK_ENV=development
python database/seed.py
python run.py

