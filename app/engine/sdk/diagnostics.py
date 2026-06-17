"""SDK diagnostics contract — the common shape for errors, findings and results.

This module is the single, machine-readable contract every SDK service speaks:

* :class:`SdkError` — one problem, identified by a stable ``code``.
* :class:`SdkActionResult` — the outcome of an install/enable/activate-style
  action, carrying an optional error and any warnings.
* :class:`DoctorFinding` — one health-audit observation with a ``severity``.

SDK endpoints return the structured ``code`` (also surfaced as ``error_key`` at
the HTTP boundary). See ``docs/sdk/diagnostics.md`` for the full policy.

Codes are lowercase, dot-separated identifiers under a small set of namespaces
(``sdk.manifest.*``, ``sdk.capabilities.*``, ``sdk.storage.*`` …). They are part
of the public contract: tests assert on ``code`` and ``details``, never on the
human-readable ``message``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

# --- code convention -----------------------------------------------------------

# A code is one or more lowercase/digit segments separated by dots, e.g.
# ``sdk.storage.sqlite.query_missing``. The leading segment is always ``sdk``.
CODE_PATTERN = re.compile(r"^sdk(\.[a-z0-9]+(_[a-z0-9]+)*)+$")

#: Public namespaces a code may live under. Kept explicit so a typo'd namespace
#: is caught by :func:`is_known_namespace` rather than silently accepted.
CODE_NAMESPACES: frozenset[str] = frozenset(
    {
        "sdk.manifest",
        "sdk.compatibility",
        "sdk.capabilities",
        "sdk.paths",
        "sdk.dependencies",
        "sdk.conflicts",
        "sdk.settings",
        "sdk.assets",
        "sdk.content",
        "sdk.locale",
        "sdk.frontend",
        "sdk.interop",
        "sdk.persistence",
        "sdk.storage",
    }
)

#: The initial code catalogue from the stability plan (Phase 1). Services may
#: emit codes beyond this set, but every code here is guaranteed stable.
SDK_ERROR_CODES: frozenset[str] = frozenset(
    {
        "sdk.manifest.missing",
        "sdk.manifest.unreadable",
        "sdk.manifest.invalid",
        "sdk.manifest.id_mismatch",
        "sdk.manifest.kind_root_mismatch",
        "sdk.manifest.snapshot_stale",
        "sdk.compatibility.version_too_low",
        "sdk.compatibility.version_too_high",
        "sdk.compatibility.unverified",
        "sdk.capabilities.unknown",
        "sdk.capabilities.forbidden",
        "sdk.capabilities.deprecated",
        "sdk.paths.unsafe",
        "sdk.dependencies.missing",
        "sdk.dependencies.disabled",
        "sdk.dependencies.active_dependents",
        "sdk.conflicts.active",
        "sdk.settings.invalid_value",
        "sdk.persistence.migration_required",
        "sdk.persistence.manifest_hash_mismatch",
        "sdk.persistence.validation_status_invalid",
        "sdk.frontend.capability_map_mismatch",
        "sdk.interop.namespace_forbidden",
        "sdk.storage.capability_missing",
        "sdk.storage.scope_forbidden",
        "sdk.storage.path_forbidden",
        "sdk.storage.sqlite.query_missing",
        "sdk.storage.sqlite.query_invalid",
        "sdk.storage.sqlite.param_invalid",
        "sdk.storage.sqlite.migration_failed",
    }
)


def is_machine_readable_code(code: str) -> bool:
    """A code is machine-readable when it matches the strict identifier shape."""
    return bool(CODE_PATTERN.match(code))


def is_known_namespace(code: str) -> bool:
    """True when ``code`` lives under one of the declared public namespaces."""
    return any(
        code == namespace or code.startswith(f"{namespace}.")
        for namespace in CODE_NAMESPACES
    )


# --- structured types ----------------------------------------------------------

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class SdkError:
    """One SDK problem, identified by a stable machine-readable ``code``."""

    code: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    package_id: str | None = None
    campaign_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            data["details"] = dict(self.details)
        if self.package_id is not None:
            data["package_id"] = self.package_id
        if self.campaign_id is not None:
            data["campaign_id"] = self.campaign_id
        return data


@dataclass(frozen=True)
class SdkActionResult:
    """Outcome of an SDK action (install/enable/activate/...)."""

    success: bool
    package_id: str | None = None
    campaign_id: str | None = None
    error: SdkError | None = None
    warnings: tuple[SdkError, ...] = ()

    @classmethod
    def ok(
        cls,
        *,
        package_id: str | None = None,
        campaign_id: str | None = None,
        warnings: tuple[SdkError, ...] = (),
    ) -> SdkActionResult:
        return cls(
            success=True,
            package_id=package_id,
            campaign_id=campaign_id,
            warnings=warnings,
        )

    @classmethod
    def fail(
        cls,
        error: SdkError,
        *,
        warnings: tuple[SdkError, ...] = (),
    ) -> SdkActionResult:
        return cls(
            success=False,
            package_id=error.package_id,
            campaign_id=error.campaign_id,
            error=error,
            warnings=warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"success": self.success}
        if self.package_id is not None:
            data["package_id"] = self.package_id
        if self.campaign_id is not None:
            data["campaign_id"] = self.campaign_id
        if self.error is not None:
            data["error"] = self.error.to_dict()
        if self.warnings:
            data["warnings"] = [w.to_dict() for w in self.warnings]
        return data


@dataclass(frozen=True)
class DoctorFinding:
    """One observation from a package health audit.

    The canonical finding shape for the strict doctor (Phase 9). It carries a
    ``severity`` alongside the stable ``code`` so the CLI/UI can rank findings
    without parsing the human-readable ``message``.
    """

    code: str
    severity: Severity
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    package_id: str | None = None
    campaign_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.details:
            data["details"] = dict(self.details)
        if self.package_id is not None:
            data["package_id"] = self.package_id
        if self.campaign_id is not None:
            data["campaign_id"] = self.campaign_id
        return data


