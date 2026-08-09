"""Quem assina uma rolagem no chat.

Uma rolagem é do **personagem**, não da conta. Na mesa ninguém diz "o ricardo
tirou 18" — diz o nome do personagem. E o mestre fala como mestre, não pelo nome
dele.

A regra, nesta ordem:

1. **GM** (e o assistente) assina como ``GM``. O papel é o personagem dele.
2. **Jogador** assina com o nome do ator que ele possui.
3. Sem ator possuído (espectador, streamer, alguém que ainda não recebeu
   personagem), continua o nome da conta — é melhor do que uma rolagem anônima.

O projeto não tem um campo "personagem deste membro": a posse vive em
``actor_owners``, e um jogador pode possuir mais de um ator. Nesse caso vale o
**alterado mais recentemente**, que é o que ele está usando de fato — melhor
heurística do que ordem alfabética, que fixaria no mesmo personagem para sempre.
"""

from __future__ import annotations

from sqlalchemy import select

from app.persistence.database import engine_connect
from app.persistence.tables import actor_owners, actors_core

GM_SPEAKER = "GM"
_GM_ROLES = {"gm", "assistant_gm"}


class ChatSpeakerService:
    """Resolve o nome que assina uma mensagem de rolagem."""

    def speaker_name(self, *, campaign_id: str, user_id: str, role: str | None, fallback: str) -> str:
        if (role or "").lower() in _GM_ROLES:
            return GM_SPEAKER

        character = self.owned_character_name(campaign_id=campaign_id, user_id=user_id)
        return character or fallback

    def owned_character_name(self, *, campaign_id: str, user_id: str) -> str | None:
        if not campaign_id or not user_id:
            return None

        with engine_connect() as conn:
            row = conn.execute(
                select(actors_core.c.name)
                .select_from(
                    actors_core.join(actor_owners, actor_owners.c.actor_id == actors_core.c.id)
                )
                .where(actors_core.c.campaign_id == campaign_id)
                .where(actor_owners.c.user_id == user_id)
                .where(actors_core.c.status == "active")


                .order_by(actors_core.c.updated_at.desc(), actors_core.c.name.asc())
                .limit(1)
            ).first()

        return str(row[0]) if row and row[0] else None
