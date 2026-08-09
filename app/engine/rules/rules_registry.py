"""Loads a system's declarative rule files from its package (§9).

Reads ``rules/formulas|derived|actions`` and ``mappings/tokens`` for an
installed system, resolving each path safely under the package dir. Files are
small; we read on demand rather than cache, so an updated package is picked up.
"""

from __future__ import annotations

import json

from app.engine.sdk import package_registry
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest import PackageManifest
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository


class SystemRulesService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()
        self.install = PackageInstallService()

    def _read_json(self, package_dir_name: str, relative: str) -> dict:
        if not relative:
            return {}
        base = package_registry.PACKAGES_DIR / package_dir_name
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return {}
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _record_and_manifest(self, system_id: str) -> tuple[dict, PackageManifest] | None:
        record = self.installed.get(system_id)
        if record is None:
            return None




        manifest = self.install.get_manifest(system_id)
        if manifest is None:
            return None
        return record, manifest

    def get_helpers(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        helpers = self._read_json(record["package_dir"], manifest.rules.get("formulas", "")).get(
            "helpers"
        )
        return helpers if isinstance(helpers, dict) else {}

    def get_derived(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        derived = self._read_json(record["package_dir"], manifest.rules.get("derived", "")).get(
            "derived"
        )
        return derived if isinstance(derived, dict) else {}

    def get_actions(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        actions = self._read_json(record["package_dir"], manifest.rules.get("actions", "")).get(
            "actions"
        )
        return actions if isinstance(actions, dict) else {}

    def get_action(self, system_id: str, action_id: str) -> dict | None:
        action = self.get_actions(system_id).get(action_id)
        return action if isinstance(action, dict) else None

    def get_validation(self, system_id: str, type_id: str) -> dict:
        """The ``{path: {min, max}}`` constraint map declared for an actor/item type."""
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        validation = self._read_json(
            record["package_dir"], manifest.rules.get("validation", "")
        ).get("validation")
        if not isinstance(validation, dict):
            return {}
        type_map = validation.get(type_id)
        return type_map if isinstance(type_map, dict) else {}

    def get_conditions(self, system_id: str) -> list[dict]:
        """The conditions a system declares, in the order it declares them.

        Each entry carries an ``id`` (the ``sheet.conditions.<id>`` flag it
        mirrors), a ``labelKey``, a ``category`` the effects HUD groups by, a
        ``kind`` the sheet colours by, and the ``modifiers`` the condition costs
        its owner. Malformed entries are dropped rather than raised: a ruleset is
        data, and one bad row must not cost the whole list.
        """
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return []
        record, manifest = pair
        declared = self._read_json(
            record["package_dir"], manifest.rules.get("conditions", "")
        ).get("conditions")
        if not isinstance(declared, list):
            return []
        out: list[dict] = []
        for entry in declared[:64]:
            if not isinstance(entry, dict):
                continue
            condition_id = str(entry.get("id") or "").strip()
            if not condition_id:
                continue
            kind = str(entry.get("kind") or "neutral")
            modifiers = entry.get("modifiers")
            out.append(
                {
                    "id": condition_id,
                    "labelKey": str(entry.get("labelKey") or ""),
                    "icon": str(entry.get("icon") or "") or None,
                    "kind": kind if kind in {"positive", "negative", "neutral"} else "neutral",
                    "category": str(entry.get("category") or "condition"),
                    "modifiers": [m for m in modifiers if isinstance(m, dict)][:16]
                    if isinstance(modifiers, list)
                    else [],
                }
            )
        return out

    def get_token_mappings(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        return self._read_json(record["package_dir"], manifest.mappings.get("tokens", ""))

    def get_combat_config(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}
        record, manifest = pair
        return self._read_json(record["package_dir"], manifest.rules.get("combat", ""))

    def get_chat_card_mappings(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}

        record, manifest = pair
        return self._read_json(
            record["package_dir"],
            manifest.mappings.get("chatCards", ""),
        )

    def get_roll_toast_mappings(self, system_id: str) -> dict:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return {}

        record, manifest = pair
        return self._read_json(
            record["package_dir"],
            manifest.mappings.get("rollToast", ""),
        )
