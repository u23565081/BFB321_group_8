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


@pytest.mark.parametrize("environment", ["DevelopmentConfig", "ProductionConfig"])
@pytest.mark.parametrize("database_url", [None, "", "sqlite:///:memory:"])
def test_non_test_config_requires_mysql(monkeypatch, config_path, environment, database_url):
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    config = runpy.run_path(str(config_path))[environment]
    with pytest.raises(RuntimeError, match="Copy .env.example to .env and set DATABASE_URL to your MySQL database"):
        _ = config.SQLALCHEMY_DATABASE_URI


def test_testing_config_uses_in_memory_sqlite(monkeypatch, config_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    config = runpy.run_path(str(config_path))["TestingConfig"]
    assert config.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"


@pytest.mark.parametrize("value, expected", [(None, False), ("0", False), ("false", False), ("1", True), ("true", True)])
def test_debug_is_opt_in(monkeypatch, config_path, value, expected):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    if value is None:
        monkeypatch.delenv("FLASK_DEBUG", raising=False)
    else:
        monkeypatch.setenv("FLASK_DEBUG", value)
    configs = runpy.run_path(str(config_path))
    assert configs["DevelopmentConfig"].DEBUG is expected
    assert configs["ProductionConfig"].DEBUG is False


@pytest.mark.parametrize("entrypoint", ["run.py", "app.py"])
@pytest.mark.parametrize("host", [None, "192.0.2.10"])
def test_entrypoint_host_defaults_to_localhost(monkeypatch, entrypoint, host):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    application = Mock(config={"DEBUG": False})
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=lambda: application))
    if host is None:
        monkeypatch.delenv("HOST", raising=False)
    else:
        monkeypatch.setenv("HOST", host)
    path = Path(__file__).resolve().parents[1] / entrypoint
    runpy.run_path(str(path), run_name="__main__")
    application.run.assert_called_once_with(host=host or "127.0.0.1", port=5000, debug=False)
