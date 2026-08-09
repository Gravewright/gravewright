"""Chave de ``provides.mappings`` que ninguém lê é mapeamento que não existe.

O validador de manifest aceita qualquer chave em ``provides.mappings`` — o
arquivo existe, o caminho é seguro, tudo passa. Mas o servidor só procura nomes
específicos (``tokens``, ``chatCards``, ``rollToast``). Declarar ``token`` em vez
de ``tokens`` faz o mapeamento simplesmente não ser encontrado.

O efeito é inteiramente silencioso: ``get_token_mappings`` devolve ``{}``, o
projetor desiste antes de montar a TokenView, e o token perde barras **e imagem**
no tabuleiro. Nada é registrado, nada falha.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "data/packages"
REGISTRY = ROOT / "app/engine/rules/rules_registry.py"


def _consumed_keys() -> set[str]:
    """Os nomes que o servidor realmente procura, lidos do próprio registry."""
    source = REGISTRY.read_text(encoding="utf-8")
    keys = set(re.findall(r'manifest\.mappings\.get\(\s*"(\w+)"', source))
    assert keys, "não consegui ler as chaves consumidas; o registry mudou de forma?"
    return keys


def test_every_declared_mapping_key_is_read_by_the_server():
    consumed = _consumed_keys()
    problemas: list[str] = []

    for manifest_path in PACKAGES.rglob("manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared = (manifest.get("provides") or {}).get("mappings") or {}
        package = manifest.get("id", manifest_path.parent.name)

        for key in declared:
            # ``pdfFields`` e afins são lidos pelo próprio pacote, no navegador;
            # o servidor não precisa conhecê-los. O que não pode é um nome QUASE
            # certo — o singular de um plural que o servidor espera.
            if key in consumed:
                continue
            quase = {c for c in consumed if c.rstrip("s") == key.rstrip("s")}
            if quase:
                problemas.append(
                    f"{package}: '{key}' não é lido; o servidor procura {sorted(quase)}"
                )

    assert not problemas, "\n  ".join(["mapeamentos que nunca serão encontrados:", *problemas])


def test_the_pdf_system_token_mapping_reaches_the_projector():
    """O caminho inteiro: manifest -> registry -> TokenView. Sem isso o token do
    tabuleiro fica sem barra e sem imagem."""
    from app.engine.sdk.package_manifest import PackageManifest

    package = PACKAGES / "rulesets/gravewright-pdf-system"
    manifest = PackageManifest.from_dict(
        json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    )

    relative = manifest.mappings.get("tokens", "")
    assert relative, "a chave que o servidor lê é 'tokens'"
    assert (package / relative).is_file()

    mapping = json.loads((package / relative).read_text(encoding="utf-8"))
    assert "character" in mapping, "o mapeamento é por tipo de ator"


def test_a_missing_token_mapping_costs_the_image_not_only_the_bars():
    """Por que o sintoma é 'o token some' e não 'a barra some': o projetor
    devolve {} antes de chegar na imagem."""
    projector = (ROOT / "app/engine/tokens/actor_token_projector.py").read_text(encoding="utf-8")
    corpo = projector.split("def project(", 1)[1]

    saida_cedo = corpo.index("return {}")
    imagem = corpo.index("token_asset_url")
    assert saida_cedo < imagem, (
        "sem mapeamento o projetor desiste antes da imagem — é isso que faz o "
        "token sumir do tabuleiro, não só perder a barra"
    )
