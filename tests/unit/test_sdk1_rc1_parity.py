"""RC 1 parity: one public surface, described identically everywhere.

Every method must exist in the runtime gate map, the capability registry, the
machine contract, the TypeScript definitions, all three locale references, and be
recognised by Package Doctor. A method documented but unreachable — or reachable
but undocumented — is a certification failure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.engine.sdk.capability_registry import get_registry


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
DTS = (ROOT / "docs/sdk/gravewright-sdk-1.d.ts").read_text(encoding="utf-8")
REFERENCES = {
    "en": (ROOT / "docs/sdk/method-reference.md").read_text(encoding="utf-8"),
    "pt-br": (ROOT / "docs/pt-br/sdk/method-reference.md").read_text(encoding="utf-8"),
    "es": (ROOT / "docs/es/sdk/method-reference.md").read_text(encoding="utf-8"),
}
INDEXES = {
    "en": (ROOT / "docs/sdk/contract-index.md").read_text(encoding="utf-8"),
    "pt-br": (ROOT / "docs/pt-br/sdk/contract-index.md").read_text(encoding="utf-8"),
    "es": (ROOT / "docs/es/sdk/contract-index.md").read_text(encoding="utf-8"),
}

METHODS = {item["path"]: item for item in CONTRACT["methods"]}
REGISTRY = get_registry()


def test_the_registry_and_the_machine_contract_describe_the_same_methods():
    registry_methods = set(REGISTRY.method_to_capability())
    assert set(METHODS) == registry_methods
    for path, item in METHODS.items():
        assert item["requiredCapability"] == REGISTRY.method_to_capability()[path], path


@pytest.mark.parametrize("path", sorted(METHODS))
def test_every_public_method_is_documented_in_every_locale(path):
    for locale, text in REFERENCES.items():
        assert f"## `sdk.{path}(" in text, f"{path} missing from {locale} method reference"


@pytest.mark.parametrize("path", sorted(METHODS))
def test_every_public_method_is_typed_in_the_d_ts(path):
    # The final segment is the declared member name on its namespace object.
    member = path.split(".")[-1]
    assert re.search(rf"\b{re.escape(member)}\s*[(<:]", DTS), f"{path} missing from gravewright-sdk-1.d.ts"


@pytest.mark.parametrize("path", sorted(METHODS))
def test_every_public_method_resolves_a_declared_capability_and_typed_shape(path):
    item = METHODS[path]
    assert item["requiredCapability"] in {c["name"] for c in CONTRACT["capabilities"]}
    assert item["returns"] and item["returns"] not in {"any", "unknown", "JsonValue"}
    assert item["errors"], path
    for field in ("authority", "visibility", "concurrency", "durability", "lifecycle"):
        assert item.get(field) or field == "authority", f"{path} missing {field}"
    for parameter in item["parameters"]:
        assert parameter["type"] not in {"any", "unknown", "object", "function"}, f"{path}({parameter['name']})"


def test_every_capability_event_and_error_appears_in_every_locale_index():
    names = [c["name"] for c in CONTRACT["capabilities"]]
    events = [e["name"] if isinstance(e, dict) else e for e in CONTRACT["events"]]
    for locale, text in INDEXES.items():
        for name in names + events + CONTRACT["errors"]:
            assert f"`{name}`" in text, f"{name} missing from {locale} contract index"


def test_package_doctor_recognises_every_public_method_and_capability():
    """Doctor gates packages against the same registry the contract is built from."""
    doctor_methods = REGISTRY.method_to_capability()
    for path, item in METHODS.items():
        assert doctor_methods.get(path) == item["requiredCapability"], path
    for capability in {c["name"] for c in CONTRACT["capabilities"]}:
        assert REGISTRY.status_of(capability) is not None, capability
        assert capability not in REGISTRY.forbidden_names(), capability


@pytest.mark.parametrize("namespace", [
    "scene.shaders.customLibrary", "scene.spatialSounds", "sounds", "campaign",
    "workflows", "gameplay.flows", "timelines", "ui.dragDrop", "ui.applications",
])
def test_deep_namespaces_are_fully_represented(namespace):
    """Nested namespaces are the easiest place for a surface to go missing."""
    paths = [p for p in METHODS if p == namespace or p.startswith(f"{namespace}.")]
    assert paths, namespace
    for path in paths:
        assert REGISTRY.method_to_capability().get(path)
        for text in REFERENCES.values():
            assert f"## `sdk.{path}(" in text


def test_the_contract_has_no_unresolved_shapes():
    assert CONTRACT["sdkVersion"] == "1"
    unresolved_returns = [m["path"] for m in CONTRACT["methods"]
                          if m["returns"] in {"", "any", "unknown", "JsonValue"}]
    unresolved_parameters = [f"{m['path']}({p['name']})" for m in CONTRACT["methods"]
                             for p in m["parameters"]
                             if p["type"] in {"", "any", "unknown", "object", "function"}]
    assert unresolved_returns == []
    assert unresolved_parameters == []
    for name, dto in CONTRACT["dtos"].items():
        for field, value in (dto.get("properties") or {}).items():
            assert value.get("typeExpression") not in {"", "any", "unknown"}, f"{name}.{field}"
