"""Keep the PT-BR SDK docs aligned with the English SDK docs.

The PT-BR translation must track the real SDK surface, not drift from it. These tests
enforce three invariants:

1. Every English SDK doc has a PT-BR counterpart.
2. Every ``sdk.<method>`` API identifier used in an English doc also appears in its
   PT-BR counterpart (this is what makes a translation *dangerous* when it drifts —
   it documents methods that do not exist, or omits ones that do).
3. The removed legacy "System API" / "Module API" surface is not reintroduced in
   either language.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EN_DIR = PROJECT_ROOT / "docs" / "sdk"
PT_DIR = PROJECT_ROOT / "docs" / "pt-br" / "sdk"

# English filename -> PT-BR filename when the translation uses a localized name.
RENAMED = {
    "creating-packages-with-ai.md": "criando-pacotes-com-ia.md",
    "declarative-packages.md": "pacotes-declarativos.md",
}

API_TOKEN = re.compile(r"sdk\.[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*")
LEGACY = re.compile(r"System API|Module API")

# ``sdk.validation.*`` and ``sdk.errors.*`` are diagnostic keys, not runtime methods.
NON_API_PREFIXES = ("sdk.validation.", "sdk.errors.")


def _pt_for(en_file: Path) -> Path:
    return PT_DIR / RENAMED.get(en_file.name, en_file.name)


def _en_docs() -> list[Path]:
    return sorted(EN_DIR.glob("*.md"))


def _api_tokens(text: str) -> set[str]:
    # Namespace-only mentions (sdk.combat) and full calls (sdk.combat.register) both count;
    # diagnostic keys (sdk.validation.*, sdk.errors.*) are not part of the API surface.
    return {
        token
        for token in API_TOKEN.findall(text)
        if not token.startswith(NON_API_PREFIXES)
    }


@pytest.mark.parametrize("en_file", _en_docs(), ids=lambda p: p.name)
def test_pt_counterpart_exists(en_file: Path) -> None:
    pt_file = _pt_for(en_file)
    assert pt_file.is_file(), f"missing PT-BR counterpart for docs/sdk/{en_file.name}: {pt_file}"


@pytest.mark.parametrize("en_file", _en_docs(), ids=lambda p: p.name)
def test_pt_covers_en_api_surface(en_file: Path) -> None:
    pt_file = _pt_for(en_file)
    if not pt_file.is_file():
        pytest.skip("counterpart missing (covered by test_pt_counterpart_exists)")
    en_tokens = _api_tokens(en_file.read_text(encoding="utf-8"))
    pt_tokens = _api_tokens(pt_file.read_text(encoding="utf-8"))
    missing = sorted(en_tokens - pt_tokens)
    assert not missing, (
        f"{pt_file.relative_to(PROJECT_ROOT)} is missing SDK API identifiers present in "
        f"docs/sdk/{en_file.name}: {missing}"
    )


@pytest.mark.parametrize(
    "doc",
    sorted(EN_DIR.glob("*.md")) + sorted(PT_DIR.glob("*.md")),
    ids=lambda p: str(p.relative_to(PROJECT_ROOT)),
)
def test_no_legacy_api_mentions(doc: Path) -> None:
    assert not LEGACY.search(doc.read_text(encoding="utf-8")), (
        f"{doc.relative_to(PROJECT_ROOT)} reintroduces a removed legacy API surface "
        "(System API / Module API)."
    )
