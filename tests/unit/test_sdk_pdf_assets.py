"""Um pacote precisa poder entregar a ficha em PDF que ele declara.

O serviço de assets de pacote serve apenas o que o manifest referencia, e só de
pacote habilitado. Antes de liberar ``.pdf`` ele devolvia 404 para qualquer PDF,
o que impedia um sistema baseado em ficha PDF de existir como pacote.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.sdk.package_asset_service import _CONTENT_TYPES

ROOT = Path(__file__).resolve().parents[2]


def test_pdf_is_servable_from_a_package():
    assert _CONTENT_TYPES.get(".pdf") == "application/pdf"


def test_only_declared_and_known_types_are_served():
    """A liberação do PDF não pode virar 'serve qualquer arquivo'."""
    source = (ROOT / "app/engine/sdk/package_asset_service.py").read_text(encoding="utf-8")

    # continua valendo: o caminho tem de estar declarado no manifest
    assert "if relative not in set(manifest.referenced_paths()):" in source
    assert "return None" in source

    # e o tipo tem de estar na lista: extensão desconhecida segue barrada
    assert "content_type = _CONTENT_TYPES.get(Path(relative).suffix.lower())" in source

    # tipos executáveis pelo servidor nunca podem entrar nessa lista
    for dangerous in (".py", ".sh", ".exe", ".dll", ".so", ".sqlite3", ".env"):
        assert dangerous not in _CONTENT_TYPES, dangerous
