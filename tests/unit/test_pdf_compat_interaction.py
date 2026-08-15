"""O pdf.js vendorizado precisa ser o build ``legacy``.

O build moderno usa APIs que nem todo navegador tem: Map.getOrInsertComputed
(que o Chrome ainda não traz) e Uint8Array.toHex (Chrome 140+), e usa justamente
nos caminhos de FORMULÁRIO e DESCRIPTOGRAFIA, por onde passa toda ficha de RPG
preenchível. Com ele, o documento nem abre e a ficha só diz "não foi possível
abrir o PDF", sem indicar que o problema é o navegador.

O build legacy carrega os próprios polyfills. Trocar de volta pelo moderno é uma
regressão silenciosa: passa em qualquer máquina de desenvolvimento moderna e
quebra na mão de quem joga.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests/js/pdf_compat_harness.js"
PACKAGE = ROOT / "data/packages/rulesets/gravewright-pdf-system"


@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente: harness de pdf.js pulado")
def test_the_vendored_pdfjs_works_without_bleeding_edge_apis():
    """Roda o pdf.js vendorizado num Node que não tem nenhuma das APIs novas -
    espelho de um navegador atrasado (ver o harness)."""
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, cwd=ROOT, timeout=120
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_bundled_build_carries_its_own_polyfills():
    """A marca do legacy. Sem isto, o pacote está com o build errado."""
    for name in ("pdf.mjs", "pdf.worker.mjs"):
        source = (PACKAGE / "vendor" / name).read_text(encoding="utf-8", errors="ignore")
        assert "core-js" in source, f"{name} não parece ser o build legacy"


def test_the_viewer_points_straight_at_the_vendored_worker():
    """O embrulho que existia só para carregar um preenchimento nosso saiu junto
    com o preenchimento: com o legacy, o worker se resolve sozinho."""
    viewer = (PACKAGE / "scripts/pdf-viewer.js").read_text(encoding="utf-8")
    assert 'workerSrc = asset("vendor/pdf.worker.mjs")' in viewer
    assert "pdf-compat" not in viewer, "o remendo foi removido"
    assert not (PACKAGE / "scripts/pdf-compat.mjs").exists()
    assert not (PACKAGE / "scripts/pdf-worker.mjs").exists()

    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    declared = {
        entry["path"]
        for group in manifest["provides"]["assets"].values()
        for entry in group
    }
    assert not [p for p in declared if "pdf-compat" in p or "pdf-worker" in p], (
        "o manifest ainda declara arquivos que não existem mais"
    )
