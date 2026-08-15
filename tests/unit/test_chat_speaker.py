"""Uma rolagem no chat sai pelo personagem, não pela conta.

Na mesa ninguém diz "o ricardo tirou 18": diz o nome do personagem. E o mestre
fala como mestre. A ficha já seguia essa regra (``actor_name or author_name``);
o que faltava era o ``/roll`` digitado ou vindo da bandeja.

Mensagem de **texto** continua saindo pelo nome de quem escreveu: ali quem fala é
a pessoa, não o personagem.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import update

from app.engine.chat.chat_speaker import GM_SPEAKER, ChatSpeakerService
from app.persistence.database import engine_begin
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.tables import actors_core
from tests.conftest import seed_campaign, seed_member, seed_user


@pytest.fixture
def speakers() -> ChatSpeakerService:
    return ChatSpeakerService()


def _actor(campaign_id: str, creator: str, name: str, owner: str | None = None) -> str:
    return ActorRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        actor_type="character",
        name=name,
        created_by_user_id=creator,
        owner_user_ids=[owner] if owner else None,
    )


def _touch(actor_id: str, when: int) -> None:
    """Mexe no ``updated_at`` para o desempate ficar determinístico no teste."""
    with engine_begin() as conn:
        conn.execute(
            update(actors_core).where(actors_core.c.id == actor_id).values(updated_at=when)
        )


def test_the_gm_signs_as_gm(speakers):
    gm = seed_user(name="Ricardo")
    campaign_id = seed_campaign(gm)

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=gm, role="gm", fallback="Ricardo"
    ) == GM_SPEAKER


def test_the_assistant_gm_signs_as_gm_too(speakers):
    """Quem mestra a mesa fala como mesa, independentemente do rótulo interno."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    assistente = seed_user(name="Ana")
    seed_member(campaign_id, assistente, "assistant_gm")

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=assistente, role="assistant_gm", fallback="Ana"
    ) == GM_SPEAKER


def test_a_player_signs_with_the_character_they_own(speakers):
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    jogador = seed_user(name="ricardo")
    seed_member(campaign_id, jogador, "player")
    _actor(campaign_id, gm, "Aria Corvo", owner=jogador)

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=jogador, role="player", fallback="ricardo"
    ) == "Aria Corvo"


def test_with_several_characters_the_most_recently_touched_wins(speakers):
    """O projeto não tem "personagem deste membro". Com mais de um, vale o que a
    pessoa está usando agora: ordem alfabética fixaria no mesmo para sempre."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    jogador = seed_user(name="ricardo")
    seed_member(campaign_id, jogador, "player")

    antigo = _actor(campaign_id, gm, "Aria Corvo", owner=jogador)
    recente = _actor(campaign_id, gm, "Bruno Lupo", owner=jogador)
    agora = int(time.time())
    _touch(antigo, agora - 3600)
    _touch(recente, agora)

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=jogador, role="player", fallback="ricardo"
    ) == "Bruno Lupo"


def test_a_player_without_a_character_keeps_their_own_name(speakers):
    """Espectador, streamer ou quem ainda não recebeu personagem. Uma rolagem
    anônima seria pior do que uma assinada pela conta."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    jogador = seed_user(name="ricardo")
    seed_member(campaign_id, jogador, "player")

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=jogador, role="player", fallback="ricardo"
    ) == "ricardo"


def test_a_character_of_another_player_is_not_borrowed(speakers):
    """Possuir é o critério: o ator de outra pessoa não assina a minha rolagem."""
    gm = seed_user(name="GM")
    campaign_id = seed_campaign(gm)
    dono = seed_user(name="ana")
    outro = seed_user(name="ricardo")
    seed_member(campaign_id, dono, "player")
    seed_member(campaign_id, outro, "player")
    _actor(campaign_id, gm, "Aria Corvo", owner=dono)

    assert speakers.speaker_name(
        campaign_id=campaign_id, user_id=outro, role="player", fallback="ricardo"
    ) == "ricardo"


def test_only_rolls_change_the_signature():
    """Mensagem de texto continua pelo nome da conta, e a consulta ao banco só
    acontece quando é rolagem."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2] / "app/engine/chat/chat_service.py"
    ).read_text(encoding="utf-8")

    bloco = source.split("e_rolagem = (", 1)[1].split("base: dict", 1)[0]
    assert '"/gmroll"' in bloco and '"/roll", "/r"' in bloco, "os dois comandos contam"
    assert "if e_rolagem:" in bloco, "sem rolagem, nem consulta o banco"
    assert "fallback=sender_name" in bloco
