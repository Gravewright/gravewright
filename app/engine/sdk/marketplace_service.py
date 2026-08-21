"""Refreshes remote manifests into an atomic, permission-neutral local cache."""

from __future__ import annotations

import json
import ipaddress
import http.client
import os
import socket
import ssl
import time
import uuid
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

from app.config import config
from app.engine.sdk.marketplace_registry import (
    MarketplaceRegistryError, load_marketplace_document, parse_marketplace_document,
)
from app.engine.sdk.package_compatibility import (
    COMPAT_INCOMPATIBLE, update_version_is_valid, version_key,
)
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_manifest import SDK_VERSION
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.engine.sdk.package_integrity import compute_package_tree_hash
from app.engine.sdk.package_loader import load_package
from app.engine.sdk import package_registry
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = PROJECT_ROOT / "marketplace.toml"
DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/Gravewright/gravewright-marketplace/main/marketplace.toml"
DEFAULT_REGISTRY_CACHE = Path(config.data_dir) / "marketplace" / "marketplace.toml"
DEFAULT_CACHE = Path(config.data_dir) / "marketplace" / "cache.json"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_REGISTRY_BYTES = 1024 * 1024
REMOTE_REFRESH_TTL_SECONDS = 60 * 60

Fetch = Callable[[str, int], bytes]


def fetch_bytes(url: str, limit: int) -> bytes:
    current = url
    for _redirect in range(6):
        parsed = urlparse(current)
        if not _safe_remote_url(current):
            raise ValueError("MARKETPLACE_URL_UNSAFE")
        addresses = _resolved_public_addresses(parsed.hostname or "", parsed.port or 443)
        if not addresses:
            raise ValueError("MARKETPLACE_URL_UNSAFE")
        connection = _PinnedHTTPSConnection(parsed.hostname or "", addresses[0], parsed.port or 443, timeout=15)
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            connection.request("GET", path, headers={"Accept": "application/json", "User-Agent": "Gravewright-Marketplace/1"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("MARKETPLACE_REDIRECT_INVALID")
                current = urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise ValueError("MARKETPLACE_HTTP_ERROR")
            length_header = response.getheader("Content-Length")
            if length_header is not None and int(length_header) > limit:
                raise ValueError("MARKETPLACE_RESPONSE_TOO_LARGE")
            chunks, total = [], 0
            while chunk := response.read(min(64 * 1024, limit + 1 - total)):
                total += len(chunk)
                if total > limit:
                    raise ValueError("MARKETPLACE_RESPONSE_TOO_LARGE")
                chunks.append(chunk)
            if length_header is not None and total != int(length_header):
                raise ValueError("MARKETPLACE_RESPONSE_INCOMPLETE")
            return b"".join(chunks)
        finally:
            connection.close()
    raise ValueError("MARKETPLACE_TOO_MANY_REDIRECTS")


class MarketplaceService:
    def __init__(self, *, registry_path: Path | None = None,
                 registry_url: str | None = DEFAULT_REGISTRY_URL,
                 cache_path: Path = DEFAULT_CACHE, fetcher: Fetch = fetch_bytes,
                 channel: str | None = None, core_channel: str | None = None) -> None:
        self.registry_path = registry_path
        self.registry_url = registry_url if registry_path is None else None
        self.registry_cache_path = DEFAULT_REGISTRY_CACHE if registry_path is None else registry_path
        self.cache_path = cache_path
        self.fetcher = fetcher
        if channel is None or core_channel is None:
            from app.business.inside_settings_service import InsideSettingsService
            updates = InsideSettingsService().read()["updates"]
            if channel is None:
                channel = str(updates["packages_channel"])
            if core_channel is None:
                core_channel = str(updates["core_channel"])
        self.channel = channel if channel in {"stable", "testing", "dev"} else "stable"
        self.core_channel = (
            core_channel if core_channel in {"stable", "testing", "dev"} else self.channel
        )
        self.installed = InstalledPackageRepository()

    def read_cache(self) -> dict:
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": 1, "lastRefresh": None, "refreshStatus": "never", "packages": []}
        return value if isinstance(value, dict) else {"version": 1, "lastRefresh": None, "refreshStatus": "never", "packages": []}

    def refresh(self) -> dict:
        previous = self.read_cache()
        try:
            if self.registry_url:
                registry_bytes = self.fetcher(self.registry_url, MAX_REGISTRY_BYTES)
                registry = parse_marketplace_document(registry_bytes)
                self._write_registry_cache(registry_bytes)
            else:
                registry = load_marketplace_document(self.registry_cache_path)
        except MarketplaceRegistryError as exc:
            return {**previous, "refreshStatus": "failed", "refreshError": str(exc)}
        except Exception:
            return {**previous, "refreshStatus": "failed", "refreshError": "MARKETPLACE_REGISTRY_UNAVAILABLE"}

        entries = registry.packages
        packages = []
        network_failures = 0
        enabled_entries = [entry for entry in entries if entry.enabled]
        for entry in entries:
            if not entry.enabled:
                continue
            resolved = entry.release_for(self.channel)
            if resolved is None:
                continue
            resolved_channel, release = resolved
            item = {"id": entry.id, "name": entry.name, "kind": entry.kind, "manifestUrl": release.manifest,
                    "channel": resolved_channel, "selectedChannel": self.channel,
                    "availableChannels": sorted((entry.channels or {}).keys()),
                    "category": entry.category, "tags": list(entry.tags),
                    "featured": entry.featured, "reviewedAt": entry.reviewed_at,
                    "updatePolicy": entry.update_policy, "approvedVersion": release.approved_version,
                    "validationState": "unavailable", "source": entry.source,
                    "effectiveSource": entry.source,
                    "sourceCertified": True, "bundled": entry.bundled,
                    "access": entry.access, "publisherName": entry.publisher,
                    "licenseModel": entry.license_model, "authProvider": entry.auth_provider}
            try:
                if entry.bundled:
                    package_dir = package_registry.package_dir_for(entry.kind, entry.id)
                    if package_dir is None or not package_dir.is_dir():
                        raise ValueError("MARKETPLACE_BUNDLED_PACKAGE_MISSING")
                    loaded = load_package(package_dir, expected_id=entry.id)
                    if loaded.manifest is None:
                        raise ValueError(loaded.errors[0] if loaded.errors else "MARKETPLACE_BUNDLED_MANIFEST_INVALID")
                    raw = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
                else:
                    try:
                        manifest_bytes = self.fetcher(release.manifest, MAX_MANIFEST_BYTES)
                    except Exception as exc:
                        network_failures += 1
                        raise ValueError("MARKETPLACE_MANIFEST_FETCH_FAILED") from exc
                    raw = json.loads(manifest_bytes)
                validation = validate_manifest(raw)
                manifest = PackageManifest.from_dict(raw)
                if not update_version_is_valid(manifest.version):
                    raise ValueError("MARKETPLACE_VERSION_INVALID")
                if manifest.id != entry.id or manifest.kind != entry.kind:
                    raise ValueError("MARKETPLACE_MANIFEST_MISMATCH")
                if manifest.sdk_version != SDK_VERSION:
                    item.update({"name": entry.name or manifest.name, "description": manifest.description,
                                 "publisher": manifest.author_names()[0] if manifest.author_names() else "",
                                 "version": manifest.version, "sdkVersion": manifest.sdk_version,
                                 "compatibility": COMPAT_INCOMPATIBLE, "validationState": "incompatible",
                                 "validationError": "sdk.validation.sdk_version"})
                    packages.append(item)
                    continue
                if not validation.ok:
                    raise ValueError(validation.errors[0])
                distribution = manifest.distribution
                declared_source = distribution.source if distribution else ""
                provenance_mismatch = bool(declared_source and declared_source != entry.source)
                if entry.source in {"core", "partner"} and declared_source != entry.source:
                    raise ValueError("MARKETPLACE_PROVENANCE_MISMATCH")
                if entry.bundled:
                    tree_hash = compute_package_tree_hash(package_dir)
                    if tree_hash.lower() != entry.approved_tree_sha256:
                        raise ValueError("MARKETPLACE_BUNDLED_INTEGRITY_MISMATCH")
                    item.update({
                        "name": entry.name or manifest.name, "description": manifest.description,
                        "publisher": manifest.author_names()[0] if manifest.author_names() else "",
                        "version": manifest.version, "sdkVersion": manifest.sdk_version,
                        "compatibility": validation.compatibility_status, "validationState": "valid",
                        "declaredSource": declared_source, "effectiveSource": entry.source,
                        "provenanceMismatch": provenance_mismatch,
                        "manifestIdentity": {"id": manifest.id, "kind": manifest.kind,
                                             "version": manifest.version, "sdkVersion": manifest.sdk_version,
                                             "source": declared_source},
                    })
                    packages.append(item)
                    continue
                if (distribution is None or distribution.type != "zip" or not _valid_download(distribution.url)
                        or not _valid_sha256(distribution.sha256)):
                    raise ValueError("MARKETPLACE_ARTIFACT_INVALID")
                if entry.update_policy == "curated" and manifest.version != release.approved_version:
                    raise ValueError("MARKETPLACE_VERSION_NOT_APPROVED")
                if release.approved_sha256 and distribution.sha256.lower() != release.approved_sha256:
                    raise ValueError("MARKETPLACE_CHECKSUM_NOT_APPROVED")
                item.update({
                    "name": entry.name or manifest.name, "description": manifest.description,
                    "publisher": manifest.author_names()[0] if manifest.author_names() else "",
                    "version": manifest.version, "sdkVersion": manifest.sdk_version,
                    "compatibility": validation.compatibility_status,
                    "validationState": "incompatible" if validation.compatibility_status == COMPAT_INCOMPATIBLE else "valid",
                    "artifact": {"url": distribution.url, "sha256": distribution.sha256},
                    "declaredSource": declared_source, "effectiveSource": entry.source,
                    "provenanceMismatch": provenance_mismatch,
                    "manifestIdentity": {"id": manifest.id, "kind": manifest.kind,
                                         "version": manifest.version, "sdkVersion": manifest.sdk_version,
                                         "source": declared_source},
                })
            except Exception as exc:  # one bad manifest never destroys valid siblings
                item["validationError"] = str(exc)
            packages.append(item)

        if enabled_entries and network_failures == len(enabled_entries) and previous.get("packages"):
            return {**previous, "refreshStatus": "failed", "refreshError": "MARKETPLACE_REFRESH_FAILED"}
        core = None
        if registry.core is not None:
            resolved_core_channel = registry.core.release_channel_for(self.core_channel)
            core = {
                "id": registry.core.id, "name": registry.core.name,
                "enabled": registry.core.enabled, "repository": registry.core.repository,
                "releases": registry.core.releases,
                "availableChannels": sorted(registry.core.channels),
                "selectedChannel": self.core_channel, "channel": resolved_core_channel,
            }
        available_package_channels = sorted({
            channel_name
            for entry in registry.packages if entry.enabled
            for channel_name in (entry.channels or {})
        })
        result = {"version": 2, "lastRefresh": int(time.time()), "refreshStatus": "ok",
                  "selectedChannel": self.channel, "selectedCoreChannel": self.core_channel,
                  "registryUrl": self.registry_url or "local",
                  "core": core, "availablePackageChannels": available_package_channels,
                  "packages": packages}
        self._write_cache(result)
        return result

    def catalog(self) -> dict:
        cache = self.read_cache()
        channel_stale = cache.get("selectedChannel", "stable") != self.channel
        installed = {row["id"]: row for row in self.installed.list_all()}
        packages = []
        for item in cache.get("packages", []):
            package = dict(item)
            record = installed.get(package.get("id"))
            if channel_stale:
                action = "channel-unavailable"
            elif package.get("validationState") == "incompatible":
                action = "incompatible"
            elif package.get("access") == "entitled":
                action = "license-required"
            elif package.get("validationState") != "valid":
                action = "unavailable"
            elif record is None:
                action = "unavailable" if package.get("bundled") else "install"
            elif package.get("bundled"):
                action = "installed"
            elif version_key(str(package.get("version", ""))) > version_key(str(record.get("version", ""))):
                action = "update"
            elif version_key(str(package.get("version", ""))) < version_key(str(record.get("version", ""))):
                action = "ahead-of-channel"
            else:
                action = "installed"
            package["installState"] = action
            package["channelStale"] = channel_stale
            package["installedVersion"] = str(record.get("version", "")) if record else ""
            packages.append(package)
        return {**cache, "requestedChannel": self.channel, "channelStale": channel_stale,
                "packages": packages}

    def catalog_with_automatic_refresh(self) -> dict:
        """Refresh when the cache is absent or the local registry changed."""
        cache = self.read_cache()
        last_refresh = int(cache.get("lastRefresh") or 0)
        if self.registry_url:
            registry_changed = last_refresh < int(time.time()) - REMOTE_REFRESH_TTL_SECONDS
        else:
            try:
                registry_changed = self.registry_cache_path.stat().st_mtime > last_refresh
            except OSError:
                registry_changed = False
        channel_changed = (cache.get("selectedChannel") != self.channel
                           or cache.get("selectedCoreChannel", self.core_channel) != self.core_channel)
        cache_schema_changed = "availablePackageChannels" not in cache
        if last_refresh == 0 or registry_changed or channel_changed or cache_schema_changed:
            self.refresh()
        return self.catalog()

    def get_valid(self, package_id: str) -> dict | None:
        return next((item for item in self.catalog().get("packages", [])
                     if item.get("id") == package_id and item.get("validationState") == "valid"
                     and item.get("access", "public") == "public"
                     and not item.get("channelStale")), None)

    def _write_cache(self, document: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
        temporary.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
        os.replace(temporary, self.cache_path)

    def _write_registry_cache(self, content: bytes) -> None:
        self.registry_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.registry_cache_path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
        temporary.write_bytes(content)
        os.replace(temporary, self.registry_cache_path)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _valid_download(value: str) -> bool:
    return _safe_remote_url(value)


def _safe_remote_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved
                or address.is_multicast or address.is_unspecified)


def _resolved_public_addresses(host: str, port: int) -> list[str]:
    try:
        values = {entry[4][0] for entry in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("MARKETPLACE_DNS_FAILED") from exc
    addresses = []
    for value in values:
        address = ipaddress.ip_address(value)
        if (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved
                or address.is_multicast or address.is_unspecified):
            raise ValueError("MARKETPLACE_DNS_UNSAFE")
        addresses.append(value)
    return sorted(addresses)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """TLS connection pinned to the address that passed SSRF validation."""

    def __init__(self, host: str, address: str, port: int, *, timeout: float) -> None:
        super().__init__(host, port=port, timeout=timeout, context=ssl.create_default_context())
        self._validated_address = address

    def connect(self) -> None:
        raw = socket.create_connection((self._validated_address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise
