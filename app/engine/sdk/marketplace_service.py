"""Refreshes remote manifests into an atomic, permission-neutral local cache."""

from __future__ import annotations

import json
import ipaddress
import os
import time
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from app.config import config
from app.engine.sdk.marketplace_registry import MarketplaceRegistryError, load_marketplace
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE, version_key
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_manifest import SDK_VERSION
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = PROJECT_ROOT / "marketplace.toml"
DEFAULT_CACHE = Path(config.data_dir) / "marketplace" / "cache.json"
MAX_MANIFEST_BYTES = 1024 * 1024

Fetch = Callable[[str, int], bytes]


def fetch_bytes(url: str, limit: int) -> bytes:
    if not _safe_remote_url(url):
        raise ValueError("MARKETPLACE_URL_UNSAFE")
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Gravewright-Marketplace/1"})
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=15) as response:  # noqa: S310 - URL policy enforced on every hop
        if not _safe_remote_url(response.geturl()):
            raise ValueError("MARKETPLACE_URL_UNSAFE")
        length = int(response.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError("MARKETPLACE_RESPONSE_TOO_LARGE")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("MARKETPLACE_RESPONSE_TOO_LARGE")
    return data


class MarketplaceService:
    def __init__(self, *, registry_path: Path = DEFAULT_REGISTRY, cache_path: Path = DEFAULT_CACHE, fetcher: Fetch = fetch_bytes) -> None:
        self.registry_path = registry_path
        self.cache_path = cache_path
        self.fetcher = fetcher
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
            entries = load_marketplace(self.registry_path)
        except MarketplaceRegistryError as exc:
            return {**previous, "refreshStatus": "failed", "refreshError": str(exc)}

        packages = []
        network_failures = 0
        enabled_entries = [entry for entry in entries if entry.enabled]
        for entry in entries:
            if not entry.enabled:
                continue
            item = {"id": entry.id, "name": entry.name, "kind": entry.kind, "manifestUrl": entry.manifest,
                    "channel": entry.channel, "category": entry.category, "tags": list(entry.tags),
                    "featured": entry.featured, "reviewedAt": entry.reviewed_at,
                    "updatePolicy": entry.update_policy, "approvedVersion": entry.approved_version,
                    "validationState": "unavailable"}
            try:
                try:
                    manifest_bytes = self.fetcher(entry.manifest, MAX_MANIFEST_BYTES)
                except Exception as exc:
                    network_failures += 1
                    raise ValueError("MARKETPLACE_MANIFEST_FETCH_FAILED") from exc
                raw = json.loads(manifest_bytes)
                validation = validate_manifest(raw)
                manifest = PackageManifest.from_dict(raw)
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
                if (distribution is None or distribution.type != "zip" or not _valid_download(distribution.url)
                        or not _valid_sha256(distribution.sha256)):
                    raise ValueError("MARKETPLACE_ARTIFACT_INVALID")
                if entry.update_policy == "curated" and manifest.version != entry.approved_version:
                    raise ValueError("MARKETPLACE_VERSION_NOT_APPROVED")
                if entry.approved_sha256 and distribution.sha256.lower() != entry.approved_sha256:
                    raise ValueError("MARKETPLACE_CHECKSUM_NOT_APPROVED")
                item.update({
                    "name": entry.name or manifest.name, "description": manifest.description,
                    "publisher": manifest.author_names()[0] if manifest.author_names() else "",
                    "version": manifest.version, "sdkVersion": manifest.sdk_version,
                    "compatibility": validation.compatibility_status,
                    "validationState": "incompatible" if validation.compatibility_status == COMPAT_INCOMPATIBLE else "valid",
                    "artifact": {"url": distribution.url, "sha256": distribution.sha256},
                    "manifestIdentity": {"id": manifest.id, "kind": manifest.kind,
                                         "version": manifest.version, "sdkVersion": manifest.sdk_version},
                })
            except Exception as exc:  # one bad manifest never destroys valid siblings
                item["validationError"] = str(exc)
            packages.append(item)

        if enabled_entries and network_failures == len(enabled_entries) and previous.get("packages"):
            return {**previous, "refreshStatus": "failed", "refreshError": "MARKETPLACE_REFRESH_FAILED"}
        result = {"version": 1, "lastRefresh": int(time.time()), "refreshStatus": "ok", "packages": packages}
        self._write_cache(result)
        return result

    def catalog(self) -> dict:
        cache = self.read_cache()
        installed = {row["id"]: row for row in self.installed.list_all()}
        packages = []
        for item in cache.get("packages", []):
            package = dict(item)
            record = installed.get(package.get("id"))
            if package.get("validationState") == "incompatible":
                action = "incompatible"
            elif package.get("validationState") != "valid":
                action = "unavailable"
            elif record is None:
                action = "install"
            elif version_key(str(package.get("version", ""))) > version_key(str(record.get("version", ""))):
                action = "update"
            else:
                action = "installed"
            package["installState"] = action
            package["installedVersion"] = str(record.get("version", "")) if record else ""
            packages.append(package)
        return {**cache, "packages": packages}

    def catalog_with_automatic_refresh(self) -> dict:
        """Refresh when the cache is absent or the local registry changed."""
        cache = self.read_cache()
        last_refresh = int(cache.get("lastRefresh") or 0)
        try:
            registry_changed = self.registry_path.stat().st_mtime > last_refresh
        except OSError:
            registry_changed = False
        if last_refresh == 0 or registry_changed:
            self.refresh()
        return self.catalog()

    def get_valid(self, package_id: str) -> dict | None:
        return next((item for item in self.catalog().get("packages", [])
                     if item.get("id") == package_id and item.get("validationState") == "valid"), None)

    def _write_cache(self, document: dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
        os.replace(temporary, self.cache_path)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _valid_download(value: str) -> bool:
    return _safe_remote_url(value)


def _safe_remote_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
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


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_remote_url(newurl):
            raise ValueError("MARKETPLACE_REDIRECT_UNSAFE")
        return super().redirect_request(req, fp, code, msg, headers, newurl)
