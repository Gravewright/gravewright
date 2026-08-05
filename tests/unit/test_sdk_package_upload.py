"""Upload-a-ZIP install for SDK packages (Inside > Add-ons)."""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_user

MANIFEST = {
    "schemaVersion": 1,
    "sdkVersion": "1",
    "name": "Uploaded",
    "version": "1.0.0",
    "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
    "entrypoints": {},
    "provides": {},
    "capabilities": ["assets.scripts"],
    "activation": {"scope": "campaign", "mode": "multiple"},
    "id": "uploaded-addon",
    "kind": "addon",
}


def _zip(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content.encode() if isinstance(content, str) else content)
    return buf.getvalue()


RULESET_MANIFEST = {
    "schemaVersion": 1,
    "sdkVersion": "1",
    "name": "Uploaded Ruleset",
    "version": "1.0.0",
    "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
    "entrypoints": {},
    "provides": {"storage": {"model": "fixture"}, "actorTypes": [{"id": "character"}]},
    "capabilities": ["actors.register"],
    "activation": {"scope": "campaign", "mode": "exclusive"},
    "id": "uploaded-ruleset",
    "kind": "ruleset",
}


def _manifest_zip(*, root: str = "", **overrides) -> bytes:
    manifest = json.dumps({**MANIFEST, **overrides})
    return _zip({f"{root}manifest.json": manifest})


def _ruleset_zip(**overrides) -> bytes:
    return _zip({"manifest.json": json.dumps({**RULESET_MANIFEST, **overrides})})


@pytest.fixture
def packages_dir(tmp_path, monkeypatch):
    target = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", target)
    return target


def test_upload_installs_valid_zip(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(), user_id=None, replace=False
    )
    assert result.success, result.error_key
    assert result.package_id == "uploaded-addon"
    assert (packages_dir / "addons" / "uploaded-addon" / "manifest.json").is_file()
    record = svc.get("uploaded-addon")
    assert record is not None and record["status"] == "installed"


def test_upload_accepts_single_root_folder(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(root="uploaded-addon/"), user_id=None
    )
    assert result.success, result.error_key
    assert (packages_dir / "addons" / "uploaded-addon" / "manifest.json").is_file()


def test_upload_rejects_non_zip(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(filename="pkg.txt", data=b"nope", user_id=None)
    assert not result.success
    assert result.error_key == "inside.addons.errors.package_invalid"


def test_upload_rejects_path_traversal(db, packages_dir):
    svc = PackageInstallService()
    data = _zip({"manifest.json": json.dumps(MANIFEST), "../evil.txt": "x"})
    result = svc.install_uploaded_archive(filename="pkg.zip", data=data, user_id=None)
    assert not result.success
    assert result.error_key == "inside.addons.errors.package_unsafe"


def test_upload_rejects_invalid_manifest(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_zip({"manifest.json": "{not json"}), user_id=None
    )
    assert not result.success
    assert result.error_key == "sdk.errors.invalid_manifest"


def test_upload_rejects_missing_manifest(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_zip({"readme.txt": "hi"}), user_id=None
    )
    assert not result.success
    assert result.error_key == "sdk.errors.invalid_manifest"


def test_upload_duplicate_requires_replace_then_replaces(db, packages_dir):
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(filename="pkg.zip", data=_manifest_zip(), user_id=None).success

    # Without replace: blocked with a clear, recoverable error.
    blocked = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(version="1.1.0"), user_id=None
    )
    assert not blocked.success
    assert blocked.error_key == "inside.addons.errors.package_exists"

    # With replace, while only installed (not enabled): succeeds and updates files.
    replaced = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(version="1.1.0"), user_id=None, replace=True
    )
    assert replaced.success, replaced.error_key
    manifest = json.loads(
        (packages_dir / "addons" / "uploaded-addon" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "1.1.0"


def test_upload_replace_blocked_while_enabled(db, packages_dir):
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(filename="pkg.zip", data=_manifest_zip(), user_id=None).success
    assert svc.enable(package_id="uploaded-addon").success

    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(version="1.1.0"), user_id=None, replace=True
    )
    assert not result.success
    assert result.error_key == "inside.addons.errors.disable_before_replace"


def test_upload_ruleset_installs_for_ruleset_tab(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="rs.zip", data=_ruleset_zip(), user_id=None, expected_group="ruleset"
    )
    assert result.success, result.error_key
    assert (packages_dir / "rulesets" / "uploaded-ruleset" / "manifest.json").is_file()


def test_addon_rejected_in_ruleset_tab(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(), user_id=None, expected_group="ruleset"
    )
    assert not result.success
    assert result.error_key == "inside.rulesets.errors.not_a_ruleset_package"
    assert not (packages_dir / "addons" / "uploaded-addon").exists()


def test_ruleset_rejected_in_addon_tab(db, packages_dir):
    svc = PackageInstallService()
    result = svc.install_uploaded_archive(
        filename="rs.zip", data=_ruleset_zip(), user_id=None, expected_group="addon"
    )
    assert not result.success
    assert result.error_key == "inside.addons.errors.ruleset_not_allowed"
    assert not (packages_dir / "rulesets" / "uploaded-ruleset").exists()


def test_upload_route_installs_for_owner(db, packages_dir):
    from litestar.testing import TestClient

    from main import app

    owner_id = seed_user(name="Owner", email="owner-upload@test.com")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner_id)
        resp = client.post(
            "/sdk/packages/upload",
            files={"package_file": ("pkg.zip", _manifest_zip(), "application/zip")},
            data={"replace": "false"},
            follow_redirects=False,
        )

    assert resp.status_code in (301, 302, 303, 307, 308)
    assert "packages_message_key=inside.addons.messages.uploaded" in resp.headers["location"]
    assert (packages_dir / "addons" / "uploaded-addon" / "manifest.json").is_file()


def test_remove_deletes_addon_files_from_disk(db, packages_dir):
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(filename="pkg.zip", data=_manifest_zip(), user_id=None).success
    pkg_dir = packages_dir / "addons" / "uploaded-addon"
    assert pkg_dir.is_dir()

    result = svc.remove(package_id="uploaded-addon", delete_files=True)
    assert result.success, result.error_key
    assert not pkg_dir.exists()
    assert svc.get("uploaded-addon") is None
    # Gone for good: not rediscovered on disk as "available".
    assert all(item["id"] != "uploaded-addon" for item in svc.list_for_tab())


def test_remove_deletes_ruleset_files_from_disk(db, packages_dir):
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(
        filename="rs.zip", data=_ruleset_zip(), user_id=None, expected_group="ruleset"
    ).success
    pkg_dir = packages_dir / "rulesets" / "uploaded-ruleset"
    assert pkg_dir.is_dir()

    assert svc.remove(package_id="uploaded-ruleset", delete_files=True).success
    assert not pkg_dir.exists()


def test_remove_without_delete_files_keeps_dir(db, packages_dir):
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(filename="pkg.zip", data=_manifest_zip(), user_id=None).success
    assert svc.remove(package_id="uploaded-addon", delete_files=False).success
    assert (packages_dir / "addons" / "uploaded-addon").is_dir()


def test_remove_route_deletes_files(db, packages_dir):
    from litestar.testing import TestClient

    from main import app

    owner_id = seed_user(name="Owner", email="owner-remove@test.com")
    svc = PackageInstallService()
    assert svc.install_uploaded_archive(
        filename="pkg.zip", data=_manifest_zip(), user_id=owner_id
    ).success
    pkg_dir = packages_dir / "addons" / "uploaded-addon"
    assert pkg_dir.is_dir()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner_id)
        resp = client.post(
            "/sdk/packages/remove",
            data={"package_id": "uploaded-addon"},
            follow_redirects=False,
        )

    assert resp.status_code in (301, 302, 303, 307, 308)
    assert not pkg_dir.exists()


def test_upload_route_json_prompts_replace_on_conflict(db, packages_dir):
    from litestar.testing import TestClient

    from main import app

    owner_id = seed_user(name="Owner", email="owner-upload-json@test.com")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner_id)
        headers = {"accept": "application/json"}

        first = client.post(
            "/sdk/packages/upload",
            files={"package_file": ("pkg.zip", _manifest_zip(), "application/zip")},
            data={"expected_group": "addon"},
            headers=headers,
        )
        assert first.status_code == 200
        assert first.json()["ok"] is True

        # Same id again -> not an error banner, but a replace prompt signal.
        conflict = client.post(
            "/sdk/packages/upload",
            files={"package_file": ("pkg.zip", _manifest_zip(version="1.1.0"), "application/zip")},
            data={"expected_group": "addon"},
            headers=headers,
        )
        body = conflict.json()
        assert body["ok"] is False and body["conflict"] is True

        # Confirming the prompt re-sends with replace=true and succeeds.
        replaced = client.post(
            "/sdk/packages/upload",
            files={"package_file": ("pkg.zip", _manifest_zip(version="1.1.0"), "application/zip")},
            data={"expected_group": "addon", "replace": "true"},
            headers=headers,
        )
        assert replaced.json()["ok"] is True
