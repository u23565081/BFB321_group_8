"""Start scripts must stop before installing/seeding an unconfigured project."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("case", ["missing", "sqlite", "unset"])
def test_windows_start_preflight(tmp_path, case):
    powershell = shutil.which("powershell")
    if not powershell:
        pytest.skip("Windows PowerShell is not installed")
    root = Path(__file__).resolve().parents[1]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(root / "scripts/start.ps1", scripts / "start.ps1")
    shutil.copyfile(root / ".env.example", tmp_path / ".env.example")
    if case != "missing":
        (tmp_path / ".env").write_text(
            "DATABASE_URL=sqlite:///:memory:\n" if case == "sqlite" else "SECRET_KEY=test\n",
            encoding="utf-8",
        )
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    result = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scripts / "start.ps1"), "-MySQL"],
        env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stdout + result.stderr
    assert (tmp_path / ".env").exists()
    assert not (tmp_path / ".venv").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell execution requires Linux/macOS")
@pytest.mark.parametrize("case", ["missing", "sqlite", "unset"])
def test_posix_start_preflight(tmp_path, case):
    root = Path(__file__).resolve().parents[1]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(root / "scripts/start.sh", scripts / "start.sh")
    shutil.copyfile(root / ".env.example", tmp_path / ".env.example")
    if case != "missing":
        (tmp_path / ".env").write_text(
            "DATABASE_URL=sqlite:///:memory:\n" if case == "sqlite" else "SECRET_KEY=test\n",
            encoding="utf-8",
        )
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    result = subprocess.run(["sh", str(scripts / "start.sh"), "--mysql"], env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stdout + result.stderr
    assert (tmp_path / ".env").exists()
    assert not (tmp_path / ".venv").exists()
