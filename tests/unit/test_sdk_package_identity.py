"""Phase 5 — manifest identity and kind-root binding.

A package's on-disk location is bound to its manifest: the directory name must
equal ``manifest.id`` and the kind_plural root must match ``manifest.kind``.
Mismatches are structural errors with stable codes; the registry reports rather
than silently hides them, and the doctor surfaces them.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.sdk import package_registry
from app.engine.sdk.package_loader import (
    LoadedPackage,
    load_package,
)
from app.engine.sdk.package_manifest import (
    DIRECTORY_TO_KIND,
    KIND_TO_DIRECTORY,
    PackageKind,
    PackageManifest,
)
from app.engine.sdk.package_manifest_validator import PackageManifestValidation
from app.engine.sdk.package_registry import (
    load_all,
    load_by_package_id,
    package_dir_for,
    storage_dir_for,
)
from tests.conftest import install_system, seed_user


def _manifest(**overrides) -> dict:
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "addon",
        "id": "my-addon",
        "name": "My Addon",
        "version": "0.1.0",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["assets.scripts"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {},
    }
    manifest.update(overrides)
    return manifest


def _write(directory: Path, manifest: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


# --- mapping -----------------------------------------------------------------


def test_all_sdk_kinds_have_directory_mapping():
    for kind in PackageKind.values():
        assert kind in KIND_TO_DIRECTORY, kind
    # The mapping is a bijection.
    assert DIRECTORY_TO_KIND == {v: k for k, v in KIND_TO_DIRECTORY.items()}
    assert set(KIND_TO_DIRECTORY) == PackageKind.values()


def test_storage_resolution_uses_validated_kind_and_package_id():
    storage = storage_dir_for("ruleset", "dnd5e")
    assert storage is not None
    assert storage.as_posix().endswith("storage/packages/rulesets/dnd5e")
    # Unknown kind / unsafe id never resolve.
    assert storage_dir_for("bogus", "dnd5e") is None
    assert storage_dir_for("ruleset", "../etc") is None
    assert package_dir_for("addon", "my-addon").as_posix().endswith("packages/addons/my-addon")


# --- loader binding ----------------------------------------------------------


def test_manifest_id_must_match_package_directory(tmp_path):
    directory = _write(tmp_path / "foo", _manifest(id="bar"))
    loaded = load_package(directory, expected_id="foo", expected_kind_root=None)
    assert "sdk.manifest.id_mismatch" in loaded.validation.errors


def test_id_mismatch_returns_stable_error_code(tmp_path):
    directory = _write(tmp_path / "foo", _manifest(id="bar"))
    loaded = load_package(directory, expected_id="foo")
    assert "sdk.manifest.id_mismatch" in loaded.validation.errors


def test_package_kind_must_match_root_directory(tmp_path):
    # An addon manifest under the rulesets/ root mismatches.
    directory = _write(tmp_path / "my-addon", _manifest(kind="addon"))
    loaded = load_package(directory, expected_id="my-addon", expected_kind_root="rulesets")
    assert "sdk.manifest.kind_root_mismatch" in loaded.validation.errors

    # A matching kind/root passes the binding check.
    ok_dir = _write(tmp_path / "my-addon2", _manifest(id="my-addon2", kind="addon"))
    ok = load_package(ok_dir, expected_id="my-addon2", expected_kind_root="addons")
    assert "sdk.manifest.kind_root_mismatch" not in ok.validation.errors


# --- registry discovery ------------------------------------------------------


def test_registry_discovers_grouped_and_flat(tmp_path):
    _write(tmp_path / "addons" / "grouped-addon", _manifest(id="grouped-addon"))
    _write(tmp_path / "legacy-flat", _manifest(id="legacy-flat"))

    loaded = {p.id: p for p in load_all(tmp_path)}
    assert "grouped-addon" in loaded
    assert "legacy-flat" in loaded
    assert loaded["grouped-addon"].kind_dir == "addons"
    assert loaded["grouped-addon"].is_flat_layout is False
    assert loaded["legacy-flat"].is_flat_layout is True


def test_registry_skips_or_reports_id_mismatch(tmp_path):
    # Directory says "foo" but the manifest claims "bar": discovered + reported.
    _write(tmp_path / "addons" / "foo", _manifest(id="bar"))
    loaded = load_all(tmp_path)
    assert len(loaded) == 1
    assert "sdk.manifest.id_mismatch" in loaded[0].validation.errors

    by_id = load_by_package_id("foo", tmp_path)
    assert by_id is not None
    assert "sdk.manifest.id_mismatch" in by_id.validation.errors


# --- doctor ------------------------------------------------------------------


def _fake_loaded(*, errors: list[str], kind_dir: str | None) -> LoadedPackage:
    raw = _manifest()
    return LoadedPackage(
        package_dir=Path("x"),
        manifest=PackageManifest.from_dict(raw),
        validation=PackageManifestValidation(errors=list(errors)),
        raw=raw,
        kind_dir=kind_dir,
    )


def test_doctor_reports_manifest_id_mismatch(db, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    gm = seed_user(email="identity-id@test.com")
    install_system(gm, package_id="dnd5e")
    monkeypatch.setattr(
        package_registry,
        "load_by_package_id",
        lambda pid, *a, **k: _fake_loaded(errors=["sdk.manifest.id_mismatch"], kind_dir="rulesets"),
    )
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.manifest.id_mismatch" in codes


def test_doctor_reports_kind_root_mismatch(db, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    gm = seed_user(email="identity-kind@test.com")
    install_system(gm, package_id="dnd5e")
    monkeypatch.setattr(
        package_registry,
        "load_by_package_id",
        lambda pid, *a, **k: _fake_loaded(
            errors=["sdk.manifest.kind_root_mismatch"], kind_dir="addons"
        ),
    )
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.manifest.kind_root_mismatch" in codes


def test_doctor_reports_flat_layout(db, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    gm = seed_user(email="identity-flat@test.com")
    install_system(gm, package_id="dnd5e")
    monkeypatch.setattr(
        package_registry,
        "load_by_package_id",
        lambda pid, *a, **k: _fake_loaded(errors=[], kind_dir=None),
    )
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "package_flat_layout" in codes


# --- asset resolution --------------------------------------------------------


def test_asset_resolution_uses_validated_package_id(db):
    from app.engine.sdk.package_asset_service import PackageAssetService

    gm = seed_user(email="identity-asset@test.com")
    install_system(gm, package_id="dnd5e")
    resolved = PackageAssetService().resolve("dnd5e", "assets/dnd5e.css")
    assert resolved is not None
    path, content_type = resolved
    assert content_type == "text/css"
    assert path.is_file()
    # Served from the grouped location, never a flat or traversed path.
    assert "rulesets/dnd5e" in path.as_posix()
