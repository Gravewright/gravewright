from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.engine.sdk import package_archive_installer, package_registry
from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.marketplace_installer import MarketplaceInstaller
from app.engine.sdk.marketplace_registry import MarketplaceRegistryError, parse_marketplace_toml
from app.engine.sdk.marketplace_service import MarketplaceService, _safe_remote_url
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_install_service import PackageInstallService


def archive(manifest: dict, extra: dict[str, bytes] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("manifest.json", json.dumps(manifest))
        for name, content in (extra or {}).items():
            package.writestr(name, content)
    return output.getvalue()


def manifest(*, package_id: str = "curated-addon", kind: str = "addon", version: str = "1.0.0",
             sdk_version: str = "1", artifact_url: str = "https://packages.test/addon.zip",
             sha256: str = "0" * 64, top_level_distribution: bool = False) -> dict:
    value = {
        "schemaVersion": 1, "sdkVersion": sdk_version, "id": package_id, "kind": kind,
        "name": "Curated Addon", "description": "A useful package", "authors": ["Publisher"],
        "version": version, "compatibility": {"minimum": "1", "verified": "1", "maximum": "1.x"},
        "capabilities": [], "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {}, "provides": {},
    }
    if top_level_distribution:
        value.update({"download": artifact_url, "sha256": sha256})
    else:
        value["distribution"] = {"type": "zip", "url": artifact_url, "sha256": sha256}
    return value


def registry(*, package_id: str = "curated-addon", kind: str = "addon", enabled: bool = True) -> str:
    return f'''version = 1
[[packages]]
id = "{package_id}"
name = "Curated Addon"
kind = "{kind}"
manifest = "https://packages.test/manifest.json"
enabled = {str(enabled).lower()}
channel = "stable"
tags = ["tools", "community"]
'''


def curated_registry(*, approved_version: str, approved_sha256: str = "") -> str:
    checksum = f'approved_sha256 = "{approved_sha256}"\n' if approved_sha256 else ""
    return registry() + f'update_policy = "curated"\napproved_version = "{approved_version}"\n{checksum}'


def write_registry(path: Path, value: str | None = None) -> None:
    path.write_text(value or registry(), encoding="utf-8", newline="\n")


def test_registry_parses_valid_toml_and_canonical_kind() -> None:
    entries = parse_marketplace_toml(registry())
    assert len(entries) == 1 and entries[0].kind == "addon" and entries[0].channel == "stable"


def test_catalog_refreshes_automatically_before_its_first_render(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(
        registry_path=path,
        cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode(),
    )

    catalog = service.catalog_with_automatic_refresh()

    assert catalog["refreshStatus"] == "ok"
    assert [item["id"] for item in catalog["packages"]] == ["curated-addon"]


@pytest.mark.parametrize("document, code", [
    ("not toml = [", "MARKETPLACE_TOML_INVALID"),
    (registry() + registry().replace("version = 1\n", "", 1), "MARKETPLACE_DUPLICATE_ID"),
    (registry(kind="plugin"), "MARKETPLACE_KIND_INVALID"),
])
def test_registry_rejects_invalid_documents(document: str, code: str) -> None:
    with pytest.raises(MarketplaceRegistryError, match=code):
        parse_marketplace_toml(document)


def test_disabled_package_is_not_refreshed(tmp_path: Path) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, registry(enabled=False))
    service = MarketplaceService(registry_path=path, cache_path=cache, fetcher=lambda *_: pytest.fail("fetch"))
    assert service.refresh()["packages"] == []


def test_refresh_fetches_manifest_and_builds_cache(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode())
    result = service.refresh()
    assert result["refreshStatus"] == "ok" and result["packages"][0]["validationState"] == "valid"
    assert cache.is_file() and service.catalog()["packages"][0]["installState"] == "install"
    assert "$schema" not in result["packages"][0]["artifact"]


def test_top_level_download_and_sha256_resolve_version(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    remote = manifest(version="0.3.1", top_level_distribution=True, sha256="A" * 64)
    result = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(remote).encode()).refresh()
    item = result["packages"][0]
    assert item["version"] == "0.3.1"
    assert item["artifact"] == {"url": "https://packages.test/addon.zip", "sha256": "A" * 64}


def test_publisher_policy_follows_root_manifest_version(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest(version="2.0.0")).encode())
    assert service.refresh()["packages"][0]["version"] == "2.0.0"


def test_curated_policy_blocks_unapproved_and_accepts_approved(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, curated_registry(approved_version="1.0.0"))
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest(version="2.0.0")).encode())
    blocked = service.refresh()["packages"][0]
    assert blocked["validationError"] == "MARKETPLACE_VERSION_NOT_APPROVED"
    service.fetcher = lambda *_: json.dumps(manifest(version="1.0.0")).encode()
    assert service.refresh()["packages"][0]["validationState"] == "valid"


def test_curated_checksum_approves_exact_bytes(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, curated_registry(approved_version="1.0.0", approved_sha256="a" * 64))
    result = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest(sha256="b" * 64)).encode()).refresh()
    assert result["packages"][0]["validationError"] == "MARKETPLACE_CHECKSUM_NOT_APPROVED"


@pytest.mark.parametrize("url", ["file:///tmp/package.zip", "http://localhost/a", "http://127.0.0.1/a", "http://[::1]/a"])
def test_download_url_policy_rejects_local_and_unsupported_targets(url: str) -> None:
    assert not _safe_remote_url(url)


@pytest.mark.parametrize("remote, error", [
    (manifest(package_id="different"), "MARKETPLACE_MANIFEST_MISMATCH"),
    (manifest(kind="theme"), "MARKETPLACE_MANIFEST_MISMATCH"),
])
def test_refresh_rejects_manifest_identity_mismatch(tmp_path: Path, remote: dict, error: str) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    result = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(remote).encode()).refresh()
    assert result["packages"][0]["validationState"] == "unavailable"
    assert result["packages"][0]["validationError"] == error


def test_sdk_incompatible_is_visible_but_not_installable(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest(sdk_version="2")).encode())
    service.refresh()
    item = service.catalog()["packages"][0]
    assert item["validationState"] == "incompatible" and item["installState"] == "incompatible"


def test_one_bad_manifest_does_not_remove_valid_sibling(tmp_path: Path) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, registry() + registry(package_id="second-addon").replace("version = 1\n", "", 1))
    def fetch(url: str, _limit: int) -> bytes:
        value = manifest(package_id="second-addon") if "second" in url else manifest()
        return json.dumps(value).encode()
    # Give the second entry its own manifest URL so the fixture can distinguish it.
    text = path.read_text(encoding="utf-8")
    marker = text.rfind('manifest = "https://packages.test/manifest.json"')
    path.write_text(text[:marker] + 'manifest = "https://packages.test/second.json"' + text[marker + len('manifest = "https://packages.test/manifest.json"'):], encoding="utf-8")
    result = MarketplaceService(registry_path=path, cache_path=cache, fetcher=fetch).refresh()
    assert len(result["packages"]) == 2


def test_registry_entries_are_the_complete_active_catalog(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    second = registry(package_id="second-ruleset", kind="ruleset").replace("version = 1\n", "", 1)
    addon = registry(package_id="generic-addon", kind="addon").replace("version = 1\n", "", 1)
    write_registry(path, registry() + second + addon)
    def fetch(url: str, _limit: int) -> bytes:
        package_id = "second-ruleset" if "second" in url else "generic-addon" if "generic" in url else "curated-addon"
        kind = "ruleset" if package_id == "second-ruleset" else "addon"
        return json.dumps(manifest(package_id=package_id, kind=kind)).encode()
    text = path.read_text(encoding="utf-8").replace(
        'id = "second-ruleset"\nname = "Curated Addon"',
        'id = "second-ruleset"\nname = "Curated Addon"').replace(
        'id = "second-ruleset"\nname = "Curated Addon"\nkind = "ruleset"\nmanifest = "https://packages.test/manifest.json"',
        'id = "second-ruleset"\nname = "Curated Addon"\nkind = "ruleset"\nmanifest = "https://packages.test/second.json"').replace(
        'id = "generic-addon"\nname = "Curated Addon"\nkind = "addon"\nmanifest = "https://packages.test/manifest.json"',
        'id = "generic-addon"\nname = "Curated Addon"\nkind = "addon"\nmanifest = "https://packages.test/generic.json"')
    path.write_text(text, encoding="utf-8", newline="\n")
    assert len(MarketplaceService(registry_path=path, cache_path=cache, fetcher=fetch).refresh()["packages"]) == 3
    write_registry(path)
    refreshed = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode()).refresh()
    assert [item["id"] for item in refreshed["packages"]] == ["curated-addon"]


def test_removed_marketplace_entry_does_not_uninstall_package(marketplace_install_env) -> None:
    _packages, path, cache = marketplace_install_env
    data = archive(manifest())
    service = prepared_marketplace(path, cache, data, manifest(sha256=hashlib.sha256(data).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(
        package_id="curated-addon", user_id=None).success
    path.write_text("version = 1\npackages = []\n", encoding="utf-8", newline="\n")
    assert MarketplaceService(registry_path=path, cache_path=cache).refresh()["packages"] == []
    assert PackageInstallService().get("curated-addon")["version"] == "1.0.0"


def test_single_root_archive_is_normalized(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    output = io.BytesIO()
    embedded = manifest(top_level_distribution=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("generic-package-1.0.0/manifest.json", json.dumps(embedded))
    data = output.getvalue()
    remote = manifest(top_level_distribution=True, sha256=hashlib.sha256(data).hexdigest())
    service = prepared_marketplace(path, cache, data, remote)
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(
        package_id="curated-addon", user_id=None).success
    assert (packages / "addons" / "curated-addon" / "manifest.json").is_file()


def test_refresh_failure_keeps_last_valid_cache(tmp_path: Path) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode())
    assert service.refresh()["packages"][0]["validationState"] == "valid"
    path.write_text("broken = [", encoding="utf-8")
    fallback = service.refresh()
    assert fallback["refreshStatus"] == "failed" and fallback["packages"][0]["id"] == "curated-addon"


def test_network_failure_keeps_last_valid_cache(tmp_path: Path) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode())
    service.refresh()
    service.fetcher = lambda *_: (_ for _ in ()).throw(OSError("offline"))
    fallback = service.refresh()
    assert fallback["refreshStatus"] == "failed"
    assert fallback["packages"][0]["validationState"] == "valid"


@pytest.fixture
def marketplace_install_env(tmp_path: Path, monkeypatch, db):
    packages = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages)
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    return packages, path, cache


def prepared_marketplace(path: Path, cache: Path, package_bytes: bytes, remote: dict) -> MarketplaceService:
    service = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(remote).encode())
    assert service.refresh()["packages"][0]["validationState"] == "valid"
    return service


def test_checksum_mismatch_never_installs(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    data = archive(manifest())
    service = prepared_marketplace(path, cache, data, manifest(sha256="f" * 64))
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(package_id="curated-addon", user_id=None)
    assert not result.success and result.error_key == "PACKAGE_CHECKSUM_MISMATCH"
    assert not (packages / "addons" / "curated-addon").exists()


def test_path_traversal_archive_is_rejected(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    base = manifest()
    data = archive(base, {"../escape.txt": b"no"})
    service = prepared_marketplace(path, cache, data, manifest(sha256=hashlib.sha256(data).hexdigest()))
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(package_id="curated-addon", user_id=None)
    assert not result.success and result.error_key == package_archive_installer.ERROR_UNSAFE


def test_oversized_archive_is_rejected(marketplace_install_env, monkeypatch) -> None:
    _packages, path, cache = marketplace_install_env
    data = archive(manifest())
    service = prepared_marketplace(path, cache, data, manifest(sha256=hashlib.sha256(data).hexdigest()))
    monkeypatch.setattr(package_archive_installer, "MAX_PACKAGE_BYTES", len(data) - 1)
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(package_id="curated-addon", user_id=None)
    assert not result.success


def test_package_doctor_rejection_prevents_publish(marketplace_install_env, monkeypatch) -> None:
    packages, path, cache = marketplace_install_env
    data = archive(manifest())
    service = prepared_marketplace(path, cache, data, manifest(sha256=hashlib.sha256(data).hexdigest()))
    monkeypatch.setattr(PackageDoctorService, "audit_staged", lambda *_: [DoctorFinding(code="rejected", severity="error")])
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_DOCTOR_REJECTED" and not (packages / "addons" / "curated-addon").exists()


def test_staged_install_and_successful_update(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    first = archive(manifest())
    first_service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=first_service, fetcher=lambda *_: first).install(package_id="curated-addon", user_id=None).success
    assert PackageInstallService().get("curated-addon")["version"] == "1.0.0"

    second = archive(manifest(version="2.0.0"))
    second_service = prepared_marketplace(path, cache, second, manifest(version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    assert second_service.catalog()["packages"][0]["installState"] == "update"
    assert MarketplaceInstaller(marketplace=second_service, fetcher=lambda *_: second).install(package_id="curated-addon", user_id=None).success
    assert PackageInstallService().get("curated-addon")["version"] == "2.0.0"
    disk = json.loads((packages / "addons" / "curated-addon" / "manifest.json").read_text())
    assert disk["version"] == "2.0.0"


def test_failed_update_restores_previous_version(marketplace_install_env, monkeypatch) -> None:
    packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(package_id="curated-addon", user_id=None).success
    second = archive(manifest(version="2.0.0"))
    service = prepared_marketplace(path, cache, second, manifest(version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    installer = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: second)
    class FailingRepository:
        def get(self, package_id):
            return PackageInstallService().get(package_id)
        def upsert(self, **_kwargs):
            raise RuntimeError("database failed")
    installer.installed = FailingRepository()
    result = installer.install(package_id="curated-addon", user_id=None)
    assert not result.success and result.error_key == "PACKAGE_INSTALL_FAILED"
    disk = json.loads((packages / "addons" / "curated-addon" / "manifest.json").read_text())
    assert disk["version"] == "1.0.0"
    assert PackageInstallService().get("curated-addon")["version"] == "1.0.0"


def test_artifact_manifest_must_match_fetched_manifest(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    data = archive(manifest(version="1.0.0"))
    remote = manifest(version="2.0.0", sha256=hashlib.sha256(data).hexdigest())
    service = prepared_marketplace(path, cache, data, remote)
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "MARKETPLACE_ARTIFACT_MANIFEST_MISMATCH"
    assert not (packages / "addons" / "curated-addon").exists()
