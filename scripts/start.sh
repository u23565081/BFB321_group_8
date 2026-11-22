#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env. Set DATABASE_URL to your MySQL database and SECRET_KEY, then rerun. See README.md."
    exit 1
fi
database_url=${DATABASE_URL:-$(sed -n "s/^[[:space:]]*\(export[[:space:]]*\)\{0,1\}DATABASE_URL[[:space:]]*=[[:space:]]*['\"]\{0,1\}\(mysql+pymysql:\/\/.*\)/\2/p" .env | tail -n 1)}
case "$database_url" in
    mysql+pymysql://*) ;;
    *) echo "Copy .env.example to .env and set DATABASE_URL to your MySQL database (mysql+pymysql://...)." >&2; exit 1 ;;
esac
if [ "${1:-}" = "--mysql" ]; then
    exec docker compose up --build
fi
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -c "from dotenv import load_dotenv; import os; load_dotenv(); from sqlalchemy.engine import make_url; url = make_url(os.getenv('DATABASE_URL', '')); assert url.drivername == 'mysql+pymysql' and url.host and url.database, 'Set a complete mysql+pymysql DATABASE_URL in .env'"
python database/seed.py
exec python run.py

