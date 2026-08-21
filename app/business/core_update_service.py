"""Fail-closed discovery of official Gravewright product releases.

This service never mutates the running installation. Product artifacts are
selected from signed release metadata, not branches or arbitrary manifest URLs.
The operator explicitly downloads the verified release for the detected format;
source and container installs receive format-specific upgrade guidance.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import threading
import time
import uuid
from pathlib import Path

from app.config import config
from app.engine.sdk.marketplace_registry import (
    load_marketplace_document, parse_marketplace_document,
)
from app.engine.sdk.marketplace_service import (
    DEFAULT_REGISTRY_CACHE, DEFAULT_REGISTRY_URL, MAX_REGISTRY_BYTES, fetch_bytes,
)
from app.engine.sdk.package_compatibility import update_version_is_valid, version_key

RELEASES_URL = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"
MAX_RELEASE_METADATA_BYTES = 2 * 1024 * 1024
CACHE_PATH = Path(config.data_dir) / "updates" / "core.json"
CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_WRITE_LOCK = threading.Lock()


def _clean_version(value: str) -> str:
    value = value.strip()
    return value[1:] if value.lower().startswith("v") else value


def _channel(version: str) -> str:
    lowered = version.lower()
    if any(marker in lowered for marker in ("dev", "alpha", "nightly")):
        return "dev"
    if "beta" in lowered or "rc" in lowered:
        return "testing"
    return "stable"


def _channel_order(selected: str) -> tuple[str, ...]:
    return {
        "stable": ("stable",),
        "testing": ("testing", "stable"),
        "dev": ("dev", "testing", "stable"),
    }.get(selected, ("stable",))


def _install_format() -> str:
    if os.environ.get("GRAVEWRIGHT_CONTAINER", "").lower() in {"1", "true", "yes"}:
        return "container"
    if getattr(sys, "frozen", False) and platform.system() == "Windows":
        return "win64"
    return "source"


class CoreUpdateService:
    def __init__(self, *, fetcher=fetch_bytes, cache_path: Path = CACHE_PATH,
                 current_version: str | None = None, channel: str | None = None,
                 registry_fetcher=fetch_bytes,
                 registry_cache_path: Path = DEFAULT_REGISTRY_CACHE) -> None:
        self.fetcher = fetcher
        self.registry_fetcher = registry_fetcher
        self.registry_cache_path = registry_cache_path
        self.cache_path = cache_path
        self.current_version = current_version or config.gravewright_version
        self.catalog_bound = current_version is None
        if channel is None:
            if current_version is not None:
                channel = _channel(_clean_version(current_version))
            else:
                from app.business.inside_settings_service import InsideSettingsService
                channel = str(InsideSettingsService().read()["updates"]["core_channel"])
        self.channel = channel if channel in {"stable", "testing", "dev"} else "stable"

    def status(self) -> dict:
        current = _clean_version(self.current_version)
        channel = self.channel
        try:
            cached = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = {}
        valid = (isinstance(cached, dict) and cached.get("currentVersion") == current
                 and cached.get("channel") == channel
                 and cached.get("installFormat") == _install_format()
                 and isinstance(cached.get("checkedAt"), int)
                 and int(cached["checkedAt"]) >= int(time.time()) - CACHE_TTL_SECONDS
                 and cached.get("status") in {"available", "current", "ahead-of-channel", "failed"})
        if not valid:
            cached = {"status": "unchecked", "channel": channel}
        return {"currentVersion": current, "installFormat": _install_format(), **cached}

    def check(self) -> dict:
        current = _clean_version(self.current_version)
        channel = self.channel
        try:
            release_url = RELEASES_URL
            channel_order = _channel_order(channel)
            published_channels = list(channel_order)
            if self.catalog_bound:
                core = self._catalog_core()
                if core is None or not core.enabled:
                    raise ValueError("CORE_MARKETPLACE_ENTRY_UNAVAILABLE")
                resolved = core.release_channel_for(channel)
                if resolved is None:
                    raise ValueError("CORE_RELEASE_CHANNEL_UNAVAILABLE")
                release_url = core.releases
                channel_order = (resolved,)
                published_channels = sorted(core.channels)
            releases = json.loads(self.fetcher(release_url, MAX_RELEASE_METADATA_BYTES))
            if not isinstance(releases, list):
                raise ValueError("CORE_RELEASE_METADATA_INVALID")
            candidates_by_channel: dict[str, list] = {name: [] for name in channel_order}
            for release in releases:
                if not isinstance(release, dict) or release.get("draft"):
                    continue
                version = _clean_version(str(release.get("tag_name") or ""))
                release_channel = _channel(version)
                if not update_version_is_valid(version) or release_channel not in candidates_by_channel:
                    continue
                asset = self._asset(release, version)
                if asset:
                    candidates_by_channel[release_channel].append((version_key(version), release, asset, version))
            resolved_channel = next((name for name in channel_order if candidates_by_channel[name]), None)
            if resolved_channel is None:
                raise ValueError("CORE_RELEASE_CHANNEL_UNAVAILABLE")
            candidates = candidates_by_channel[resolved_channel]
            _, release, asset, available = max(candidates, key=lambda item: item[0])
            comparison = (version_key(available) > version_key(current)) - (
                version_key(available) < version_key(current)
            )
            status = "available" if comparison > 0 else "ahead-of-channel" if comparison < 0 else "current"
            result = {
                "checkedAt": int(time.time()), "status": status,
                "currentVersion": current, "availableVersion": available, "channel": channel,
                "resolvedChannel": resolved_channel,
                "publishedChannels": published_channels,
                "installFormat": _install_format(), "releaseName": str(release.get("name") or available),
                "releaseNotes": str(release.get("body") or "")[:4000],
                "releaseUrl": str(release.get("html_url") or ""),
                "artifact": asset if comparison > 0 else None,
                "requiresBackup": comparison > 0,
                "channelRisk": "critical" if channel == "dev" else "preview" if channel == "testing" else "normal",
            }
        except Exception as exc:
            result = {"checkedAt": int(time.time()), "status": "failed", "currentVersion": current,
                      "channel": channel, "installFormat": _install_format(), "errorKey": str(exc)}
        self._write(result)
        return result

    def _catalog_core(self):
        try:
            raw = self.registry_fetcher(DEFAULT_REGISTRY_URL, MAX_REGISTRY_BYTES)
            registry = parse_marketplace_document(raw)
            with _CACHE_WRITE_LOCK:
                self.registry_cache_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.registry_cache_path.with_suffix(
                    f".tmp-{os.getpid()}-{uuid.uuid4().hex}"
                )
                temporary.write_bytes(raw)
                temporary.replace(self.registry_cache_path)
            return registry.core
        except Exception:
            try:
                return load_marketplace_document(self.registry_cache_path).core
            except Exception as cache_error:
                raise ValueError("CORE_MARKETPLACE_REGISTRY_UNAVAILABLE") from cache_error

    @staticmethod
    def _asset(release: dict, version: str) -> dict | None:
        expected = f"Gravewright-{version}-win64.zip".lower()
        matches = [raw for raw in release.get("assets") or [] if isinstance(raw, dict)
                   and str(raw.get("name", "")).lower() == expected]
        if len(matches) != 1:
            return None
        for raw in matches:
            digest = str(raw.get("digest") or "")
            if (not digest.startswith("sha256:") or len(digest) != 71
                    or any(char not in "0123456789abcdefABCDEF" for char in digest[7:])):
                continue
            url = str(raw.get("browser_download_url") or "")
            size = raw.get("size")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > 1024 ** 3:
                continue
            from urllib.parse import urlparse
            parsed = urlparse(url)
            expected_prefix = f"/Gravewright/gravewright/releases/download/v{version}/"
            if (parsed.scheme != "https" or parsed.hostname != "github.com"
                    or not parsed.path.startswith(expected_prefix) or parsed.query or parsed.fragment):
                continue
            return {"name": raw.get("name"), "url": url, "sha256": digest[7:], "size": size}
        return None

    def _write(self, result: dict) -> None:
        with _CACHE_WRITE_LOCK:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
            temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.cache_path)
