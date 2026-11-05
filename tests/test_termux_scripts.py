"""Regression tests for the Termux installers.

These run the scripts in ``--dry-run`` mode, so they do not touch pip, pkg, or
the network. They lock in the bugs that made the old installer confusing:
``--no-ollama`` must select the mock backend, and the env files must point at a
single per-user store instead of the current directory.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash is not available"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts" / "termux-install.sh"


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["ZOE_HOME"] = str(tmp_path / ".zoe")
    env.pop("ZOE_LLM_BACKEND", None)
    env.pop("ZOE_GGUF_PATH", None)
    return subprocess.run(
        ["bash", str(INSTALLER), "--dry-run", "--yes", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_no_ollama_selects_mock_backend(tmp_path):
    result = _run(tmp_path, "--no-ollama")
    assert result.returncode == 0, result.stderr
    assert 'export ZOE_LLM_BACKEND="mock"' in result.stdout
    assert 'export ZOE_LEDGER_PATH="' in result.stdout


def test_explicit_backend_survives_no_ollama(tmp_path):
    result = _run(
        tmp_path,
        "--no-ollama",
        "--backend", "llama-cli",
        "--model-file", str(tmp_path / "model.gguf"),
    )
    assert result.returncode == 0, result.stderr
    assert 'export ZOE_LLM_BACKEND="llama-cli"' in result.stdout
    assert f'export ZOE_GGUF_PATH="{tmp_path / "model.gguf"}"' in result.stdout


def test_dry_run_does_not_create_a_venv(tmp_path):
    result = _run(tmp_path, "--no-ollama")
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".zoe" / "venv").exists()
