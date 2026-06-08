from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import config
from app.helpers.i18n import CATALOGS, get_supported_locale


SETTINGS_PATH = Path(config.data_dir) / "inside" / "settings.json"


@dataclass(frozen=True)
class InsideSettingsUpdate:
    app_name: str
    default_locale: str


@dataclass(frozen=True)
class PrivacySettingsUpdate:
    enabled: bool
    title: str
    content: str
    data_controller: str
    dpo_contact: str
    contact_email: str
    legal_basis: str
    retention_policy: str
    data_subject_rights: str


DEFAULT_PRIVACY = {
    "enabled": False,
    "title": "Política de Privacidade",
    "content": "",
    "data_controller": "",
    "dpo_contact": "",
    "contact_email": "",
    "legal_basis": "Consentimento, execução de contrato e legítimo interesse, conforme aplicável.",
    "retention_policy": "Os dados são mantidos pelo tempo necessário para operar o serviço e cumprir obrigações legais.",
    "data_subject_rights": "O titular pode solicitar acesso, correção, portabilidade, revogação de consentimento e exclusão de dados.",
    "updated_at": None,
}


class InsideSettingsService:
    def read(self) -> dict[str, Any]:
        data = self._read_file()
        app = data.get("app") if isinstance(data.get("app"), dict) else {}
        privacy = data.get("privacy") if isinstance(data.get("privacy"), dict) else {}

        default_locale = get_supported_locale(str(app.get("default_locale") or config.default_locale))
        return {
            "app": {
                "app_name": str(app.get("app_name") or config.app_name),
                "default_locale": default_locale,
                "supported_locales": sorted(CATALOGS.keys()),
            },
            "privacy": {
                **DEFAULT_PRIVACY,
                **privacy,
                "enabled": bool(privacy.get("enabled", DEFAULT_PRIVACY["enabled"])),
            },
        }

    def update_app(self, update: InsideSettingsUpdate) -> None:
        data = self._read_file()
        app = data.get("app") if isinstance(data.get("app"), dict) else {}
        privacy = data.get("privacy") if isinstance(data.get("privacy"), dict) else {}
        app_name = update.app_name.strip() or config.app_name
        data["app"] = {
            **app,
            "app_name": app_name[:80],
            "default_locale": get_supported_locale(update.default_locale),
        }
        data["privacy"] = privacy
        self._write_file(data)

    def update_privacy(self, update: PrivacySettingsUpdate) -> None:
        data = self._read_file()
        app = data.get("app") if isinstance(data.get("app"), dict) else {}
        data["app"] = app
        data["privacy"] = {
            "enabled": update.enabled,
            "title": update.title.strip()[:120] or DEFAULT_PRIVACY["title"],
            "content": update.content.strip(),
            "data_controller": update.data_controller.strip()[:160],
            "dpo_contact": update.dpo_contact.strip()[:160],
            "contact_email": update.contact_email.strip()[:160],
            "legal_basis": update.legal_basis.strip(),
            "retention_policy": update.retention_policy.strip(),
            "data_subject_rights": update.data_subject_rights.strip(),
            "updated_at": datetime.now(UTC).date().isoformat(),
        }
        self._write_file(data)

    def app_name(self) -> str:
        return str(self.read()["app"]["app_name"])

    def privacy_for_login(self) -> dict[str, Any]:
        privacy = dict(self.read()["privacy"])
        content_parts = [
            privacy.get("content", ""),
            privacy.get("legal_basis", ""),
            privacy.get("retention_policy", ""),
            privacy.get("data_subject_rights", ""),
        ]
        contacts = [privacy.get("data_controller", ""), privacy.get("dpo_contact", ""), privacy.get("contact_email", "")]
        contact_text = " · ".join(part for part in contacts if part)
        if contact_text:
            content_parts.append(contact_text)
        privacy["content"] = "\n\n".join(part for part in content_parts if part)
        privacy["enabled"] = bool(config.privacy_enabled or privacy.get("enabled"))
        return privacy

    def _read_file(self) -> dict[str, Any]:
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_file(self, data: dict[str, Any]) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = SETTINGS_PATH.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        tmp_path.replace(SETTINGS_PATH)
