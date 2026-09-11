"""Discover Django source releases from an explicitly configured repository.

Never mutates the running installation. Metadata requires a SHA-256 digest;
the operator must verify downloaded bytes before a manual upgrade. Legacy
Windows artifacts and unsupported installation formats are not offered.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import threading
import time
import uuid
from pathlib import Path

from django.conf import settings

from .release_metadata import fetch_bytes, normalize_version, update_version_is_valid, version_key, version_label
from gravewright.version import release_version

MAX_RELEASE_METADATA_BYTES = 2 * 1024 * 1024
CACHE_PATH = None
CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_WRITE_LOCK = threading.Lock()


def _clean_version(value: str) -> str:
    return normalize_version(value)


def _channel(version: str) -> str:
    lowered = normalize_version(version).lower()
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
    def __init__(
        self,
        *,
        fetcher=fetch_bytes,
        cache_path: Path = CACHE_PATH,
        current_version: str | None = None,
        channel: str | None = None,
    ) -> None:
        self.repository = settings.GRAVEWRIGHT_RELEASES_REPOSITORY.strip()
        self.fetcher = fetcher
        self.cache_path = cache_path
        self.current_version = _clean_version(current_version or release_version())
        if channel is None:
            if current_version is not None:
                channel = _channel(_clean_version(current_version))
            else:
                from .models import HostSettings

                channel = HostSettings.objects.get_or_create(pk=1)[0].channel
        self.channel = channel if channel in {"stable", "testing", "dev"} else "stable"

    def status(self) -> dict:
        current = _clean_version(self.current_version)
        channel = self.channel
        try:
            from .models import HostSettings

            cached = (
                HostSettings.objects.get_or_create(pk=1)[0].update_status
                if self.cache_path is None
                else json.loads(self.cache_path.read_text(encoding="utf-8"))
            )
        except OSError, ValueError:
            cached = {}
        valid = (
            isinstance(cached, dict)
            and cached.get("currentVersion") == current
            and cached.get("channel") == channel
            and cached.get("installFormat") == _install_format()
            and cached.get("repository") == self.repository
            and isinstance(cached.get("checkedAt"), int)
            and int(cached["checkedAt"]) >= int(time.time()) - CACHE_TTL_SECONDS
            and cached.get("status")
            in {"available", "current", "ahead-of-channel", "failed"}
        )
        if not valid:
            cached = {"status": "unchecked", "channel": channel}
        return {"currentVersion": current, "installFormat": _install_format(), **cached,
                "currentVersionLabel": version_label(current)}

    def check(self) -> dict:
        current = _clean_version(self.current_version)
        channel = self.channel
        try:
            if not self.repository:
                raise ValueError("CORE_RELEASE_SOURCE_NOT_CONFIGURED")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
                raise ValueError("CORE_RELEASE_SOURCE_INVALID")
            if _install_format() != "source":
                raise ValueError("CORE_INSTALL_FORMAT_UNSUPPORTED")
            release_url = f"https://api.github.com/repos/{self.repository}/releases?per_page=30"
            channel_order = _channel_order(channel)
            published_channels = list(channel_order)
            releases = json.loads(self.fetcher(release_url, MAX_RELEASE_METADATA_BYTES))
            if not isinstance(releases, list):
                raise ValueError("CORE_RELEASE_METADATA_INVALID")
            candidates_by_channel: dict[str, list] = {
                name: [] for name in channel_order
            }
            for release in releases:
                if not isinstance(release, dict) or release.get("draft"):
                    continue
                version = _clean_version(str(release.get("tag_name") or ""))
                release_channel = _channel(version)
                if (
                    not update_version_is_valid(version)
                    or release_channel not in candidates_by_channel
                ):
                    continue
                asset = self._asset(release, version)
                if asset:
                    candidates_by_channel[release_channel].append(
                        (version_key(version), release, asset, version)
                    )
            resolved_channel = next(
                (name for name in channel_order if candidates_by_channel[name]), None
            )
            if resolved_channel is None:
                raise ValueError("CORE_RELEASE_CHANNEL_UNAVAILABLE")
            candidates = candidates_by_channel[resolved_channel]
            _, release, asset, available = max(candidates, key=lambda item: item[0])
            comparison = (version_key(available) > version_key(current)) - (
                version_key(available) < version_key(current)
            )
            status = (
                "available"
                if comparison > 0
                else "ahead-of-channel"
                if comparison < 0
                else "current"
            )
            result = {
                "repository": self.repository,
                "checkedAt": int(time.time()),
                "status": status,
                "currentVersion": current,
                "currentVersionLabel": version_label(current),
                "availableVersion": available,
                "availableVersionLabel": version_label(available),
                "channel": channel,
                "resolvedChannel": resolved_channel,
                "publishedChannels": published_channels,
                "installFormat": _install_format(),
                "releaseName": str(release.get("name") or available),
                "releaseNotes": str(release.get("body") or "")[:4000],
                "releaseUrl": str(release.get("html_url") or ""),
                "artifact": asset if comparison > 0 else None,
                "requiresBackup": comparison > 0,
                "channelRisk": "critical"
                if channel == "dev"
                else "preview"
                if channel == "testing"
                else "normal",
            }
        except Exception as exc:
            result = {
                "repository": self.repository,
                "checkedAt": int(time.time()),
                "status": "failed",
                "currentVersion": current,
                "currentVersionLabel": version_label(current),
                "channel": channel,
                "installFormat": _install_format(),
                "errorKey": str(exc),
            }
        self._write(result)
        return result

    def _asset(self, release: dict, version: str) -> dict | None:
        expected = f"Gravewright-{version}-django.zip".lower()
        matches = [
            raw
            for raw in release.get("assets") or []
            if isinstance(raw, dict) and str(raw.get("name", "")).lower() == expected
        ]
        if len(matches) != 1:
            return None
        for raw in matches:
            digest = str(raw.get("digest") or "")
            if (
                not digest.startswith("sha256:")
                or len(digest) != 71
                or any(char not in "0123456789abcdefABCDEF" for char in digest[7:])
            ):
                continue
            url = str(raw.get("browser_download_url") or "")
            size = raw.get("size")
            if (
                not isinstance(size, int)
                or isinstance(size, bool)
                or size <= 0
                or size > 1024**3
            ):
                continue
            from urllib.parse import urlparse

            parsed = urlparse(url)
            expected_path = f"/{self.repository}/releases/download/{release['tag_name']}/{raw['name']}"
            if (
                parsed.scheme != "https"
                or parsed.hostname != "github.com"
                or parsed.path != expected_path
                or parsed.netloc != "github.com"
                or parsed.query
                or parsed.fragment
            ):
                continue
            return {
                "name": raw.get("name"),
                "url": url,
                "sha256": digest[7:],
                "size": size,
            }
        return None

    def _write(self, result: dict) -> None:
        if self.cache_path is None:
            from .models import HostSettings

            HostSettings.objects.update_or_create(
                pk=1, defaults={"update_status": result}
            )
            return
        with _CACHE_WRITE_LOCK:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(
                f".tmp-{os.getpid()}-{uuid.uuid4().hex}"
            )
            temporary.write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(self.cache_path)
