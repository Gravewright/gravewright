import shutil
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT/"tests/js/wall_interaction_harness.js"

@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente: cobertura de interacao de paredes ignorada")
def test_wall_drawing_interaction_behaviour():
    """Executa o dynamic-lighting.js real sobre um DOM minimo (ver o harness)."""
    result=subprocess.run(["node",str(HARNESS)],capture_output=True,text=True,cwd=ROOT,timeout=60)
    assert result.returncode==0, f"{result.stdout}\n{result.stderr}"
