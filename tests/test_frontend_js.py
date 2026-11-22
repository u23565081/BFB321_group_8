"""Run the fetch interaction checks when Node.js is available."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_frontend_fetch_interactions():
    node = shutil.which("node")
    if not node:
        pytest.skip("Install Node.js to run the frontend fetch interaction checks")
    result = subprocess.run(
        [node, "--test", str(Path(__file__).with_name("frontend.test.cjs"))],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
