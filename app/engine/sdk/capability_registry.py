"""Canonical SDK capability registry.

``capabilities.json`` (next to this module) is the single source of truth for
SDK capabilities. The Python validator, the doctor, the frontend capability map,
and the generated docs all derive from — or are validated against — it.

Each capability declares ``status``, ``description``, ``surfaces`` and
``methods``. A separate ``forbidden`` block lists capabilities that are always
rejected. This module loads that file once and exposes typed views over it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name("capabilities.json")

VALID_STATUSES = frozenset({"stable", "forbidden"})
VALID_SURFACES = frozenset({"manifest", "backend", "frontend", "doctor"})


@dataclass(frozen=True)
class Capability:
    name: str
    status: str
    description: str
    surfaces: tuple[str, ...]
    methods: tuple[str, ...]

    @property
    def is_frontend(self) -> bool:
        return "frontend" in self.surfaces


@dataclass(frozen=True)
class CapabilityRegistry:
    capabilities: dict[str, Capability]
    forbidden: dict[str, str]  # name -> reason

    # --- allow/deny lists ------------------------------------------------------

    def known_names(self) -> frozenset[str]:
        return frozenset(self.capabilities)

    def forbidden_names(self) -> frozenset[str]:
        return frozenset(self.forbidden)

    # --- lookups ---------------------------------------------------------------

    def status_of(self, name: str) -> str | None:
        cap = self.capabilities.get(name)
        return cap.status if cap else None

    def names_with_status(self, status: str) -> frozenset[str]:
        return frozenset(n for n, c in self.capabilities.items() if c.status == status)

    # --- method gates ----------------------------------------------------------

    def method_to_capability(self) -> dict[str, str]:
        """Flatten ``capability -> methods`` into ``method -> capability``."""
        out: dict[str, str] = {}
        for cap in self.capabilities.values():
            for method in cap.methods:
                out[method] = cap.name
        return out


def _load(path: Path) -> CapabilityRegistry:
    data = json.loads(path.read_text(encoding="utf-8"))
    caps: dict[str, Capability] = {}
    for name, raw in data.get("capabilities", {}).items():
        caps[name] = Capability(
            name=name,
            status=str(raw.get("status", "")),
            description=str(raw.get("description", "")),
            surfaces=tuple(raw.get("surfaces", []) or []),
            methods=tuple(raw.get("methods", []) or []),
        )
    forbidden = {
        name: str(raw.get("reason", ""))
        for name, raw in data.get("forbidden", {}).items()
    }
    return CapabilityRegistry(capabilities=caps, forbidden=forbidden)


@lru_cache(maxsize=1)
def get_registry() -> CapabilityRegistry:
    return _load(REGISTRY_PATH)
