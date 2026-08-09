"""Anúncio de mudança de acesso a um recurso da campanha.

Trocar o dono de um ator/item/diário e conceder acesso pelo modal de permissões
mudam a mesma coisa — quem enxerga o recurso — então precisam anunciar o mesmo
evento, com o mesmo formato. Antes só o modal anunciava: a troca de dono era
silenciosa, e o jogador que ganhava um ator não via nada aparecer até recarregar.

Manter o mapa aqui evita que os dois caminhos divirjam.
"""

from __future__ import annotations

from app.contracts.transport import RealtimeGatewayContract
from app.realtime.events import TransportEvent


_RESOURCE_EVENTS = {
    "actor": (TransportEvent.ACTOR_UPDATED, "actor_id"),
    "item": (TransportEvent.ITEM_UPDATED, "item_id"),
    "journal": (TransportEvent.JOURNAL_ACCESS_CHANGED, "journal_id"),
}


async def announce_resource_tree_change(
    *,
    resource_type: str,
    campaign_id: str | None,
    transport: RealtimeGatewayContract | None,
) -> bool:
    """Avisa que a árvore do painel mudou (pasta criada, renomeada, movida).

    O jogador enxerga uma pasta quando ela contém algo dele, então curadoria do
    GM muda o que ele vê. Os painéis recarregam por sala, então o evento não
    precisa carregar o id do recurso — só a sala.
    """
    entry = _RESOURCE_EVENTS.get(resource_type)
    if entry is None or not campaign_id or transport is None:
        return False

    event, _id_field = entry
    await transport.to_room(
        room_id=campaign_id,
        event=event,
        payload={"room_id": campaign_id},
    )
    return True


async def announce_resource_access_change(
    *,
    resource_type: str,
    resource_id: str,
    campaign_id: str | None,
    updated_by: str,
    transport: RealtimeGatewayContract | None,
) -> bool:
    """Avisa a sala que mudou quem enxerga o recurso. Devolve se anunciou."""
    entry = _RESOURCE_EVENTS.get(resource_type)
    if entry is None or not campaign_id or transport is None:
        return False

    event, id_field = entry
    await transport.to_room(
        room_id=campaign_id,
        event=event,
        payload={
            "room_id": campaign_id,
            id_field: resource_id,
            "updated_by": updated_by,
        },
    )
    return True
