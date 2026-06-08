"""Read-only access to a system's UI assets (Sheet API — system CSS/JS).

Systems declare front-end assets in their manifest under ``system.assets``
(``styles`` / ``scripts``, package-relative paths). The core serves only the
*declared* files (a whitelist) from the system package directory, so a system
can ship its own sheet skin and behaviour without inflating the core VTT
bundle. Like every System API surface this layer is descriptive — it never
executes anything server-side; it only serves static files.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.systems import system_loader
from app.engine.systems.system_loader import safe_join
from app.engine.systems.system_manifest import SystemManifest
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository

_STATUS_ENABLED = "enabled"

_CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
}


class SystemAssetService:
    """Serves and lists the UI assets declared by enabled systems."""

    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()

    def _enabled_record_manifest(self, system_id: str) -> tuple[dict, SystemManifest] | None:
        record = self.installed.get(system_id)
        if record is None or record["status"] != _STATUS_ENABLED:
            return None
        try:
            manifest = SystemManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        return record, manifest

    def list_enabled_assets(self) -> list[dict]:
        """One descriptor per enabled system that declares UI assets.

        ``styles``/``scripts`` are package-relative paths; the caller turns them
        into ``/systems/<id>/asset/<path>`` URLs (with ``version`` for busting).
        """
        out: list[dict] = []
        for record in self.installed.list_all():
            if record["status"] != _STATUS_ENABLED:
                continue
            pair = self._enabled_record_manifest(record["id"])
            if pair is None:
                continue
            _, manifest = pair
            styles = manifest.asset_styles
            scripts = manifest.asset_scripts
            if not styles and not scripts:
                continue
            out.append(
                {
                    "system_id": manifest.id,
                    "version": manifest.version or "0",
                    "styles": styles,
                    "scripts": scripts,
                }
            )
        return out

    def resolve(self, system_id: str, relative_path: str) -> tuple[Path, str] | None:
        """Resolve a declared asset to an on-disk path + content type, or ``None``.

        Only files listed in the manifest's ``assets`` block are servable, and
        only for an *enabled* system; everything else returns ``None`` (404).
        """
        pair = self._enabled_record_manifest(system_id)
        if pair is None:
            return None
        record, manifest = pair
        relative = relative_path.lstrip("/")
        declared = set(manifest.asset_styles) | set(manifest.asset_scripts)
        if relative not in declared:
            return None
        base = system_loader.SYSTEMS_DIR / record["package_dir"]
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        content_type = _CONTENT_TYPES.get(path.suffix.lower())
        if content_type is None:
            return None
        return path, content_type
