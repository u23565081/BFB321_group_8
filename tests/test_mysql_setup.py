"""Opt-in clean-machine check against a dedicated empty MySQL 8 server.

PowerShell: $env:MYSQL_SETUP_PORT='3307'; python -m pytest tests/test_mysql_setup.py -v
The server must have no spaza_inventory database or spaza_user account.
Root password, if needed: MYSQL_SETUP_ROOT_PASSWORD. Never target a shared server.
"""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(not os.getenv("MYSQL_SETUP_PORT"), reason="Requires a dedicated empty MySQL 8 server")
def test_readme_setup_on_empty_mysql():
    import pymysql
    from pymysql import _auth

    assert _auth._have_cryptography, "Install the updated requirements-dev.txt (PyMySQL[rsa]) before this check"

    port = int(os.environ["MYSQL_SETUP_PORT"])
    root = Path(__file__).resolve().parents[1]
    connection = pymysql.connect(
        host="127.0.0.1", port=port, user="root",
        password=os.getenv("MYSQL_SETUP_ROOT_PASSWORD", ""), autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            assert cursor.fetchone()[0].startswith("8.")
            cursor.execute("SHOW DATABASES LIKE 'spaza_inventory'")
            assert cursor.fetchone() is None, "Use an empty, dedicated MySQL instance"
            cursor.execute("SELECT User FROM mysql.user WHERE User='spaza_user'")
            assert cursor.fetchone() is None, "Use an instance without spaza_user"
            cursor.execute("CREATE DATABASE spaza_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute("CREATE USER 'spaza_user'@'localhost' IDENTIFIED BY 'spaza_password'")
            cursor.execute("GRANT ALL PRIVILEGES ON spaza_inventory.* TO 'spaza_user'@'localhost'")
    finally:
        connection.close()

    env = dict(os.environ, MYSQL_PWD="spaza_password")
    subprocess.run(
        ["mysql", "--protocol=TCP", "-h", "127.0.0.1", "-P", str(port),
         "-u", "spaza_user", "spaza_inventory"],
        input=(root / "database/schema.sql").read_bytes(), env=env, check=True,
    )
    # Clear authentication caches: seeding must work on a cold MySQL 8 server,
    # not merely after the CLI has authenticated this user over TLS.
    with pymysql.connect(
        host="127.0.0.1", port=port, user="root",
        password=os.getenv("MYSQL_SETUP_ROOT_PASSWORD", ""), autocommit=True,
    ) as admin:
        with admin.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")
    env.update(
        DATABASE_URL=f"mysql+pymysql://spaza_user:spaza_password@localhost:{port}/spaza_inventory",
        SECRET_KEY="mysql-setup-check-secret", FLASK_ENV="development", FLASK_DEBUG="0",
    )
    # Run twice to check that the documented seed entry point is idempotent.
    for _ in range(2):
        subprocess.run([sys.executable, "database/seed.py"], cwd=root, env=env, check=True)
    smoke = """
from app import create_app
from app.extensions import db
from app.models import Product, Shop, User
app = create_app()
assert not app.debug
with app.app_context():
    assert db.engine.dialect.name == 'mysql'
    assert Product.query.count() == 20
    assert Shop.query.count() == 5
    assert User.query.count() == 2
client = app.test_client()
for email, password in [('owner@demo.co.za', 'demo2026'), ('admin@demo.co.za', 'admin2026')]:
    assert client.post('/login', data={'email': email, 'password': password}).status_code == 302
    for path in ['/dashboard', '/inventory', '/replenishment', '/orders', '/impact']:
        assert client.get(path).status_code == 200, path
    client.post('/logout')
"""
    subprocess.run([sys.executable, "-c", smoke], cwd=root, env=env, check=True)
