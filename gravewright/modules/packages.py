"""Install signed browser packages and persist their table-scoped configuration.

The host validates archive bytes but never imports package Python or executes
package binaries. JavaScript later runs in the user's main browser page, without
a sandbox; signing keys therefore identify trusted publishers, not permissions.
See ``docs/en/modules.md`` (``docs/pt-BR/modules.md`` in Portuguese).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).with_name("contracts")
SDK_VERSION = (1, 0, 0)
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024
MAX_FILES = 4096
MAX_VALUE = 256 * 1024
MAX_NAMESPACE = 4 * 1024 * 1024

from django.db import transaction

from gravewright.accounts.services import AuthError

from .models import ModuleSet, ModuleValue, Package


class ModuleFailure(AuthError):
    def __init__(self, code, message=None):
        super().__init__(
            code,
            {
                "permission_denied": 403,
                "not_found": 404,
                "conflict": 409,
                "stale_context": 409,
                "unavailable": 503,
            }.get(code, 400),
        )


def canonical(record: dict) -> bytes:
    """Return the exact ASCII JSON bytes covered by the publisher's signature."""
    # Catalog fields are ASCII strings; no floating point/cross-language number ambiguity.
    return json.dumps(
        {k: v for k, v in record.items() if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def compatible(value: str) -> bool:
    """Stable release comparator conjunction, deliberately rejects unknown range syntax."""
    if not isinstance(value, str) or not value.strip():
        return False
    for term in value.split():
        match = re.fullmatch(
            r"(>=|<=|>|<|=)?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", term
        )
        if not match:
            return False
        operator, *digits = match.groups()
        version = tuple(map(int, digits))
        if not {
            ">=": SDK_VERSION >= version,
            "<=": SDK_VERSION <= version,
            ">": SDK_VERSION > version,
            "<": SDK_VERSION < version,
            "=": SDK_VERSION == version,
        }[operator or "="]:
            return False
    return True


def safe_path(name: str) -> PurePosixPath:
    """Accept a relative archive path without traversal or URL interpretation."""
    if (
        not isinstance(name, str)
        or not name
        or any(c in name for c in ("\\", "\x00", ":", "%", "?", "#"))
    ):
        raise ModuleFailure("invalid_data", "Invalid package path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        raise ModuleFailure("invalid_data", "Invalid package path")
    return path


class Contracts:
    """Load the checked-in SDK registry and validate its JSON data boundaries."""
    def __init__(self):
        self.registry = json.loads((CONTRACTS / "registry.json").read_text())
        self.validators = {}
        for path in (CONTRACTS / "schemas").glob("*.json"):
            schema = json.loads(path.read_text())
            Draft202012Validator.check_schema(schema)
            self.validators["schemas/" + path.name] = Draft202012Validator(schema)

    def validate(self, path, value):
        try:
            json.dumps(value, allow_nan=False)
            if not self.validators[path].is_valid(value):
                raise ValueError()
        except ValueError, TypeError, RecursionError:
            raise ModuleFailure("invalid_data") from None


class ModulePackages:
    """Manage immutable releases, activation revisions, and module JSON values.

    HTTP views own user/GM authorization. These lower-level methods assume callers
    have established that authority and enforce package and concurrency invariants.
    """
    def __init__(self, directory: Path, keys: dict[str, str] | None = None):
        if keys is not None:
            if not isinstance(keys, dict):
                raise ValueError("Marketplace keys must be a keyId-to-base64 object")
            for key_id, value in keys.items():
                if not isinstance(key_id, str) or not isinstance(value, str):
                    raise ValueError("Invalid marketplace key")
                try:
                    Ed25519PublicKey.from_public_bytes(
                        base64.b64decode(value, validate=True)
                    )
                except ValueError:
                    raise ValueError("Invalid marketplace public key") from None
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.keys = keys or {}
        self.contracts = Contracts()

    def verify(self, record: dict, *, require_compatible=True):
        """Authenticate a catalog record, optionally allowing incompatible releases."""
        fields = {"id", "version", "sdk", "download", "sha256", "keyId", "signature"}
        if not isinstance(record, dict):
            raise ModuleFailure("invalid_data")
        if (
            not fields <= set(record)
            or set(record) - fields - {"status"}
            or any(not isinstance(v, str) or not v.isascii() for v in record.values())
        ):
            raise ModuleFailure("invalid_data", "Invalid signed record")
        if not re.fullmatch("[a-f0-9]{64}", record["sha256"]):
            raise ModuleFailure("invalid_data")
        url = urlsplit(record["download"])
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.fragment
        ):
            raise ModuleFailure("invalid_data")
        key = self.keys.get(record["keyId"])
        if not key:
            raise ModuleFailure("permission_denied", "Unknown marketplace signing key")
        try:
            Ed25519PublicKey.from_public_bytes(
                base64.b64decode(key, validate=True)
            ).verify(
                base64.b64decode(record["signature"], validate=True), canonical(record)
            )
        except ValueError, InvalidSignature:
            raise ModuleFailure(
                "permission_denied", "Invalid marketplace signature"
            ) from None
        if record.get("status", "active") not in ("active", "revoked"):
            raise ModuleFailure("invalid_data")
        if require_compatible and not compatible(record["sdk"]):
            raise ModuleFailure("unavailable", "Incompatible SDK")

    def revoke(self, record: dict):
        """Apply a signed revocation and invalidate every affected table's revision."""
        self.verify(record, require_compatible=False)
        if record.get("status") != "revoked":
            raise ModuleFailure("invalid_data")
        with transaction.atomic():
            Package.objects.filter(
                module_id=record["id"], version=record["version"]
            ).update(revoked=True)
            for row in ModuleSet.objects.select_for_update():
                if row.modules.get(record["id"]) == record["version"]:
                    del row.modules[record["id"]]
                    row.replacements = {
                        k: v for k, v in row.replacements.items() if v != record["id"]
                    }
                    row.revision = uuid.uuid4().hex
                    row.save()

    def install(self, record: dict, archive: bytes):
        """Validate and extract a release without permitting an ID/version overwrite."""
        self.verify(record)
        if record.get("status") == "revoked":
            raise ModuleFailure("permission_denied", "Revoked module version")
        if (
            len(archive) > MAX_ARCHIVE
            or hashlib.sha256(archive).hexdigest() != record["sha256"]
        ):
            raise ModuleFailure("invalid_data", "Archive digest or size mismatch")
        try:
            package = zipfile.ZipFile(io.BytesIO(archive))
            entries = package.infolist()
            if (
                len(entries) > MAX_FILES
                or sum(e.file_size for e in entries) > MAX_EXPANDED
            ):
                raise ModuleFailure("invalid_data", "Package quota exceeded")
            names = set()
            for entry in entries:
                name = entry.filename.rstrip("/") if entry.is_dir() else entry.filename
                safe_path(name)
                mode = entry.external_attr >> 16
                if (
                    stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                    or entry.flag_bits & 1
                ):
                    raise ModuleFailure("invalid_data", "Unsupported archive entry")
                if name.casefold() in names:
                    raise ModuleFailure("invalid_data", "Duplicate package path")
                names.add(name.casefold())
                if not entry.is_dir() and Path(name).suffix.lower() not in {
                    ".js",
                    ".mjs",
                    ".css",
                    ".json",
                    ".map",
                    ".html",
                    ".txt",
                    ".md",
                    ".svg",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".gif",
                    ".avif",
                    ".ico",
                    ".pdf",
                    ".woff",
                    ".woff2",
                    ".ttf",
                    ".ogg",
                    ".mp3",
                    ".wav",
                    ".wasm",
                }:
                    raise ModuleFailure("invalid_data", "File type not allowed")
            manifest = json.loads(package.read("manifest.json"))
            self.contracts.validate("schemas/manifest.json", manifest)
            if (
                manifest["id"] != record["id"]
                or manifest["version"] != record["version"]
                or manifest["sdk"]["requires"] != record["sdk"]
                or not compatible(manifest["sdk"]["requires"])
            ):
                raise ModuleFailure(
                    "invalid_data", "Manifest does not match signed record"
                )
            entry = str(safe_path(manifest["entry"]))
            if (
                Path(entry).suffix not in (".js", ".mjs")
                or entry not in package.namelist()
            ):
                raise ModuleFailure("invalid_data", "Missing JavaScript entry")
            archives = self.directory / "archives"
            archives.mkdir(exist_ok=True)
            archived = archives / (record["sha256"] + ".zip")
            if not archived.exists():
                staged = archives / (uuid.uuid4().hex + ".tmp")
                staged.write_bytes(archive)
                staged.replace(archived)
            destination = (
                self.directory
                / "packages"
                / manifest["id"]
                / manifest["version"]
                / record["sha256"]
            )
            with transaction.atomic():
                old = (
                    Package.objects.select_for_update()
                    .filter(module_id=manifest["id"], version=manifest["version"])
                    .first()
                )
                if old:
                    if old.digest != record["sha256"] or old.revoked:
                        raise ModuleFailure("conflict")
                    self.verify_installed(old)
                    return manifest
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = Path(
                    tempfile.mkdtemp(prefix=".install-", dir=destination.parent)
                )
                try:
                    for file in entries:
                        if file.is_dir():
                            continue
                        target = temporary / file.filename
                        target.parent.mkdir(parents=True, exist_ok=True)
                        content = package.read(file)
                        if content.startswith(
                            (
                                b"MZ",
                                b"\x7fELF",
                                b"\xcf\xfa\xed\xfe",
                                b"\xfe\xed\xfa\xcf",
                            )
                        ):
                            raise ModuleFailure(
                                "invalid_data", "Native executable content rejected"
                            )
                        target.write_bytes(content)
                    if destination.exists():
                        shutil.rmtree(
                            destination
                        )  # orphan from interrupted installation
                    temporary.rename(destination)
                    Package.objects.create(
                        module_id=manifest["id"],
                        version=manifest["version"],
                        digest=record["sha256"],
                        manifest=manifest,
                        record=record,
                    )
                finally:
                    if temporary.exists():
                        shutil.rmtree(temporary)
            return manifest
        except (zipfile.BadZipFile, KeyError, ValueError, OSError) as error:
            if isinstance(error, ModuleFailure):
                raise
            raise ModuleFailure("invalid_data", "Invalid module archive") from None

    def verify_installed(self, row, asset=None):
        """Recheck the signed archive and extracted bytes, including on activation."""
        record = row.record
        self.verify(record)
        archive = self.directory / "archives" / (row.digest + ".zip")
        try:
            raw = archive.read_bytes()
            if hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ModuleFailure("invalid_data", "Installed archive changed")
            root = (
                self.directory / "packages" / row.module_id / row.version / row.digest
            )
            with zipfile.ZipFile(io.BytesIO(raw)) as package:
                names = {
                    entry.filename for entry in package.infolist() if not entry.is_dir()
                }
                if asset is not None and asset not in names:
                    raise ModuleFailure("not_found")
                if (
                    asset is None
                    and {
                        str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
                    }
                    != names
                ):
                    raise ModuleFailure("invalid_data", "Installed package changed")
                for name in [asset] if asset is not None else names:
                    path = root / name
                    if any(
                        p.is_symlink() for p in (path, *path.parents)
                    ) or path.read_bytes() != package.read(name):
                        raise ModuleFailure("invalid_data", "Installed package changed")
        except OSError, zipfile.BadZipFile, KeyError:
            raise ModuleFailure(
                "invalid_data", "Installed package unavailable"
            ) from None

    def state(self, table_id):
        """Describe the selected, non-revoked releases and their authenticated URLs."""
        row = ModuleSet.objects.filter(campaign_id=table_id).first()
        modules, revision, replacements = (
            (row.modules, row.revision, row.replacements) if row else ({}, "0", {})
        )
        descriptors = []
        for module_id, version in modules.items():
            installed = Package.objects.filter(
                module_id=module_id, version=version, revoked=False
            ).first()
            if installed:
                descriptors.append(
                    {
                        "id": module_id,
                        "version": version,
                        "entry": installed.manifest["entry"],
                        "baseUrl": f"/api/module-packages/{module_id}/{version}/{installed.digest}/",
                    }
                )
        return {
            "tableId": str(table_id),
            "moduleSetRevision": revision,
            "modules": descriptors,
            "replacements": replacements,
        }

    @transaction.atomic
    def configure(self, table_id, modules, replacements, expected_revision):
        """Atomically replace exact release selections if the caller's revision matches."""
        if (
            not isinstance(modules, dict)
            or not isinstance(replacements, dict)
            or len(modules) > 64
            or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in modules.items()
            )
            or any(
                k not in self.contracts.registry["domains"] or v not in modules
                for k, v in replacements.items()
            )
        ):
            raise ModuleFailure("invalid_data")
        from gravewright.campaigns.models import Campaign

        Campaign.objects.select_for_update().get(pk=table_id)
        row, _ = ModuleSet.objects.get_or_create(campaign_id=table_id)
        if row.revision != expected_revision:
            raise ModuleFailure("conflict")
        for module_id, version in modules.items():
            installed = Package.objects.filter(
                module_id=module_id, version=version, revoked=False
            ).first()
            if not installed:
                raise ModuleFailure("not_found")
            self.verify_installed(installed)
        row.modules, row.replacements, row.revision = (
            modules,
            replacements,
            uuid.uuid4().hex,
        )
        row.save()
        return self.state(table_id)

    def check(self, table_id, module_id, revision):
        """Reject a module handle from an inactive or superseded activation set."""
        state = self.state(table_id)
        if state["moduleSetRevision"] != revision or not any(
            m["id"] == module_id for m in state["modules"]
        ):
            raise ModuleFailure("stale_context")

    @transaction.atomic
    def storage(
        self,
        table_id,
        module_id,
        user_id,
        revision,
        action,
        key="",
        value=None,
        expected_revision=None,
    ):
        """Read or compare-and-swap JSON in one module/table/user namespace.

        An empty user ID selects shared table storage; views enforce GM-only writes.
        Missing values have no revision, so creation expects ``None``. Updates and
        deletes require the opaque revision returned by the preceding read/write.
        """
        if not isinstance(key, str) or len(key) > 240 or "\x00" in key:
            raise ModuleFailure("invalid_data")
        ModuleSet.objects.select_for_update().filter(campaign_id=table_id).first()
        self.check(table_id, module_id, revision)
        namespace = ModuleValue.objects.filter(
            campaign_id=table_id, module_id=module_id, user_key=str(user_id)
        )
        row = namespace.filter(key=key).first()
        if action == "get":
            return {"value": row.value, "revision": row.revision} if row else None
        if action == "list":
            return list(
                namespace.filter(key__startswith=key)
                .order_by("key")
                .values("key", "revision")
            )
        if action not in ("set", "delete") or not key:
            raise ModuleFailure("invalid_data")
        if expected_revision is not None and not isinstance(expected_revision, str):
            raise ModuleFailure("invalid_data")
        if action == "delete" and not isinstance(expected_revision, str):
            raise ModuleFailure("invalid_data")
        if (row.revision if row else None) != expected_revision:
            raise ModuleFailure("conflict")
        if action == "delete":
            row.delete()
            return None
        try:
            size = len(
                json.dumps(value, allow_nan=False, separators=(",", ":")).encode()
            )
            used = sum(
                len(json.dumps(v, separators=(",", ":")).encode())
                for v in namespace.exclude(key=key).values_list("value", flat=True)
            )
        except TypeError, ValueError, RecursionError:
            raise ModuleFailure("invalid_data") from None
        if size > MAX_VALUE or used + size > MAX_NAMESPACE:
            raise ModuleFailure("invalid_data")
        revision = uuid.uuid4().hex
        ModuleValue.objects.update_or_create(
            campaign_id=table_id,
            module_id=module_id,
            user_key=str(user_id),
            key=key,
            defaults={"value": value, "revision": revision},
        )
        return {"value": value, "revision": revision}


def host():
    """Build the package host from current settings and configured publisher keys."""
    from django.conf import settings

    keys = (
        json.loads(Path(settings.GRAVEWRIGHT_MARKETPLACE_KEYS_FILE).read_text())
        if settings.GRAVEWRIGHT_MARKETPLACE_KEYS_FILE
        else {}
    )
    return ModulePackages(Path(settings.MEDIA_ROOT) / "modules", keys)
