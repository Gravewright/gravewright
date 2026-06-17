"""Load a single SDK package from disk into a validated in-memory shape.

A package directory is the unit of installation; its ``manifest.json`` is read,
parsed, modelled, and validated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.engine.sdk.package_manifest import DIRECTORY_TO_KIND, PackageManifest
from app.engine.sdk.package_manifest_validator import (
    PackageManifestValidation,
    validate_manifest,
)
from app.engine.sdk.package_interop import interop_schema_paths
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_storage import storage_block, validate_named_queries

MANIFEST_FILENAME = "manifest.json"


@dataclass
class LoadedPackage:
    package_dir: Path
    manifest: PackageManifest
    validation: PackageManifestValidation
    raw: dict
    # The ``kind_plural`` directory the package was discovered under
    # (``addons``, ``rulesets``, …).
    kind_dir: str | None = None

    @property
    def id(self) -> str:
        return self.manifest.id or self.package_dir.name

    @property
    def ok(self) -> bool:
        return self.validation.ok

    @property
    def relative_dir(self) -> str:
        """Path relative to the packages root, e.g. ``rulesets/<id>``."""
        return f"{self.kind_dir}/{self.id}" if self.kind_dir else self.id


def load_package(
    package_dir: Path,
    *,
    expected_id: str | None = None,
    expected_kind_root: str | None = None,
) -> LoadedPackage:
    """Load and validate a package directory.

    ``expected_id`` (the directory name) and ``expected_kind_root`` (the
    ``kind_plural`` parent directory, when grouped) bind the package's on-disk
    location to its manifest identity: a mismatch is a structural error
    (``sdk.manifest.id_mismatch`` / ``sdk.manifest.kind_root_mismatch``). These
    checks run before any integrity hash or storage path is derived.
    """
    manifest_path = package_dir / MANIFEST_FILENAME
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw = {}
        validation = PackageManifestValidation(errors=["sdk.validation.manifest_missing"])
        return LoadedPackage(
            package_dir, PackageManifest.from_dict(raw), validation, {}, expected_kind_root
        )
    except (json.JSONDecodeError, OSError):
        raw = {}
        validation = PackageManifestValidation(errors=["sdk.validation.manifest_unreadable"])
        return LoadedPackage(
            package_dir, PackageManifest.from_dict(raw), validation, {}, expected_kind_root
        )

    manifest = PackageManifest.from_dict(raw)
    validation = validate_manifest(raw)

    # Identity binding: the manifest id must match the directory name, and the
    # kind must match the kind_plural root the package lives under.
    if expected_id and manifest.id and manifest.id != expected_id:
        validation.add("sdk.manifest.id_mismatch")
    if expected_kind_root is not None:
        expected_kind = DIRECTORY_TO_KIND.get(expected_kind_root)
        if expected_kind and manifest.kind and manifest.kind != expected_kind:
            validation.add("sdk.manifest.kind_root_mismatch")

    # Every declared path must resolve inside the package and exist on disk.
    for relative in manifest.referenced_paths():
        resolved = safe_join(package_dir, relative)
        if resolved is None:
            validation.add("sdk.validation.path_unsafe")
        elif not resolved.exists():
            validation.add("sdk.validation.file_missing")

    # Storage contract (Phase 7A): validate declared migrations dir + queries file.
    for code in _validate_storage_on_disk(package_dir, raw):
        validation.add(code)

    # Interop contract (Phase 12): declared event/RPC schemas must exist on disk.
    for relative in interop_schema_paths(raw):
        resolved = safe_join(package_dir, relative)
        if resolved is None:
            validation.add("sdk.interop.schema_path_unsafe")
        elif not resolved.is_file():
            validation.add("sdk.interop.schema_missing")

    for code in _validate_html_sheets_on_disk(package_dir, manifest):
        validation.add(code)

    return LoadedPackage(
        package_dir,
        manifest,
        validation,
        raw if isinstance(raw, dict) else {},
        expected_kind_root,
    )


def _validate_storage_on_disk(package_dir: Path, raw: dict) -> list[str]:
    """Disk-level storage contract checks: migrations dir + queries.json file."""
    block = storage_block(raw)
    if block is None:
        return []
    codes: list[str] = []

    migrations = block.get("migrations")
    if isinstance(migrations, str) and migrations:
        resolved = safe_join(package_dir, migrations)
        if resolved is None:
            codes.append("sdk.storage.migration_path_unsafe")
        elif not resolved.is_dir():
            codes.append("sdk.storage.migration_path_missing")

    queries = block.get("queries")
    if isinstance(queries, str) and queries:
        resolved = safe_join(package_dir, queries)
        if resolved is None:
            codes.append("sdk.storage.queries_path_unsafe")
        elif not resolved.is_file():
            codes.append("sdk.storage.queries_path_missing")
        else:
            try:
                data = json.loads(resolved.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                codes.append("sdk.storage.queries_path_missing")
            else:
                codes.extend(validate_named_queries(data))
    return codes


_INLINE_HANDLER = re.compile(r"\s(on[a-zA-Z][a-zA-Z0-9_-]*)\s*=")


def _validate_html_sheets_on_disk(
    package_dir: Path, manifest: PackageManifest
) -> list[str]:
    codes: list[str] = []
    for type_def in (*manifest.provides.actor_types, *manifest.provides.item_types):
        sheet = type_def.sheet
        if not isinstance(sheet, dict) or sheet.get("mode") != "html":
            continue
        template = sheet.get("template")
        if isinstance(template, str) and template:
            resolved = safe_join(package_dir, template)
            if resolved is None:
                codes.append("sdk.sheets.html.template_unsafe_path")
            elif not resolved.is_file():
                codes.append("sdk.sheets.html.template_missing")
            else:
                try:
                    html = resolved.read_text(encoding="utf-8")
                except OSError:
                    codes.append("sdk.sheets.html.template_missing")
                else:
                    lowered = html.lower()
                    if "<script" in lowered or "</script" in lowered:
                        codes.append("sdk.sheets.html.inline_script_forbidden")
                    if _INLINE_HANDLER.search(html):
                        codes.append("sdk.sheets.html.inline_handler_forbidden")
                    if "data-rich-text" in html and "sheets.richText" not in manifest.capabilities:
                        codes.append("sdk.sheets.html.rich_text_capability_missing")

        controller = sheet.get("controller")
        if isinstance(controller, str) and controller:
            resolved = safe_join(package_dir, controller)
            if resolved is None:
                codes.append("sdk.sheets.html.controller_unsafe_path")
            elif not resolved.is_file():
                codes.append("sdk.sheets.html.controller_missing")

        style = sheet.get("style")
        if isinstance(style, str) and style:
            resolved = safe_join(package_dir, style)
            if resolved is None:
                codes.append("sdk.sheets.html.style_unsafe_path")
            elif not resolved.is_file():
                codes.append("sdk.sheets.html.style_missing")

    seen: set[str] = set()
    return [c for c in codes if not (c in seen or seen.add(c))]
