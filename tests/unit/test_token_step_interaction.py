from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests/js/token_steps_harness.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente: harness de movimento pulado")
def test_token_keyboard_step_behaviour():
    """Executa o map-token-steps.js real sobre dependências mínimas (ver o harness)."""
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
