"""Bounded quality checks for the public SDK documentation.

These catch the failures that actually reach a reader: a link to someone's laptop, a
method that no longer exists, an example calling something the contract does not
declare, or implementation chronology leaking into a reference page. They are not a
banned-word filter — legitimate prose is left alone.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
DOC_ROOTS = [ROOT / "docs" / "sdk", ROOT / "docs" / "pt-br" / "sdk", ROOT / "docs" / "es" / "sdk"]
DOCS = sorted(p for root in DOC_ROOTS for p in root.rglob("*.md"))
CONTRACT = json.loads((ROOT / "docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
METHODS = {item["path"] for item in CONTRACT["methods"]}

# Paths and URLs that only resolve on the machine that wrote them. A developer's home
# directory carries a user segment; `C:\Users\file.txt` shown as an example of a
# *rejected* manifest path does not, and is legitimate security documentation.
LOCAL_REFERENCES = [
    (r"[A-Za-z]:\\\\?Users\\\\?[^\\\s`]+\\\\?[^\\\s`]", "developer home path"),
    (r"[A-Za-z]:/Users/[^/\s`]+/", "developer home path"),
    (r"vscode-webview://", "editor webview URL"),
    (r"file:///", "local file URL"),
    (r"/home/[a-z][a-z0-9_-]*/", "developer home path"),
]

# Implementation chronology: how something came to exist is not reference material.
CHRONOLOGY = [
    (r"\bwave\s*[0-9]", "implementation wave"),
    (r"\bround\s+[0-9]+\b", "implementation round"),
    (r"\bcapability hunt\b", "capability hunt"),
    (r"\bgap[- ]closure\b", "gap-closure narrative"),
    (r"\bpre-LTS\b", "pre-LTS staging term"),
    (r"\bsdk-lab\b", "lab terminology"),
]

# `sdk.<path>(` mentions in prose and examples must be real methods.
METHOD_MENTION = re.compile(r"`?sdk\.([A-Za-z][A-Za-z0-9_.]*)\s*\(")

# Known non-contract helpers exposed on the SDK object but not gated as methods.
NON_GATED = {
    "capabilities.has", "capabilities.require", "capabilities.list", "context",
    "game.context", "game.campaign", "game.scene", "game.user", "game.ready",
    "toast", "setting", "version", "package", "kind",
}


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_public_docs_contain_no_local_machine_references(doc: Path):
    text = doc.read_text(encoding="utf-8")
    for pattern, label in LOCAL_REFERENCES:
        assert not re.search(pattern, text), f"{doc.name} contains a {label}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_public_docs_contain_no_implementation_chronology(doc: Path):
    text = doc.read_text(encoding="utf-8")
    for pattern, label in CHRONOLOGY:
        found = re.search(pattern, text, flags=re.IGNORECASE)
        assert not found, f"{doc.name} references {label}: {found.group(0)!r}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_documented_sdk_calls_exist_in_the_contract(doc: Path):
    text = doc.read_text(encoding="utf-8")
    unknown = set()
    for match in METHOD_MENTION.finditer(text):
        path = match.group(1).rstrip(".")
        if path in METHODS or path in NON_GATED:
            continue
        # Namespace prefixes are legitimate prose ("sdk.audio.*").
        if any(method.startswith(f"{path}.") for method in METHODS):
            continue
        unknown.add(path)
    assert unknown == set(), f"{doc.name} references unknown SDK methods: {sorted(unknown)}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_doc_links_resolve(doc: Path):
    text = doc.read_text(encoding="utf-8")
    broken = []
    for target in re.findall(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", text):
        if target.startswith(("http://", "https://")):
            continue
        if not (doc.parent / target).resolve().is_file():
            broken.append(target)
    assert broken == [], f"{doc.name} links to missing files: {broken}"


def test_every_locale_documents_the_same_sdk_surface():
    """A locale page that silently drops methods is worse than an untranslated one."""
    for name in ("method-reference.md", "dto-reference.md", "contract-index.md"):
        pages = {root.relative_to(ROOT / "docs").parts[0]: (root / name) for root in DOC_ROOTS}
        present = {locale: path for locale, path in pages.items() if path.is_file()}
        assert len(present) == 3, f"{name} is missing a locale: {sorted(set(pages) - set(present))}"
        counts = {locale: len(METHOD_MENTION.findall(path.read_text(encoding="utf-8")))
                  for locale, path in present.items()}
        assert len(set(counts.values())) == 1, f"{name} locale drift: {counts}"
