"""SDK 1 HTML sheet contract."""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.sdk.capability_registry import get_registry
from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest_validator import validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = (PROJECT_ROOT / "static" / "js" / "sdk" / "gravewright-sdk.js").read_text(
    encoding="utf-8"
)


def test_sheet_capabilities_are_stable_manifest_capabilities():
    registry = get_registry()
    for name in ("sheets.html", "sheets.controller", "sheets.richText"):
        cap = registry.capabilities.get(name)
        assert cap is not None, name
        assert cap.status == "stable", name
        assert "manifest" in cap.surfaces


def test_sheet_capabilities_are_known_to_the_validator():
    known = get_registry().known_names()
    assert {"sheets.html", "sheets.controller", "sheets.richText"} <= known


def _manifest(sheet: object, *, capabilities=None) -> dict:
    return {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "ruleset",
        "id": "html-ruleset",
        "name": "HTML Ruleset",
        "version": "1.0.0",
        "compatibility": {
            "minimum": "1.0.0-rc.1",
            "verified": "1.0.0-rc.1",
            "maximum": "1.x",
        },
        "capabilities": capabilities
        or ["sheets.html", "sheets.controller", "sheets.richText"],
        "activation": {"scope": "campaign", "mode": "exclusive"},
        "entrypoints": {},
        "provides": {
            "storage": {"model": "schemas/storage.schema.json"},
            "actorTypes": [
                {
                    "id": "character",
                    "label": "Character",
                    "schema": "schemas/character.schema.json",
                    "sheet": sheet,
                }
            ],
        },
    }


def _write_package(
    tmp_path,
    *,
    html='<h1 data-text="actor.name"></h1>',
    sheet=None,
):
    pkg = tmp_path / "html-ruleset"
    (pkg / "schemas").mkdir(parents=True)
    (pkg / "sheets").mkdir()
    (pkg / "scripts").mkdir()
    (pkg / "styles").mkdir()
    (pkg / "schemas" / "storage.schema.json").write_text("{}", encoding="utf-8")
    (pkg / "schemas" / "character.schema.json").write_text("{}", encoding="utf-8")
    (pkg / "sheets" / "character.html").write_text(html, encoding="utf-8")
    (pkg / "scripts" / "character-sheet.js").write_text("export {};", encoding="utf-8")
    (pkg / "styles" / "character-sheet.css").write_text(".sheet{}", encoding="utf-8")
    sheet = sheet or {
        "mode": "html",
        "template": "sheets/character.html",
        "controller": "scripts/character-sheet.js",
        "style": "styles/character-sheet.css",
    }
    (pkg / "manifest.json").write_text(json.dumps(_manifest(sheet)), encoding="utf-8")
    return pkg


def test_html_sheet_manifest_object_validates():
    result = validate_manifest(
        _manifest(
            {
                "mode": "html",
                "template": "sheets/character.html",
                "controller": "scripts/character-sheet.js",
                "style": "styles/character-sheet.css",
            }
        )
    )
    assert not [e for e in result.errors if e.startswith("sdk.sheets.html.")]


def test_html_sheet_requires_sheets_html_capability():
    result = validate_manifest(
        _manifest(
            {"mode": "html", "template": "sheets/character.html"},
            capabilities=["sheets.controller"],
        )
    )
    assert "sdk.sheets.html.capability_missing" in result.errors


def test_html_sheet_controller_requires_capability():
    result = validate_manifest(
        _manifest(
            {
                "mode": "html",
                "template": "sheets/character.html",
                "controller": "scripts/c.js",
            },
            capabilities=["sheets.html"],
        )
    )
    assert "sdk.sheets.html.controller_missing" in result.errors


def test_html_sheet_template_missing_fails(tmp_path):
    pkg = _write_package(tmp_path)
    (pkg / "sheets" / "character.html").unlink()
    loaded = load_package(pkg, expected_id="html-ruleset", expected_kind_root="rulesets")
    assert "sdk.sheets.html.template_missing" in loaded.validation.errors


def test_html_sheet_unsafe_template_path_fails():
    result = validate_manifest(_manifest({"mode": "html", "template": "../escape.html"}))
    assert "sdk.sheets.html.template_unsafe_path" in result.errors


def test_html_sheet_style_missing_fails(tmp_path):
    pkg = _write_package(tmp_path)
    (pkg / "styles" / "character-sheet.css").unlink()
    loaded = load_package(pkg, expected_id="html-ruleset", expected_kind_root="rulesets")
    assert "sdk.sheets.html.style_missing" in loaded.validation.errors


def test_html_sheet_unsafe_style_path_fails():
    result = validate_manifest(
        _manifest({"mode": "html", "template": "sheets/c.html", "style": "../escape.css"})
    )
    assert "sdk.sheets.html.style_unsafe_path" in result.errors


def test_html_sheet_inline_script_fails(tmp_path):
    pkg = _write_package(tmp_path, html="<div><script>alert(1)</script></div>")
    loaded = load_package(pkg, expected_id="html-ruleset", expected_kind_root="rulesets")
    assert "sdk.sheets.html.inline_script_forbidden" in loaded.validation.errors


def test_html_sheet_inline_event_handler_fails(tmp_path):
    pkg = _write_package(tmp_path, html='<button onclick="x()">Roll</button>')
    loaded = load_package(pkg, expected_id="html-ruleset", expected_kind_root="rulesets")
    assert "sdk.sheets.html.inline_handler_forbidden" in loaded.validation.errors


def test_html_sheet_rich_text_requires_capability(tmp_path):
    pkg = _write_package(tmp_path, html='<div data-rich-text="system.bio"></div>')
    raw = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    raw["capabilities"] = ["sheets.html", "sheets.controller"]
    (pkg / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")
    loaded = load_package(pkg, expected_id="html-ruleset", expected_kind_root="rulesets")
    assert "sdk.sheets.html.rich_text_capability_missing" in loaded.validation.errors


def test_register_controller_lifecycle_and_bindings_present():
    assert "registerController(sheetType, controller)" in RUNTIME
    assert "registerSheetController(pkg.id, sheetType, controller)" in RUNTIME
    assert "controller.setup" in RUNTIME
    assert "controller.mount" in RUNTIME
    assert "controller.update" in RUNTIME
    assert "controller.unmount" in RUNTIME
    assert "controller.onAction" in RUNTIME


def test_data_text_uses_text_content():
    assert "node.textContent = getPath(ctx.data, node.dataset.text)" in RUNTIME


def test_data_rich_text_is_sanitized():
    assert "sanitizeRichText" in RUNTIME
    assert "node.innerHTML = sanitizeRichText" in RUNTIME


def test_unmount_cleans_listeners():
    assert "cleanups.forEach((fn) => fn())" in RUNTIME
    assert "mountedSheets.delete(root)" in RUNTIME


# --- end-to-end wiring: backend metadata + asset serving --------------------

ACTOR_RENDERER = (
    PROJECT_ROOT / "static" / "js" / "sheets" / "actors" / "actor-sheet-renderer.js"
).read_text(encoding="utf-8")
ITEM_RENDERER = (
    PROJECT_ROOT / "static" / "js" / "sheets" / "items" / "item-sheet-renderer.js"
).read_text(encoding="utf-8")
ACTOR_CONTROLLER = (
    PROJECT_ROOT / "static" / "js" / "sheets" / "actors" / "actor-sheet-controller.js"
).read_text(encoding="utf-8")


def _install_html_ruleset(monkeypatch, tmp_path, *, sheet=None, html=None):
    """Create + install + enable a minimal HTML-sheet ruleset on disk."""
    from app.engine.sdk import package_registry
    from app.engine.sdk.package_install_service import PackageInstallService

    packages_root = tmp_path / "packages"
    pkg = packages_root / "rulesets" / "html-ruleset"
    (pkg / "schemas").mkdir(parents=True)
    (pkg / "sheets").mkdir()
    (pkg / "scripts").mkdir()
    (pkg / "styles").mkdir()
    (pkg / "schemas" / "storage.schema.json").write_text("{}", encoding="utf-8")
    (pkg / "schemas" / "character.schema.json").write_text("{}", encoding="utf-8")
    (pkg / "sheets" / "character.html").write_text(
        html or '<h1 data-text="actor.name"></h1>', encoding="utf-8"
    )
    (pkg / "scripts" / "character-sheet.js").write_text("export {};", encoding="utf-8")
    (pkg / "styles" / "character-sheet.css").write_text(".sheet{}", encoding="utf-8")
    sheet = sheet or {
        "mode": "html",
        "template": "sheets/character.html",
        "controller": "scripts/character-sheet.js",
        "style": "styles/character-sheet.css",
    }
    # A string sheet is a declarative Sheet IR path; it must exist on disk for
    # the loader's referenced-path check to pass at install time.
    if isinstance(sheet, str) and sheet:
        layout = {"kind": "actorSheet", "body": {"type": "section", "children": []}}
        (pkg / sheet).write_text(json.dumps(layout), encoding="utf-8")
    (pkg / "manifest.json").write_text(json.dumps(_manifest(sheet)), encoding="utf-8")

    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    svc = PackageInstallService()
    assert svc.install(package_id="html-ruleset", user_id=None).success
    assert svc.enable(package_id="html-ruleset").success
    return pkg


def test_html_actor_sheet_bundle_exposes_html_mode(db, monkeypatch, tmp_path):
    from app.engine.sheets.system_layout_service import SystemLayoutService

    _install_html_ruleset(monkeypatch, tmp_path)
    layouts = SystemLayoutService()
    descriptor = layouts.get_actor_html_sheet(system_id="html-ruleset", actor_type="character")
    assert descriptor == {
        "mode": "html",
        "template": "sheets/character.html",
        "controller": "scripts/character-sheet.js",
        "style": "styles/character-sheet.css",
    }
    # An HTML sheet suppresses the declarative Sheet IR path entirely.
    assert layouts.get_actor_sheet(system_id="html-ruleset", actor_type="character") is None


def test_declarative_sheet_still_resolves(db, monkeypatch, tmp_path):
    from app.engine.sheets.system_layout_service import SystemLayoutService

    _install_html_ruleset(monkeypatch, tmp_path, sheet="sheets/character.json")

    layouts = SystemLayoutService()
    assert layouts.get_actor_html_sheet(system_id="html-ruleset", actor_type="character") is None
    resolved = layouts.get_actor_sheet(system_id="html-ruleset", actor_type="character")
    assert resolved is not None and resolved["kind"] == "actorSheet"


def test_html_sheet_template_asset_is_served(db, monkeypatch, tmp_path):
    from app.engine.sdk.package_asset_service import PackageAssetService

    _install_html_ruleset(monkeypatch, tmp_path)
    resolved = PackageAssetService().resolve("html-ruleset", "sheets/character.html")
    assert resolved is not None
    path, content_type = resolved
    assert content_type == "text/html; charset=utf-8"
    assert path.name == "character.html"


def test_html_sheet_template_asset_must_be_declared(db, monkeypatch, tmp_path):
    from app.engine.sdk.package_asset_service import PackageAssetService

    pkg = _install_html_ruleset(monkeypatch, tmp_path)
    # An undeclared HTML file on disk must not be fetchable.
    (pkg / "sheets" / "secret.html").write_text("<p>secret</p>", encoding="utf-8")
    assert PackageAssetService().resolve("html-ruleset", "sheets/secret.html") is None
    # Traversal outside the declared set is rejected too.
    assert PackageAssetService().resolve("html-ruleset", "../manifest.json") is None


# --- frontend wiring: renderer mounts the HTML template ---------------------


def test_html_sheet_renderer_mounts_template():
    for renderer in (ACTOR_RENDERER, ITEM_RENDERER):
        assert 'bundle.sheet.mode === "html"' in renderer
        assert "renderHtmlSheet(root, bundle)" in renderer
        assert "window.GravewrightHTMLSheets" in renderer
        assert "/sdk/packages/${encodeURIComponent(packageId)}/asset/${sheet.template}" in renderer
        assert "HTML.mount(packageId, sheetType, root" in renderer
        assert "HTML.unmount(root)" in renderer


def test_html_sheet_data_bind_writes_back_through_normal_path():
    # The runtime forwards edits via ctx.onChange; the renderer maps them onto
    # the existing actor/item sheet patch path (FI.writePath).
    assert "ctx.onChange?.(path, next)" in RUNTIME
    assert "onChange: (path, value) => writeHtmlSheetPath(root, path, value)" in ACTOR_RENDERER
    assert "FI.writePath" in ACTOR_RENDERER
    assert "FI.writePath = writePath" in ACTOR_CONTROLLER


def test_html_sheet_data_action_calls_controller():
    assert "controller.onAction?.(" in RUNTIME


def test_html_sheet_declarative_path_preserved():
    # The declarative renderer path is only taken when there is no HTML sheet.
    assert "buildNode(layout.body, rc)" in ACTOR_RENDERER
    assert "buildNode(layout.body, rc)" in ITEM_RENDERER


def test_html_sheet_unmount_wired_to_modal_close():
    events = (
        PROJECT_ROOT / "static" / "js" / "sheets" / "actors" / "actor-sheet-events.js"
    ).read_text(encoding="utf-8")
    assert 'addEventListener("vtt:modal-closed"' in events
    assert "GravewrightHTMLSheets?.unmount?.(root)" in events
