"""Validated TOML registry for the curated Marketplace v1 catalog."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.engine.sdk.package_manifest import PackageKind

MARKETPLACE_VERSION = 1
CHANNELS = frozenset({"stable", "beta", "experimental"})
UPDATE_POLICIES = frozenset({"publisher", "curated"})
KINDS = frozenset(PackageKind.values())


class MarketplaceRegistryError(ValueError):
    """The curated registry is structurally invalid and must fail closed."""


@dataclass(frozen=True)
class MarketplaceEntry:
    id: str
    name: str
    kind: str
    manifest: str
    enabled: bool
    channel: str
    category: str = ""
    tags: tuple[str, ...] = ()
    featured: bool = False
    reviewed_at: str = ""
    update_policy: str = "publisher"
    approved_version: str = ""
    approved_sha256: str = ""


def _text(raw: dict, key: str, *, required: bool = False) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str) or (required and not value.strip()):
        raise MarketplaceRegistryError(f"MARKETPLACE_INVALID_{key.upper()}")
    return value.strip()


def _http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username


def parse_marketplace_toml(data: bytes | str) -> tuple[MarketplaceEntry, ...]:
    try:
        document = tomllib.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
    except (tomllib.TOMLDecodeError, UnicodeError) as exc:
        raise MarketplaceRegistryError("MARKETPLACE_TOML_INVALID") from exc
    if document.get("version") != MARKETPLACE_VERSION:
        raise MarketplaceRegistryError("MARKETPLACE_VERSION_UNSUPPORTED")
    packages = document.get("packages")
    if not isinstance(packages, list):
        raise MarketplaceRegistryError("MARKETPLACE_PACKAGES_INVALID")

    entries: list[MarketplaceEntry] = []
    seen: set[str] = set()
    for raw in packages:
        if not isinstance(raw, dict):
            raise MarketplaceRegistryError("MARKETPLACE_ENTRY_INVALID")
        package_id = _text(raw, "id", required=True)
        if package_id in seen:
            raise MarketplaceRegistryError("MARKETPLACE_DUPLICATE_ID")
        seen.add(package_id)
        kind = _text(raw, "kind", required=True)
        if kind not in KINDS:
            raise MarketplaceRegistryError("MARKETPLACE_KIND_INVALID")
        manifest = _text(raw, "manifest", required=True)
        if not _http_url(manifest):
            raise MarketplaceRegistryError("MARKETPLACE_MANIFEST_URL_INVALID")
        enabled = raw.get("enabled", True)
        featured = raw.get("featured", False)
        if not isinstance(enabled, bool) or not isinstance(featured, bool):
            raise MarketplaceRegistryError("MARKETPLACE_ENTRY_INVALID")
        channel = _text(raw, "channel") or "stable"
        if channel not in CHANNELS:
            raise MarketplaceRegistryError("MARKETPLACE_CHANNEL_INVALID")
        update_policy = _text(raw, "update_policy") or "publisher"
        if update_policy not in UPDATE_POLICIES:
            raise MarketplaceRegistryError("MARKETPLACE_UPDATE_POLICY_INVALID")
        approved_version = _text(raw, "approved_version")
        approved_sha256 = _text(raw, "approved_sha256")
        if update_policy == "curated" and not approved_version:
            raise MarketplaceRegistryError("MARKETPLACE_APPROVED_VERSION_REQUIRED")
        if approved_sha256 and (len(approved_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in approved_sha256)):
            raise MarketplaceRegistryError("MARKETPLACE_APPROVED_SHA256_INVALID")
        tags = raw.get("tags", [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise MarketplaceRegistryError("MARKETPLACE_TAGS_INVALID")
        entries.append(MarketplaceEntry(
            id=package_id,
            name=_text(raw, "name") or package_id,
            kind=kind,
            manifest=manifest,
            enabled=enabled,
            channel=channel,
            category=_text(raw, "category"),
            tags=tuple(tag.strip() for tag in tags if tag.strip()),
            featured=featured,
            reviewed_at=_text(raw, "reviewed_at"),
            update_policy=update_policy,
            approved_version=approved_version,
            approved_sha256=approved_sha256.lower(),
        ))
    return tuple(entries)


def load_marketplace(path: Path) -> tuple[MarketplaceEntry, ...]:
    try:
        return parse_marketplace_toml(path.read_bytes())
    except OSError as exc:
        raise MarketplaceRegistryError("MARKETPLACE_REGISTRY_UNAVAILABLE") from exc
