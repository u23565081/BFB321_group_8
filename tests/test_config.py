"""Configuration must read environment values before defining its classes."""

from pathlib import Path
import runpy
import shutil

import pytest


@pytest.fixture()
def config_path(tmp_path):
    # Isolate dotenv discovery from the developer's real .env file.
    source = Path(__file__).resolve().parents[1] / "config.py"
    return shutil.copyfile(source, tmp_path / "config.py")


def test_development_config_uses_environment(monkeypatch, config_path):
    database_url = "mysql+pymysql://test_user:test_password@localhost/test_inventory"
    secret_key = "test-environment-secret"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SECRET_KEY", secret_key)

    config = runpy.run_path(str(config_path))["DevelopmentConfig"]

    assert config.SQLALCHEMY_DATABASE_URI == database_url
    assert config.SECRET_KEY == secret_key


def test_development_config_loads_dotenv_before_reading_values(
    monkeypatch, config_path
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    # Track keys added by load_dotenv so monkeypatch restores the environment.
    database_url = "mysql+pymysql://dotenv_user:dotenv_password@localhost/dotenv_inventory"
    secret_key = "test-dotenv-secret"
    Path(config_path).with_name(".env").write_text(
        f"DATABASE_URL={database_url}\nSECRET_KEY={secret_key}\n",
        encoding="utf-8",
    )

    config = runpy.run_path(str(config_path))["DevelopmentConfig"]

    assert config.SQLALCHEMY_DATABASE_URI == database_url
    assert config.SECRET_KEY == secret_key


def test_environment_takes_precedence_over_dotenv(monkeypatch, config_path):
    database_url = "mysql+pymysql://env_user:env_password@localhost/env_inventory"
    secret_key = "test-environment-secret"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SECRET_KEY", secret_key)
    Path(config_path).with_name(".env").write_text(
        "DATABASE_URL=mysql+pymysql://file_user:file_password@localhost/file_inventory\n"
        "SECRET_KEY=test-file-secret\n",
        encoding="utf-8",
    )

    config = runpy.run_path(str(config_path))["DevelopmentConfig"]

    assert config.SQLALCHEMY_DATABASE_URI == database_url
    assert config.SECRET_KEY == secret_key
