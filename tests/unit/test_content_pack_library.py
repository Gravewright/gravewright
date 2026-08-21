from types import SimpleNamespace

from app.engine.content.content_pack_service import ContentPackService
from app.engine.sdk.package_manifest import PackageContentPack
from app.engine.sdk.package_manifest_validator import validate_manifest


class _Manifest:
    @staticmethod
    def _resolve_label(label, label_key, locale):
        return label or label_key

    @staticmethod
    def load_locale(base, locale):
        return {}


def _service(tmp_path, pack, payload):
    service = ContentPackService.__new__(ContentPackService)
    service.installed = SimpleNamespace(get=lambda package_id: {"package_dir": "unused"})
    service._cache = {}
    service._source = lambda package_id, pack_id: (tmp_path, _Manifest(), pack, payload)
    return service


def test_format_two_indexes_without_loading_document(tmp_path):
    pack = PackageContentPack(
        id="bestiary", type="document_pack", label="Bestiary", path="index.json",
        document_type="ruleset.creature", format_version=2,
    )
    service = _service(tmp_path, pack, {
        "index": [
            {"id": "owl", "name": "Owl", "type": "beast", "document": "docs/owl.json"},
            {"id": "wolf", "name": "Wolf", "type": "beast", "document": "docs/wolf.json"},
        ]
    })

    page = service.get_index("nature", "bestiary", query="wolf", limit=1)

    assert page["total"] == 1
    assert page["entries"] == [{
        "id": "wolf", "name": "Wolf", "type": "beast",
        "document_type": "ruleset.creature", "ref": "gwpack://nature/bestiary/wolf",
    }]
    assert "document" not in page["entries"][0]


def test_format_two_loads_full_document_only_for_requested_entry(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "owl.json").write_text('{"name":"Owl","data":{"hp":2}}', encoding="utf-8")
    pack = PackageContentPack(
        id="bestiary", type="document_pack", label="", path="index.json",
        document_type="ruleset.creature", format_version=2,
    )
    service = _service(tmp_path, pack, {
        "index": [{"id": "owl", "name": "Index name", "document": "docs/owl.json"}]
    })

    document = service.get_entry("nature", "bestiary", "owl")

    assert document["name"] == "Owl"
    assert document["data"] == {"hp": 2}
    assert document["ref"] == "gwpack://nature/bestiary/owl"


def test_sdk_one_accepts_system_agnostic_custom_document_type():
    manifest = {
        "schemaVersion": 1, "sdkVersion": "1", "kind": "content", "id": "lore-library",
        "name": "Lore Library", "version": "1.0.0",
        "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": ["content.packs"],
        "activation": {"scope": "campaign", "mode": "multiple"}, "entrypoints": {},
        "provides": {"contentPacks": [{
        "id": "lore", "type": "document_pack", "documentType": "ruleset.clue",
        "path": "content/lore.json", "formatVersion": 2,
        "indexFields": ["name", "tags"],
        }]},
    }

    assert "sdk.validation.content_pack_invalid" not in validate_manifest(manifest).errors


def test_bad_format_version_is_a_validation_error_not_a_parser_crash():
    manifest = {
        "schemaVersion": 1, "sdkVersion": "1", "kind": "content", "id": "bad-pack",
        "name": "Bad Pack", "version": "1.0.0",
        "compatibility": {"minimum": "1", "verified": "1"},
        "capabilities": ["content.packs"],
        "activation": {"scope": "campaign", "mode": "multiple"}, "entrypoints": {},
        "provides": {"contentPacks": [{"id": "bad", "type": "document_pack",
                                        "path": "bad.json", "formatVersion": "latest"}]},
    }

    assert "sdk.validation.content_pack_invalid" in validate_manifest(manifest).errors
