from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect

from app.business.inside_settings_service import InsideSettingsService
from app.business.inside_settings_service import InsideSettingsUpdate
from app.business.inside_settings_service import PrivacySettingsUpdate
from app.domain.roles import SystemRole
from app.engine.sdk.marketplace_service import MarketplaceService
from app.helpers.auth import require_user
from app.helpers.i18n import get_supported_locale
from app.persistence.rows import Row


@dataclass
class InsideSettingsForm:
    app_name: str = ""
    default_locale: str = "en"
    core_channel: str | None = None
    packages_channel: str | None = None
    channels_linked: bool = False


@dataclass
class PrivacySettingsForm:
    enabled: bool = False
    title: str = ""
    content: str = ""
    data_controller: str = ""
    dpo_contact: str = ""
    contact_email: str = ""
    legal_basis: str = ""
    retention_policy: str = ""
    data_subject_rights: str = ""


def _redirect(path: str) -> Redirect:
    return Redirect(path=path)


def _owner_required(current_user: Row) -> bool:
    return str(current_user["system_role"]) == SystemRole.OWNER.value


@post("/inside/settings", guards=[require_user])
async def update_inside_settings(
    current_user: Row,
    data: Annotated[InsideSettingsForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _owner_required(current_user):
        return _redirect("/inside?settings_error_key=inside.admin.errors.not_owner")

    locale = get_supported_locale(data.default_locale)
    settings_service = InsideSettingsService()
    current = settings_service.read()["updates"]
    marketplace = MarketplaceService().catalog_with_automatic_refresh()
    core_entry = marketplace.get("core") if isinstance(marketplace.get("core"), dict) else {}
    published_core = set(core_entry.get("availableChannels", []))
    published_packages = set(marketplace.get("availablePackageChannels", []))
    core_channel = data.core_channel if data.core_channel in published_core else current["core_channel"]
    packages_channel = (
        data.packages_channel
        if data.packages_channel in published_packages
        else current["packages_channel"]
    )
    settings_service.update_app(
        InsideSettingsUpdate(
            app_name=data.app_name,
            default_locale=locale,
            core_channel=core_channel,
            packages_channel=packages_channel,
            channels_linked=data.channels_linked,
        )
    )
    response = _redirect("/inside?settings_message_key=inside.settings.messages.saved")
    response.set_cookie(
        key="gravewright_locale",
        value=locale,
        path="/",
        samesite="lax",
    )
    return response


@post("/inside/privacy", guards=[require_user])
async def update_privacy_settings(
    current_user: Row,
    data: Annotated[PrivacySettingsForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _owner_required(current_user):
        return _redirect("/inside?privacy_error_key=inside.admin.errors.not_owner")

    InsideSettingsService().update_privacy(
        PrivacySettingsUpdate(
            enabled=data.enabled,
            title=data.title,
            content=data.content,
            data_controller=data.data_controller,
            dpo_contact=data.dpo_contact,
            contact_email=data.contact_email,
            legal_basis=data.legal_basis,
            retention_policy=data.retention_policy,
            data_subject_rights=data.data_subject_rights,
        )
    )
    return _redirect("/inside?privacy_message_key=inside.privacy.messages.saved")
