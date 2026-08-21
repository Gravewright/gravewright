"""Builds the render bundle for an actor sheet (Gravewright SDK, §8 + §19).

    bundle = { actor core summary, derived-applied data, Sheet IR layout,
               can_edit, version }

The frontend renderer (game-actor-sheets.js) interprets the layout, binds
fields to ``sheet.data.patch`` and buttons to ``sheet.action.execute``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.actors.actor_asset_urls import actor_image_url
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.rules.derived_field_service import apply_derived
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sdk.package_locale_service import PackageLocaleService
from app.engine.sheets.sheet_localizer import localize_layout
from app.engine.sheets.sheet_ir_validator import validate_sheet_ir
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


def action_dialogs(actions: dict, catalog: dict[str, str]) -> dict:
    """Localized roll dialogs, keyed by action id, for the actions that ask.

    Only the dialog travels: the formula stays on the server, where the roll is
    resolved. Sending it would invite a client to argue about the result.
    """
    if not isinstance(actions, dict):
        return {}
    out: dict = {}
    for action_id, action in actions.items():
        if not isinstance(action, dict):
            continue
        dialog = action.get("dialog")
        if not isinstance(dialog, dict) or dialog.get("enabled") is False:
            continue
        out[str(action_id)] = dialog
    return localize_layout(out, catalog) if out else {}


def bundle_to_dict(bundle: "ActorSheetBundle") -> dict:
    """The JSON an open sheet renders itself from.

    One implementation on purpose. There are two services that build a bundle -
    the actor's and the token instance's, and while each also serialised its
    own, the two drifted: the token copy silently lacked ``dialogs`` (so a roll
    opened no options when the sheet came from a token) and ``token_link_mode``
    (so edits to a *linked* token were written to a token-local override instead
    of the actor, and the sheet then stopped seeing anything added to the actor).
    """
    return {
        "actor": {
            "id": bundle.actor_id,
            "name": bundle.name,
            "type": bundle.type,
            "system_id": bundle.system_id,
            "token_id": bundle.token_id,
            "source_actor_id": bundle.source_actor_id,
            "token_link_mode": bundle.token_link_mode,
        },
        "version": bundle.version,
        "can_edit": bundle.can_edit,
        "layout": bundle.layout,
        "sheet": bundle.sheet,
        "dialogs": bundle.dialogs,
        "data": bundle.data,
        "portrait_url": bundle.portrait_url,
        "token_url": bundle.token_url,
        "summary": bundle.summary,
    }


@dataclass(frozen=True)
class ActorSheetBundle:
    actor_id: str
    campaign_id: str
    system_id: str
    name: str
    type: str
    version: int
    can_edit: bool
    layout: dict | None
    sheet: dict | None





    dialogs: dict
    data: dict
    portrait_url: str | None
    token_url: str | None
    summary: dict
    token_id: str | None = None
    source_actor_id: str | None = None
    token_link_mode: str | None = None


class ActorSheetService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.locales = PackageLocaleService()
        self.systems = PackageInstallService()
        self.rules = SystemRulesService()
        self.layouts = SystemLayoutService()
        self.projector = ActorTokenProjector()

    def build_bundle(
        self, *, actor_id: str, user_id: str, locale: str | None = None
    ) -> ActorSheetBundle | None:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        campaign_dict = dict(campaign)
        if not can_view_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
            return None

        system_id = actor["system_id"]
        envelope = self.storage.read_actor(
            system_id=system_id, campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        raw_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        layout, sheet, dialogs, data = self._compose(
            system_id=system_id, actor_type=actor["type"], name=actor["name"],
            raw_data=raw_data, locale=locale,
        )

        return ActorSheetBundle(
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=system_id,
            name=actor["name"],
            type=actor["type"],
            version=int(envelope.get("version", 1)),
            can_edit=can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id),
            layout=layout,
            sheet=sheet,
            dialogs=dialogs,
            data=data,
            portrait_url=actor_image_url(actor, "portrait"),
            token_url=actor_image_url(actor, "token"),
            summary=self.projector.project(actor),
            source_actor_id=actor_id,
        )

    def build_preview_bundle(
        self,
        *,
        campaign_id: str,
        system_id: str,
        actor_type: str,
        name: str,
        data: dict,
        preview_id: str,
        locale: str | None = None,
    ) -> ActorSheetBundle:
        """Ficha de uma entrada de compêndio, sem nada gravado.

        A entrada do pack já traz tipo, nome e dados; o que faltava para desenhar
        era o layout, os diálogos e os derivados, que saem do SISTEMA e não do
        ator persistido. Por isso o preview reusa exatamente o mesmo miolo -- não
        existe uma segunda ficha de leitura para manter em dia.
        """
        layout, sheet, dialogs, composed = self._compose(
            system_id=system_id, actor_type=actor_type, name=name,
            raw_data=data if isinstance(data, dict) else {}, locale=locale,
        )
        return ActorSheetBundle(
            actor_id=preview_id,
            campaign_id=campaign_id,
            system_id=system_id,
            name=name,
            type=actor_type,
            version=1,
            # Compêndio é fonte, não estado da mesa: nunca editável daqui.
            can_edit=False,
            layout=layout,
            sheet=sheet,
            dialogs=dialogs,
            data=composed,
            portrait_url=None,
            token_url=None,
            summary={},
            source_actor_id=None,
        )

    def _compose(
        self, *, system_id: str, actor_type: str, name: str, raw_data: dict, locale: str | None
    ) -> tuple[dict | None, dict | None, dict, dict]:
        layout: dict | None = None
        sheet: dict | None = None
        dialogs: dict = {}
        data = raw_data
        if self.systems.get_active_manifest(system_id) is not None:
            sheet = self.layouts.get_actor_html_sheet(system_id=system_id, actor_type=actor_type)

            if sheet is None:
                candidate = self.layouts.get_actor_sheet(
                    system_id=system_id,
                    actor_type=actor_type,
                    locale=locale,
                )
                if candidate is not None and not validate_sheet_ir(candidate):
                    layout = candidate
            from app.config import config

            dialogs = action_dialogs(
                self.rules.get_actions(system_id),
                self.locales.get_locale(system_id, locale or config.default_locale),
            )
            helpers = self.rules.get_helpers(system_id)
            derived = self.rules.get_derived(system_id)
            data = apply_derived(
                actor_type=actor_type,
                data=raw_data,
                derived_rules=derived,
                helpers=helpers,
                core={"name": name},
            )
            data = apply_stat_modifiers(data)

        return layout, sheet, dialogs, data

    def to_dict(self, bundle: ActorSheetBundle) -> dict:
        return bundle_to_dict(bundle)

    def get_member_role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
