from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/sdk/_data/gravewright-sdk-1.json"


def test_generated_sdk1_contract_covers_the_stable_registry_and_runtime() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_sdk1_contract.py")],
        cwd=ROOT,
        check=True,
    )
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    registry=json.loads((ROOT / "app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))
    expected={method for item in registry["capabilities"].values() for method in item.get("methods",[])}
    methods={item["path"] for item in contract["methods"]}
    assert contract["sdkVersion"]=="1"
    assert all(item["status"]=="stable" for item in contract["capabilities"])
    assert methods==expected
    assert all(item["signature"].startswith(f"sdk.{item['path']}(") for item in contract["methods"])
    assert all(item["requiredCapability"] in registry["capabilities"] for item in contract["methods"])
    assert len(contract["methods"]) == 187
    assert all(item["returns"] != "JsonValue" for item in contract["methods"])
    assert all(
        parameter["type"] not in {"object", "function", "JsonValue", "any", "unknown"}
        for item in contract["methods"]
        for parameter in item["parameters"]
    )
    assert all(
        all(item.get(field) for field in ("lifecycle", "concurrency", "visibility", "durability"))
        for item in contract["methods"]
    )
    assert contract["dynamicTypes"]
    assert all(
        item.get("typeExpression") and item.get("justification")
        for item in contract["dynamicTypes"].values()
    )
    assert {"ActorDTO","TokenDTO","WallDTO","LightDTO","ShaderPresetDTO","AutomationJobDTO","PDFPresentationDTO"} <= set(contract["dtos"])


def test_typescript_declarations_and_example_cover_the_public_contract() -> None:
    declarations=(ROOT / "docs/sdk/gravewright-sdk-1.d.ts").read_text(encoding="utf-8")
    for token in ("interface GravewrightSDK","interface ActorDTO","readonly scene:","apply(sceneId:","schedule(actionId:"):
        assert token in declarations
    manifest=json.loads((ROOT / "examples/minimal-addon/manifest.json").read_text(encoding="utf-8"))
    registry=json.loads((ROOT / "app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))
    assert manifest["sdkVersion"]=="1"
    assert set(manifest["capabilities"]) <= set(registry["capabilities"])


def test_no_discovery_packages_or_public_narrative_remain() -> None:
    assert not list((ROOT / "data/packages/addons").glob("sdk-" + "lab-*"))
    forbidden=("sdk-"+"lab","extension "+"lab","extension "+"gap","gap "+"sentinel","all-"+"green")
    for base in (ROOT / "docs", ROOT / "scripts", ROOT / "examples"):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md",".json",".py",".js",".d.ts"}:
                text=path.read_text(encoding="utf-8").lower()
                assert not [term for term in forbidden if term in text], path
