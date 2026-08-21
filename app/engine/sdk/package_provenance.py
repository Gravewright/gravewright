"""Declared versus registry-certified package distribution provenance."""

from __future__ import annotations

import hmac

from app.engine.sdk.marketplace_registry import MarketplaceEntry, load_marketplace
from app.engine.sdk.marketplace_service import DEFAULT_REGISTRY
from app.engine.sdk.package_integrity import compute_package_tree_hash
from app.engine.sdk.package_manifest import PackageManifest

DEFAULT_SOURCE = "community"
PRIVILEGED_SOURCES = {"core", "partner"}


def declared_source(manifest: PackageManifest | None) -> str:
    value = manifest.distribution.source if manifest and manifest.distribution else ""
    return value if value in {"core", "community", "partner"} else ""


def certified_listing(package_id: str, *, registry_path=DEFAULT_REGISTRY) -> MarketplaceEntry | None:
    try:
        return next((entry for entry in load_marketplace(registry_path)
                     if entry.enabled and entry.id == package_id), None)
    except Exception:
        return None


def resolve_installed_provenance(*, manifest: PackageManifest | None, record: dict | None,
                                 package_dir=None, registry_path=DEFAULT_REGISTRY) -> dict:
    declared = declared_source(manifest)
    listing = certified_listing(manifest.id if manifest else "", registry_path=registry_path)
    certified = False
    certified_source = ""
    authority = "manual"
    if manifest and record and listing and listing.kind == manifest.kind:
        identity_matches = str(record.get("version") or "") == manifest.version
        if listing.bundled and package_dir is not None and identity_matches:
            actual = compute_package_tree_hash(package_dir)
            certified = hmac.compare_digest(actual, listing.approved_tree_sha256)
            authority = "gravewright-bundle" if certified else "manual"
        elif identity_matches and record.get("package_sha256"):
            try:
                from app.engine.sdk.marketplace_service import MarketplaceService
                catalog = MarketplaceService(registry_path=registry_path).catalog()
                item = next((value for value in catalog.get("packages", [])
                             if value.get("id") == manifest.id), None)
                expected = str((item or {}).get("artifact", {}).get("sha256") or "")
                certified = bool(expected and hmac.compare_digest(
                    str(record.get("package_sha256")).lower(), expected.lower()))
                authority = "marketplace" if certified else "manual"
            except Exception:
                certified = False
        if certified:
            certified_source = listing.source
    effective = certified_source if certified else DEFAULT_SOURCE
    mismatch = bool(declared and declared != effective)
    return {"declaredSource": declared, "effectiveSource": effective,
            "certifiedSource": certified_source, "certified": certified,
            "authority": authority, "mismatch": mismatch}
