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
import time
import uuid
from pathlib import Path

from app.config import config
from app.engine.sdk.marketplace_service import fetch_bytes
from app.engine.sdk.package_compatibility import update_version_is_valid, version_key

RELEASES_URL = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"
MAX_RELEASE_METADATA_BYTES = 2 * 1024 * 1024
CACHE_PATH = Path(config.data_dir) / "updates" / "core.json"
CACHE_TTL_SECONDS = 24 * 60 * 60


def _clean_version(value: str) -> str:
    value = value.strip()
    return value[1:] if value.lower().startswith("v") else value


def _channel(version: str) -> str:
    lowered = version.lower()
    if "alpha" in lowered:
        return "alpha"
    if "beta" in lowered or "rc" in lowered:
        return "beta"
    return "stable"


def _install_format() -> str:
    if os.environ.get("GRAVEWRIGHT_CONTAINER", "").lower() in {"1", "true", "yes"}:
        return "container"
    if getattr(sys, "frozen", False) and platform.system() == "Windows":
        return "win64"
    return "source"


class CoreUpdateService:
    def __init__(self, *, fetcher=fetch_bytes, cache_path: Path = CACHE_PATH,
                 current_version: str | None = None) -> None:
        self.fetcher = fetcher
        self.cache_path = cache_path
        self.current_version = current_version or config.gravewright_version

    def status(self) -> dict:
        current = _clean_version(self.current_version)
        channel = _channel(current)
        try:
            cached = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = {}
        valid = (isinstance(cached, dict) and cached.get("currentVersion") == current
                 and cached.get("channel") == channel
                 and cached.get("installFormat") == _install_format()
                 and isinstance(cached.get("checkedAt"), int)
                 and int(cached["checkedAt"]) >= int(time.time()) - CACHE_TTL_SECONDS
                 and cached.get("status") in {"available", "current", "failed"})
        if not valid:
            cached = {"status": "unchecked", "channel": channel}
        return {"currentVersion": current, "installFormat": _install_format(), **cached}

    def check(self) -> dict:
        current = _clean_version(self.current_version)
        channel = _channel(current)
        try:
            releases = json.loads(self.fetcher(RELEASES_URL, MAX_RELEASE_METADATA_BYTES))
            if not isinstance(releases, list):
                raise ValueError("CORE_RELEASE_METADATA_INVALID")
            candidates = []
            for release in releases:
                if not isinstance(release, dict) or release.get("draft"):
                    continue
                version = _clean_version(str(release.get("tag_name") or ""))
                if not update_version_is_valid(version) or _channel(version) != channel:
                    continue
                asset = self._asset(release, version)
                if asset:
                    candidates.append((version_key(version), release, asset, version))
            if not candidates:
                raise ValueError("CORE_RELEASE_CHANNEL_UNAVAILABLE")
            _, release, asset, available = max(candidates, key=lambda item: item[0])
            update_available = version_key(available) > version_key(current)
            result = {
                "checkedAt": int(time.time()), "status": "available" if update_available else "current",
                "currentVersion": current, "availableVersion": available, "channel": channel,
                "installFormat": _install_format(), "releaseName": str(release.get("name") or available),
                "releaseNotes": str(release.get("body") or "")[:4000],
                "releaseUrl": str(release.get("html_url") or ""),
                "artifact": asset if update_available else None,
                "requiresBackup": update_available,
            }
        except Exception as exc:
            result = {"checkedAt": int(time.time()), "status": "failed", "currentVersion": current,
                      "channel": channel, "installFormat": _install_format(), "errorKey": str(exc)}
        self._write(result)
        return result

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
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
        temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.cache_path)
