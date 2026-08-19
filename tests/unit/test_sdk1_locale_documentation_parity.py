import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
LOCALES = {"en": ROOT / "docs/sdk", "pt-br": ROOT / "docs/pt-br/sdk", "es": ROOT / "docs/es/sdk"}


def _headings(path: Path, level: int) -> list[str]:
    return re.findall(rf"^{'#' * level} `([^`]+)`$", path.read_text(encoding="utf-8"), re.MULTILINE)


def test_all_locales_expose_the_exact_canonical_method_set():
    expected = [method["signature"] for method in CONTRACT["methods"]]
    for locale, directory in LOCALES.items():
        assert _headings(directory / "method-reference.md", 2) == expected, locale
    registry=json.loads((ROOT / "app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))
    assert len(expected) == len({method for value in registry["capabilities"].values() for method in value.get("methods", [])})


def test_all_locales_expose_the_exact_dto_alias_and_semantic_type_set():
    expected = set(CONTRACT["dtos"]) | set(CONTRACT["typeAliases"]) | set(CONTRACT["dynamicTypes"])
    for locale, directory in LOCALES.items():
        assert set(_headings(directory / "dto-reference.md", 2)) == expected, locale


def test_capability_event_and_error_indexes_have_full_locale_parity():
    expected = set(capability["name"] for capability in CONTRACT["capabilities"])
    expected |= set(event["name"] for event in CONTRACT["events"])
    expected |= set(CONTRACT["errors"])
    for locale, directory in LOCALES.items():
        text = (directory / "contract-index.md").read_text(encoding="utf-8")
        identifiers = set(re.findall(r"^(?:### |- )`([^`]+)`", text, re.MULTILINE))
        assert identifiers == expected, locale


def test_quick_start_code_is_identical_and_javascript_is_valid():
    blocks = {}
    for locale, directory in LOCALES.items():
        text = (directory / "quick-start.md").read_text(encoding="utf-8")
        blocks[locale] = re.findall(r"```(?:json|js)\n(.*?)```", text, re.DOTALL)
        assert len(blocks[locale]) == 2
        manifest = json.loads(blocks[locale][0])
        assert manifest["sdkVersion"] == "1" and manifest["capabilities"]
    assert blocks["en"] == blocks["pt-br"] == blocks["es"]
    checked = subprocess.run(["node", "--check", "-"], input=blocks["en"][1], text=True, capture_output=True)
    assert checked.returncode == 0, checked.stderr


def test_public_sdk_docs_contain_no_discovery_residue_or_historical_scores():
    discovery_terms = [
        "sdk" + "-lab", "extension" + "-gap", "extension" + " lab",
        "gap" + " sentinel", "all" + "-green", "remaining" + " gaps",
        "closure" + " score",
    ]
    forbidden = re.compile("|".join(map(re.escape, discovery_terms)) + r"|r" + r"ound (?:[1-9]|1[0-4])|(?:17|80|93)" + "%", re.I)
    for directory in LOCALES.values():
        for path in directory.glob("*.md"):
            assert not forbidden.search(path.read_text(encoding="utf-8")), path
