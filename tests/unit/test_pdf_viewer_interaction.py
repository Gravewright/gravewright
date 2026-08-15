from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests/js/pdf_viewer_harness.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente: harness de PDF pulado")
def test_pdf_viewer_places_fields_over_the_page():
    """Executa o pdf-viewer.js real contra um pdf.js falso (ver o harness).

    O que só um teste de execução pega: o eixo Y do PDF cresce para cima, então um
    erro de inversão põe todos os campos espelhados na vertical: a ficha abre
    bonita e os campos ficam no lugar errado.
    """
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
