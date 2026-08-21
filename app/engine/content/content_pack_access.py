"""Quem pode ler e quem pode importar cada pack de compêndio.

Regra única do produto, para os quatro pontos que antes perguntavam
``member_role == "gm"`` cada um por conta própria: o corte da lista de pacotes na
página, o painel, a busca global e os endpoints que servem os packs.

Os níveis são os mesmos de ator, item e diário -- ``none`` / ``read`` / ``owner``
--, e o sentido de ``owner`` é o mesmo: pode alterar o estado do mundo. Num pack
isso quer dizer importar para a campanha, porque o pack em si vem do módulo
instalado e ninguém o edita pela mesa.
"""
from __future__ import annotations

from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.content_pack_ownership_repository import (
    ContentPackOwnershipRepository,
)

NONE = "none"
READ = "read"
OWNER = "owner"

LEVELS = (NONE, READ, OWNER)
_RANK = {NONE: 0, READ: 1, OWNER: 2}


def normalized_level(value: object) -> str:
    text = str(value or NONE)
    return text if text in LEVELS else NONE


class ContentPackAccessService:
    def __init__(
        self,
        ownership: ContentPackOwnershipRepository | None = None,
        campaigns: CampaignRepository | None = None,
    ) -> None:
        self.ownership = ownership or ContentPackOwnershipRepository()
        self.campaigns = campaigns or CampaignRepository()

    def role_of(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)

    def level_for(
        self, *, campaign_id: str, package_id: str, pack_id: str, user_id: str
    ) -> str:
        role = self.role_of(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return NONE
        # O mestre é dono de tudo, sem linha na tabela: ele é quem concede.
        if role == PlayerRole.GM.value:
            return OWNER
        # O streamer observa a mesa; compêndio é material de quem joga, e ele
        # não joga. Fora, por decisão de produto, não por falta de linha.
        if role == PlayerRole.STREAMER.value:
            return NONE
        row = self.ownership.get(
            campaign_id=campaign_id, package_id=package_id, pack_id=pack_id, role=role
        )
        return normalized_level(row["level"]) if row else NONE

    def can_read(self, *, campaign_id: str, package_id: str, pack_id: str, user_id: str) -> bool:
        return _RANK[
            self.level_for(
                campaign_id=campaign_id, package_id=package_id, pack_id=pack_id, user_id=user_id
            )
        ] >= _RANK[READ]

    def can_import(self, *, campaign_id: str, package_id: str, pack_id: str, user_id: str) -> bool:
        return (
            self.level_for(
                campaign_id=campaign_id, package_id=package_id, pack_id=pack_id, user_id=user_id
            )
            == OWNER
        )

    def reaches_any_pack(self, *, campaign_id: str, user_id: str) -> bool:
        """O compêndio vale uma aba para este usuário?

        Sem isto o jogador veria uma aba que nunca tem nada dentro.
        """
        role = self.role_of(campaign_id=campaign_id, user_id=user_id)
        if role is None or role == PlayerRole.STREAMER.value:
            return False
        if role == PlayerRole.GM.value:
            return True
        return any(
            normalized_level(row["level"]) != NONE
            for row in self.ownership.list_for_campaign(campaign_id=campaign_id)
            if row["role"] == role
        )

    def set_level(
        self, *, campaign_id: str, package_id: str, pack_id: str, role: str, level: str, user_id: str
    ) -> bool:
        """Só o mestre concede, e nunca sobre o próprio papel."""
        if self.role_of(campaign_id=campaign_id, user_id=user_id) != PlayerRole.GM.value:
            return False
        if role in {PlayerRole.GM.value, PlayerRole.STREAMER.value}:
            return False
        self.ownership.set_level(
            campaign_id=campaign_id,
            package_id=package_id,
            pack_id=pack_id,
            role=role,
            level=normalized_level(level),
        )
        return True

    def levels_for_campaign(self, *, campaign_id: str) -> dict[tuple[str, str, str], str]:
        """Mapa ``(package_id, pack_id, role) -> level``, para pintar o diálogo."""
        return {
            (row["package_id"], row["pack_id"], row["role"]): normalized_level(row["level"])
            for row in self.ownership.list_for_campaign(campaign_id=campaign_id)
        }
