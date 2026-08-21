"""Validated TOML registry for Gravewright Core and package channels."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.engine.sdk.package_manifest import PackageKind

MARKETPLACE_VERSION = 2
SUPPORTED_MARKETPLACE_VERSIONS = frozenset({1, 2})
CHANNELS = frozenset({"stable", "testing", "dev"})
LEGACY_CHANNELS = {"stable": "stable", "beta": "testing", "experimental": "dev"}
UPDATE_POLICIES = frozenset({"publisher", "curated"})
SOURCES = frozenset({"core", "community", "partner"})
ACCESS_MODES = frozenset({"public", "entitled"})
KINDS = frozenset(PackageKind.values())
OFFICIAL_CORE_REPOSITORY = "https://github.com/Gravewright/gravewright"
OFFICIAL_CORE_RELEASES = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"


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
    source: str = "community"
    bundled: bool = False
    approved_tree_sha256: str = ""
    channels: dict[str, "MarketplaceRelease"] | None = None
    access: str = "public"
    publisher: str = ""
    license_model: str = ""
    auth_provider: str = ""

    def release_for(self, preferred_channel: str) -> tuple[str, "MarketplaceRelease"] | None:
        releases = self.channels or {}
        order = {
            "stable": ("stable",),
            "testing": ("testing", "stable"),
            "dev": ("dev", "testing", "stable"),
        }.get(preferred_channel, ("stable",))
        return next(((name, releases[name]) for name in order if name in releases), None)


@dataclass(frozen=True)
class MarketplaceRelease:
    manifest: str
    approved_version: str = ""
    approved_sha256: str = ""


@dataclass(frozen=True)
class CoreMarketplaceEntry:
    id: str
    name: str
    enabled: bool
    repository: str
    releases: str
    channels: frozenset[str]

    def release_channel_for(self, preferred_channel: str) -> str | None:
        order = {
            "stable": ("stable",),
            "testing": ("testing", "stable"),
            "dev": ("dev", "testing", "stable"),
        }.get(preferred_channel, ("stable",))
        return next((name for name in order if name in self.channels), None)


@dataclass(frozen=True)
class MarketplaceDocument:
    version: int
    core: CoreMarketplaceEntry | None
    packages: tuple[MarketplaceEntry, ...]


def _text(raw: dict, key: str, *, required: bool = False) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str) or (required and not value.strip()):
        raise MarketplaceRegistryError(f"MARKETPLACE_INVALID_{key.upper()}")
    return value.strip()


def _http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username


def parse_marketplace_document(data: bytes | str) -> MarketplaceDocument:
    try:
        document = tomllib.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
    except (tomllib.TOMLDecodeError, UnicodeError) as exc:
        raise MarketplaceRegistryError("MARKETPLACE_TOML_INVALID") from exc
    document_version = document.get("version")
    if document_version not in SUPPORTED_MARKETPLACE_VERSIONS:
        raise MarketplaceRegistryError("MARKETPLACE_VERSION_UNSUPPORTED")
    core_entry = _parse_core(document.get("core"), document_version)
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
        manifest = _text(raw, "manifest")
        enabled = raw.get("enabled", True)
        featured = raw.get("featured", False)
        if not isinstance(enabled, bool) or not isinstance(featured, bool):
            raise MarketplaceRegistryError("MARKETPLACE_ENTRY_INVALID")
        channel = LEGACY_CHANNELS.get(_text(raw, "channel") or "stable", "")
        channels: dict[str, MarketplaceRelease] = {}
        if document_version == 1:
            if not channel:
                raise MarketplaceRegistryError("MARKETPLACE_CHANNEL_INVALID")
            if not _http_url(manifest):
                raise MarketplaceRegistryError("MARKETPLACE_MANIFEST_URL_INVALID")
        else:
            channel_data = raw.get("channels")
            if not isinstance(channel_data, dict) or not channel_data:
                raise MarketplaceRegistryError("MARKETPLACE_CHANNELS_REQUIRED")
            unknown = set(channel_data) - CHANNELS
            if unknown:
                raise MarketplaceRegistryError("MARKETPLACE_CHANNEL_INVALID")
            for channel_name, release_raw in channel_data.items():
                if not isinstance(release_raw, dict):
                    raise MarketplaceRegistryError("MARKETPLACE_CHANNEL_INVALID")
                release_manifest = _text(release_raw, "manifest", required=True)
                if not _http_url(release_manifest):
                    raise MarketplaceRegistryError("MARKETPLACE_MANIFEST_URL_INVALID")
                release_version = _text(release_raw, "approved_version")
                release_sha = _text(release_raw, "approved_sha256")
                if release_sha and (len(release_sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in release_sha)):
                    raise MarketplaceRegistryError("MARKETPLACE_APPROVED_SHA256_INVALID")
                channels[channel_name] = MarketplaceRelease(
                    manifest=release_manifest,
                    approved_version=release_version,
                    approved_sha256=release_sha.lower(),
                )
            channel = "stable" if "stable" in channels else next(iter(channels))
            manifest = channels[channel].manifest
        update_policy = _text(raw, "update_policy") or "publisher"
        if update_policy not in UPDATE_POLICIES:
            raise MarketplaceRegistryError("MARKETPLACE_UPDATE_POLICY_INVALID")
        approved_version = _text(raw, "approved_version")
        approved_sha256 = _text(raw, "approved_sha256")
        source = _text(raw, "source") or "community"
        if source not in SOURCES:
            raise MarketplaceRegistryError("MARKETPLACE_SOURCE_INVALID")
        access = _text(raw, "access") or "public"
        if access not in ACCESS_MODES:
            raise MarketplaceRegistryError("MARKETPLACE_ACCESS_INVALID")
        auth_provider = _text(raw, "auth_provider")
        if access == "entitled" and not auth_provider:
            raise MarketplaceRegistryError("MARKETPLACE_AUTH_PROVIDER_REQUIRED")
        bundled = raw.get("bundled", False)
        if not isinstance(bundled, bool):
            raise MarketplaceRegistryError("MARKETPLACE_BUNDLED_INVALID")
        approved_tree_sha256 = _text(raw, "approved_tree_sha256")
        if update_policy == "curated" and not approved_version:
            if document_version == 1:
                raise MarketplaceRegistryError("MARKETPLACE_APPROVED_VERSION_REQUIRED")
            if any(not release.approved_version for release in channels.values()):
                raise MarketplaceRegistryError("MARKETPLACE_APPROVED_VERSION_REQUIRED")
        if approved_sha256 and (len(approved_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in approved_sha256)):
            raise MarketplaceRegistryError("MARKETPLACE_APPROVED_SHA256_INVALID")
        if approved_tree_sha256 and (len(approved_tree_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in approved_tree_sha256)):
            raise MarketplaceRegistryError("MARKETPLACE_APPROVED_TREE_SHA256_INVALID")
        if bundled and (source != "core" or not approved_tree_sha256):
            raise MarketplaceRegistryError("MARKETPLACE_BUNDLED_PROVENANCE_INVALID")
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
            source=source, bundled=bundled,
            approved_tree_sha256=approved_tree_sha256.lower(),
            channels=channels or {
                channel: MarketplaceRelease(
                    manifest=manifest,
                    approved_version=approved_version,
                    approved_sha256=approved_sha256.lower(),
                )
            },
            access=access,
            publisher=_text(raw, "publisher"),
            license_model=_text(raw, "license_model"),
            auth_provider=auth_provider,
        ))
    return MarketplaceDocument(version=document_version, core=core_entry, packages=tuple(entries))


def _parse_core(raw: object, document_version: int) -> CoreMarketplaceEntry | None:
    if raw is None:
        return None
    if document_version != 2 or not isinstance(raw, dict):
        raise MarketplaceRegistryError("MARKETPLACE_CORE_INVALID")
    if _text(raw, "id", required=True) != "gravewright":
        raise MarketplaceRegistryError("MARKETPLACE_CORE_ID_INVALID")
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise MarketplaceRegistryError("MARKETPLACE_CORE_INVALID")
    repository = _text(raw, "repository", required=True)
    releases = _text(raw, "releases", required=True)
    if repository != OFFICIAL_CORE_REPOSITORY or releases != OFFICIAL_CORE_RELEASES:
        raise MarketplaceRegistryError("MARKETPLACE_CORE_AUTHORITY_INVALID")
    channel_data = raw.get("channels")
    if not isinstance(channel_data, dict) or not channel_data:
        raise MarketplaceRegistryError("MARKETPLACE_CORE_CHANNELS_REQUIRED")
    if set(channel_data) - CHANNELS:
        raise MarketplaceRegistryError("MARKETPLACE_CHANNEL_INVALID")
    for value in channel_data.values():
        if not isinstance(value, dict) or value.get("enabled", True) is not True:
            raise MarketplaceRegistryError("MARKETPLACE_CORE_CHANNEL_INVALID")
        if set(value) - {"enabled"}:
            raise MarketplaceRegistryError("MARKETPLACE_CORE_CHANNEL_INVALID")
    return CoreMarketplaceEntry(
        id="gravewright", name=_text(raw, "name") or "Gravewright", enabled=enabled,
        repository=repository, releases=releases, channels=frozenset(channel_data),
    )


def parse_marketplace_toml(data: bytes | str) -> tuple[MarketplaceEntry, ...]:
    """Compatibility wrapper returning only package listings."""
    return parse_marketplace_document(data).packages


def load_marketplace(path: Path) -> tuple[MarketplaceEntry, ...]:
    try:
        return parse_marketplace_toml(path.read_bytes())
    except OSError as exc:
        raise MarketplaceRegistryError("MARKETPLACE_REGISTRY_UNAVAILABLE") from exc


def load_marketplace_document(path: Path) -> MarketplaceDocument:
    try:
        return parse_marketplace_document(path.read_bytes())
    except OSError as exc:
        raise MarketplaceRegistryError("MARKETPLACE_REGISTRY_UNAVAILABLE") from exc
