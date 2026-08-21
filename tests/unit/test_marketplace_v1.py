from __future__ import annotations

import hashlib
import io
import json
import zipfile
import stat
import warnings
from pathlib import Path

import pytest

from app.engine.sdk import package_archive_installer, package_registry
from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.marketplace_installer import MarketplaceInstaller
from app.engine.sdk.marketplace_registry import (
    MarketplaceRegistryError, parse_marketplace_document, parse_marketplace_toml,
)
from app.engine.sdk.marketplace_service import MarketplaceService, _safe_remote_url
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_integrity import compute_package_tree_hash
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_provenance import resolve_installed_provenance


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
    assert entries[0].source == "community"


def test_marketplace_v2_resolves_channels_with_safe_fallback() -> None:
    document = '''version = 2
[[packages]]
id = "channel-addon"
name = "Channel Addon"
kind = "addon"
source = "community"
[packages.channels.stable]
manifest = "https://packages.test/stable.json"
[packages.channels.dev]
manifest = "https://packages.test/dev.json"
'''
    entry = parse_marketplace_toml(document)[0]
    assert entry.release_for("stable")[0] == "stable"
    assert entry.release_for("testing")[0] == "stable"
    assert entry.release_for("dev")[0] == "dev"


def test_marketplace_v2_carries_official_core_channels() -> None:
    document = '''version = 2
[core]
id = "gravewright"
name = "Gravewright"
enabled = true
repository = "https://github.com/Gravewright/gravewright"
releases = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"
[core.channels.dev]
enabled = true
[[packages]]
id = "dev-addon"
kind = "addon"
[packages.channels.dev]
manifest = "https://packages.test/dev.json"
'''
    registry = parse_marketplace_document(document)
    assert registry.core is not None
    assert registry.core.release_channel_for("stable") is None
    assert registry.core.release_channel_for("dev") == "dev"
    assert registry.packages[0].release_for("stable") is None


def test_stable_never_resolves_testing_or_dev() -> None:
    document = '''version = 2
[[packages]]
id = "preview-only"
kind = "addon"
[packages.channels.testing]
manifest = "https://packages.test/testing.json"
[packages.channels.dev]
manifest = "https://packages.test/dev.json"
'''
    entry = parse_marketplace_toml(document)[0]
    assert entry.release_for("stable") is None
    assert entry.release_for("testing")[0] == "testing"


def test_entitled_publisher_listing_is_visible_but_fails_closed_for_install(tmp_path: Path, db) -> None:
    document = '''version = 2
[[packages]]
id = "licensed-addon"
kind = "addon"
source = "partner"
access = "entitled"
publisher = "Publisher"
license_model = "commercial"
auth_provider = "publisher-account"
[packages.channels.stable]
manifest = "https://packages.test/manifest.json"
'''
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, document)
    remote = manifest(package_id="licensed-addon")
    remote["distribution"]["source"] = "partner"
    service = MarketplaceService(registry_path=path, cache_path=cache, channel="stable",
        fetcher=lambda *_: json.dumps(remote).encode())
    service.refresh()
    item = service.catalog()["packages"][0]
    assert item["installState"] == "license-required"
    assert item["publisherName"] == "Publisher"
    assert service.get_valid("licensed-addon") is None


def test_remote_registry_is_cached_only_after_valid_parse(tmp_path: Path, db) -> None:
    cache = tmp_path / "catalog.json"
    service = MarketplaceService(registry_path=None, registry_url="https://registry.test/marketplace.toml",
        cache_path=cache, channel="testing",
        fetcher=lambda url, _limit: (
            b'''version = 2
[[packages]]
id = "curated-addon"
kind = "addon"
[packages.channels.stable]
manifest = "https://packages.test/manifest.json"
''' if "registry.test" in url else json.dumps(manifest()).encode()
        ))
    service.registry_cache_path = tmp_path / "marketplace.toml"
    result = service.refresh()
    assert result["refreshStatus"] == "ok"
    assert result["selectedChannel"] == "testing"
    assert result["packages"][0]["channel"] == "stable"
    assert service.registry_cache_path.read_text(encoding="utf-8").startswith("version = 2")

    previous_registry = service.registry_cache_path.read_bytes()
    service.fetcher = lambda *_: b"invalid = ["
    failed = service.refresh()
    assert failed["refreshStatus"] == "failed"
    assert service.registry_cache_path.read_bytes() == previous_registry


def test_privileged_source_requires_matching_manifest_declaration(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path, registry() + 'source = "partner"\n')
    result = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest()).encode()).refresh()
    assert result["packages"][0]["validationError"] == "MARKETPLACE_PROVENANCE_MISMATCH"


def test_community_registry_never_promotes_self_declared_core(tmp_path: Path, db) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    raw = manifest()
    raw["distribution"]["source"] = "core"
    item = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(raw).encode()).refresh()["packages"][0]
    assert item["validationState"] == "valid"
    assert item["declaredSource"] == "core"
    assert item["effectiveSource"] == "community"
    assert item["provenanceMismatch"] is True


def test_manual_package_cannot_self_certify_privileged_source(tmp_path: Path) -> None:
    path = tmp_path / "marketplace.toml"
    write_registry(path, "version = 1\n")
    raw = manifest()
    raw["distribution"]["source"] = "core"
    result = resolve_installed_provenance(
        manifest=PackageManifest.from_dict(raw), record={"version": "1.0.0"},
        package_dir=tmp_path, registry_path=path,
    )
    assert result == {"declaredSource": "core", "effectiveSource": "community",
                      "certifiedSource": "", "certified": False,
                      "authority": "manual", "mismatch": True}


def test_bundled_core_requires_registry_tree_hash(tmp_path: Path, monkeypatch, db) -> None:
    packages = tmp_path / "packages"
    package_dir = packages / "content" / "core-pack"
    package_dir.mkdir(parents=True)
    raw = manifest(package_id="core-pack", kind="content")
    raw["distribution"] = {"source": "core"}
    (package_dir / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")
    digest = compute_package_tree_hash(package_dir)
    registry_path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(registry_path, f'''version = 1
[[packages]]
id = "core-pack"
kind = "content"
manifest = "https://packages.test/core.json"
source = "core"
bundled = true
approved_tree_sha256 = "{digest}"
''')
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages)
    item = MarketplaceService(registry_path=registry_path, cache_path=cache,
        fetcher=lambda *_: pytest.fail("bundled packages are local")).refresh()["packages"][0]
    assert item["validationState"] == "valid"
    assert item["effectiveSource"] == "core"
    assert item["sourceCertified"] is True


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


@pytest.mark.parametrize("checksum", ["", "abc", "g" * 64])
def test_missing_or_malformed_checksum_is_unavailable(tmp_path, db, checksum) -> None:
    path, cache = tmp_path / "marketplace.toml", tmp_path / "cache.json"
    write_registry(path)
    item = MarketplaceService(registry_path=path, cache_path=cache,
        fetcher=lambda *_: json.dumps(manifest(sha256=checksum)).encode()).refresh()["packages"][0]
    assert item["validationState"] == "unavailable"
    assert item["validationError"] == "MARKETPLACE_ARTIFACT_INVALID"


def test_uppercase_checksum_authenticates_downloaded_bytes(marketplace_install_env) -> None:
    _packages, path, cache = marketplace_install_env
    data = archive(manifest())
    service = prepared_marketplace(path, cache, data, manifest(
        sha256=hashlib.sha256(data).hexdigest().upper()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(
        package_id="curated-addon", user_id=None).success


def test_staged_dependency_incompatibility_is_rejected(marketplace_install_env) -> None:
    packages, path, cache = marketplace_install_env
    remote_manifest = manifest()
    remote_manifest["dependencies"] = [{"id": "missing-library", "kind": "library", "minimum": "1.0.0"}]
    data = archive(remote_manifest)
    metadata = dict(remote_manifest)
    metadata["distribution"] = {"type": "zip", "url": "https://packages.test/addon.zip",
                                "sha256": hashlib.sha256(data).hexdigest()}
    service = prepared_marketplace(path, cache, data, metadata)
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: data).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "sdk.errors.dependency_missing"
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


def test_update_refuses_to_replace_enabled_package(marketplace_install_env) -> None:
    _packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(
        package_id="curated-addon", user_id=None).success
    assert PackageInstallService().enable(package_id="curated-addon").success
    second = archive(manifest(version="2.0.0"))
    service = prepared_marketplace(path, cache, second, manifest(
        version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: second).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_UPDATE_DISABLE_FIRST"
    assert PackageInstallService().get("curated-addon")["version"] == "1.0.0"


def test_update_refuses_package_active_in_campaign(marketplace_install_env, monkeypatch) -> None:
    _packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(
        package_id="curated-addon", user_id=None).success
    monkeypatch.setattr(PackageInstallService, "active_campaign_ids", lambda *_: ["campaign"])
    second = archive(manifest(version="2.0.0"))
    service = prepared_marketplace(path, cache, second, manifest(
        version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: second).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_UPDATE_ACTIVE_IN_CAMPAIGN"


@pytest.mark.parametrize("remote_version", ["1.0.0", "0.9.9"])
def test_update_rejects_same_version_and_downgrade(marketplace_install_env, remote_version) -> None:
    _packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(
        package_id="curated-addon", user_id=None).success
    candidate = archive(manifest(version=remote_version))
    service = prepared_marketplace(path, cache, candidate, manifest(
        version=remote_version, sha256=hashlib.sha256(candidate).hexdigest()))
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: candidate).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_UPDATE_NOT_NEWER"


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


@pytest.mark.parametrize("name", [
    "../escape.txt", "/absolute.txt", "C:/windows.txt", "//server/share.txt",
    "trailing-space ", "trailing-dot.", "folder/file. ",
])
def test_hostile_member_paths_are_rejected(marketplace_install_env, name: str) -> None:
    packages, _path, _cache = marketplace_install_env
    data = archive(manifest(), {name: b"hostile"})
    result = package_archive_installer.stage_archive(filename="hostile.zip", data=data)
    assert not result.success and result.error_key == package_archive_installer.ERROR_UNSAFE
    assert not (packages.parent / "escape.txt").exists()


def test_raw_zip_backslash_path_is_rejected(marketplace_install_env) -> None:
    data = archive(manifest(), {"folder/escape.txt": b"hostile"})
    data = data.replace(b"folder/escape.txt", b"folder\\escape.txt")
    result = package_archive_installer.stage_archive(filename="backslash.zip", data=data)
    assert not result.success and result.error_key == package_archive_installer.ERROR_UNSAFE


@pytest.mark.parametrize("mode", [stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o600, stat.S_IFCHR | 0o600])
def test_special_zip_member_types_are_rejected(marketplace_install_env, mode: int) -> None:
    info = zipfile.ZipInfo("special-entry")
    info.create_system = 3
    info.external_attr = mode << 16
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        package.writestr("manifest.json", json.dumps(manifest()))
        package.writestr(info, b"target")
    result = package_archive_installer.stage_archive(filename="special.zip", data=output.getvalue())
    assert not result.success and result.error_key == package_archive_installer.ERROR_UNSAFE


@pytest.mark.parametrize("names", [
    ("duplicate.txt", "duplicate.txt"),
    ("Case.txt", "case.txt"),
    ("Manifest.json", "manifest.json"),
])
def test_duplicate_and_windows_case_collisions_are_rejected(marketplace_install_env, names) -> None:
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as package:
            package.writestr("manifest.json", json.dumps(manifest()))
            package.writestr(names[0], b"first")
            package.writestr(names[1], b"second")
    result = package_archive_installer.stage_archive(filename="collision.zip", data=output.getvalue())
    assert not result.success and result.error_key == package_archive_installer.ERROR_UNSAFE


def test_zip_compression_bomb_ratio_is_rejected(marketplace_install_env) -> None:
    data = archive(manifest(), {"huge.txt": b"0" * (2 * 1024 * 1024)})
    result = package_archive_installer.stage_archive(filename="bomb.zip", data=data)
    assert not result.success and result.error_key == package_archive_installer.ERROR_TOO_LARGE


def test_zip_entry_budget_is_rejected(marketplace_install_env, monkeypatch) -> None:
    monkeypatch.setattr(package_archive_installer, "MAX_ZIP_ENTRIES", 1)
    data = archive(manifest(), {"second.txt": b"x"})
    result = package_archive_installer.stage_archive(filename="many.zip", data=data)
    assert not result.success and result.error_key == package_archive_installer.ERROR_TOO_LARGE


def test_publication_failure_restores_old_package(marketplace_install_env, monkeypatch) -> None:
    packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(
        package_id="curated-addon", user_id=None).success
    second = archive(manifest(version="2.0.0"))
    service = prepared_marketplace(path, cache, second, manifest(version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    real_move = __import__("app.engine.sdk.marketplace_installer", fromlist=["shutil"]).shutil.move
    calls = 0
    def fail_publish(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("publish failed")
        return real_move(src, dst)
    monkeypatch.setattr("app.engine.sdk.marketplace_installer.shutil.move", fail_publish)
    result = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: second).install(
        package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_INSTALL_FAILED"
    disk = json.loads((packages / "addons" / "curated-addon" / "manifest.json").read_text())
    assert disk["version"] == "1.0.0"


def test_rollback_failure_preserves_recovery_artifacts(marketplace_install_env, monkeypatch) -> None:
    packages, path, cache = marketplace_install_env
    first = archive(manifest())
    service = prepared_marketplace(path, cache, first, manifest(sha256=hashlib.sha256(first).hexdigest()))
    assert MarketplaceInstaller(marketplace=service, fetcher=lambda *_: first).install(
        package_id="curated-addon", user_id=None).success
    second = archive(manifest(version="2.0.0"))
    service = prepared_marketplace(path, cache, second, manifest(version="2.0.0", sha256=hashlib.sha256(second).hexdigest()))
    installer = MarketplaceInstaller(marketplace=service, fetcher=lambda *_: second)
    class FailingRepository:
        def get(self, package_id): return PackageInstallService().get(package_id)
        def upsert(self, **_kwargs): raise RuntimeError("persist failed")
    installer.installed = FailingRepository()
    real_move = __import__("app.engine.sdk.marketplace_installer", fromlist=["shutil"]).shutil.move
    def fail_restore(src, dst):
        if ".marketplace-backup-" in str(src) and str(dst).endswith("curated-addon"):
            raise OSError("rollback failed")
        return real_move(src, dst)
    monkeypatch.setattr("app.engine.sdk.marketplace_installer.shutil.move", fail_restore)
    result = installer.install(package_id="curated-addon", user_id=None)
    assert result.error_key == "PACKAGE_ROLLBACK_FAILED"
    assert result.recovery_paths
    assert all(Path(value).exists() for value in result.recovery_paths)
    assert PackageInstallService().get("curated-addon")["version"] == "1.0.0"
    assert any(finding.code == "sdk.update.recovery_required"
               for finding in PackageDoctorService().audit())
