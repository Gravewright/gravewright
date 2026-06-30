from __future__ import annotations

from dataclasses import dataclass

from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sheets.sheet_drop_service import (
    HTML_DROP_LIST,
    HTML_EFFECT_LIST,
    SheetDropService,
    _html_list_path,
)
from app.engine.sheets.sheet_ir_validator import accepts_entry


@dataclass
class _Entry:
    payload: dict

    def as_dict(self) -> dict:
        return self.payload


class _FakeStorage:
    def __init__(self, envelope=None):
        self.envelope = envelope
        self.written = None

    def read_actor(self, **_kw):
        return self.envelope

    def write_actor(self, **kw):
        self.written = kw


_ACTOR = {"id": "a1", "system_id": "my-rpg", "campaign_id": "c1"}


def test_generic_drop_namespaces_accept_specific_entries():
    assert accepts_entry(["item"], "item.weapon")
    assert accepts_entry(["effect"], "effect.condition")
    assert not accepts_entry(["item"], "effect.condition")


def _manifest(sheet):
    return PackageManifest.from_dict(
        {
            "schemaVersion": 1,
            "sdkVersion": "1",
            "kind": "ruleset",
            "id": "my-rpg",
            "name": "My RPG",
            "version": "0.1.0",
            "provides": {"actorTypes": [{"id": "character", "schema": "s.json", "sheet": sheet}]},
        }
    )


def test_html_list_path_routes_to_named_zone():
    # A sheet template names per-category lists (skills, edges, gear). Each
    # resolves to its own data key so dropped items land where the sheet reads.
    assert _html_list_path("skillItems") == "skillItems"
    assert _html_list_path("equipmentItems") == "equipmentItems"
    assert _html_list_path("effects") == "effects"


def test_html_list_path_sanitizes_unsafe_zone_names():
    # The zone name is used as a single data key, never a path, so dots and other
    # traversal characters are stripped rather than trusted.
    assert _html_list_path("system.skills.../../x") == "systemskillsx"
    assert _html_list_path("") == HTML_DROP_LIST
    assert _html_list_path("   ") == HTML_DROP_LIST


def test_append_to_html_list_creates_items_array():
    svc = SheetDropService()
    svc.storage = _FakeStorage(envelope={"version": 3, "data": {}})
    entry = _Entry({"id": "i1", "name": "Sword", "type": "weapon"})

    result = svc._append_to_html_list(_ACTOR, entry)

    assert result.success
    assert result.version == 4
    assert result.changed_paths == [HTML_DROP_LIST]
    assert svc.storage.written["data"]["items"] == [{"id": "i1", "name": "Sword", "type": "weapon"}]


def test_append_to_html_list_appends_to_existing():
    svc = SheetDropService()
    svc.storage = _FakeStorage(envelope={"version": 1, "data": {"items": [{"id": "old"}]}})
    result = svc._append_to_html_list(_ACTOR, _Entry({"id": "new"}))
    assert result.success
    ids = [it["id"] for it in svc.storage.written["data"]["items"]]
    assert ids == ["old", "new"]


def test_append_to_html_effect_list_is_separate_from_items():
    svc = SheetDropService()
    svc.storage = _FakeStorage(envelope={"version": 1, "data": {"items": [{"id": "i1"}]}})
    result = svc._append_to_html_list(
        _ACTOR,
        _Entry({"id": "e1", "type": "effect", "data": {"modifiers": []}}),
        list_path=HTML_EFFECT_LIST,
    )
    assert result.success
    assert result.changed_paths == ["effects"]
    assert svc.storage.written["data"]["items"] == [{"id": "i1"}]
    assert svc.storage.written["data"]["effects"][0]["id"] == "e1"


def test_is_html_sheet_detects_mode(monkeypatch):
    svc = SheetDropService()
    html = _manifest({"mode": "html", "template": "sheets/character.html"})
    declarative = _manifest("layouts/actors/character.sheet.json")

    monkeypatch.setattr(svc.systems, "get_active_manifest", lambda _sid: html)
    assert svc._is_html_sheet("my-rpg", "character") is True

    monkeypatch.setattr(svc.systems, "get_active_manifest", lambda _sid: declarative)
    assert svc._is_html_sheet("my-rpg", "character") is False

    monkeypatch.setattr(svc.systems, "get_active_manifest", lambda _sid: None)
    assert svc._is_html_sheet("my-rpg", "character") is False
