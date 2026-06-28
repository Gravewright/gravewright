from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.engine.decks.card_service import CardService
from app.engine.decks.cards import CardFaceState
from app.engine.decks.cards import DrawDestination
from app.engine.decks.cards import DrawMode
from app.engine.decks.cards import PileKind
from app.persistence.repositories.card_repository import CardRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_scene
from tests.conftest import seed_user


def _create_instantiated_deck(campaign_id: str, gm_id: str, *, quantity: int = 2) -> str:
    service = CardService()
    created = service.create_deck_definition(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Test Deck",
        description=None,
        cards=[
            {
                "name": f"Card {index}",
                "front_asset_id": f"front-{index}",
                "quantity": 1,
            }
            for index in range(quantity)
        ],
    )
    assert created.success, created.error_key
    instantiated = service.instantiate_deck(
        campaign_id=campaign_id,
        user_id=gm_id,
        deck_definition_id=created.payload["deck"]["id"],
    )
    assert instantiated.success, instantiated.error_key
    return instantiated.payload["deck"]["id"]


def test_create_deck_definition_requires_front_asset(db):
    gm_id = seed_user(name="GM", email="cards-missing-front@test.com")
    campaign_id = seed_campaign(gm_id)

    result = CardService().create_deck_definition(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Broken Deck",
        description=None,
        cards=[{"name": "No Front"}],
    )

    assert not result.success
    assert result.error_key == "game.cards.errors.missing_front_asset"


def test_create_deck_definition_accepts_schema_front_alias(db):
    gm_id = seed_user(name="GM", email="cards-front-alias@test.com")
    campaign_id = seed_campaign(gm_id)

    result = CardService().create_deck_definition(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Schema Deck",
        description=None,
        cards=[{"name": "Ace", "front": "front-from-schema"}],
    )

    assert result.success, result.error_key
    definitions = CardRepository().list_card_definitions(deck_definition_id=result.payload["deck"]["id"])
    assert definitions[0]["front_asset_id"] == "front-from-schema"


def test_draw_to_hand_returns_front_to_owner(db):
    gm_id = seed_user(name="GM", email="cards-hand-front@test.com")
    campaign_id = seed_campaign(gm_id)
    deck_instance_id = _create_instantiated_deck(campaign_id, gm_id, quantity=1)

    result = CardService().draw(
        campaign_id=campaign_id,
        user_id=gm_id,
        deck_instance_id=deck_instance_id,
        count=1,
        destination=DrawDestination.HAND,
    )

    assert result.success, result.error_key
    assert result.payload["cards"][0]["front_asset_id"] == "front-0"
    assert result.payload["cards"][0]["face_state"] == "face_down"
    assert result.payload["cards"][0]["visibility"] == "owner_only"


def test_get_state_reports_draw_count(db):
    gm_id = seed_user(name="GM", email="cards-draw-count@test.com")
    campaign_id = seed_campaign(gm_id)
    deck_instance_id = _create_instantiated_deck(campaign_id, gm_id, quantity=2)

    before = CardService().get_state(campaign_id=campaign_id, user_id=gm_id)
    assert before.success, before.error_key
    assert before.payload["decks"][0]["id"] == deck_instance_id
    assert before.payload["decks"][0]["draw_count"] == 2

    drawn = CardService().draw(
        campaign_id=campaign_id,
        user_id=gm_id,
        deck_instance_id=deck_instance_id,
        count=1,
        destination=DrawDestination.HAND,
    )
    assert drawn.success, drawn.error_key

    after = CardService().get_state(campaign_id=campaign_id, user_id=gm_id)
    assert after.success, after.error_key
    assert after.payload["decks"][0]["draw_count"] == 1


def test_concurrent_draws_do_not_duplicate_card_ids(db):
    gm_id = seed_user(name="GM", email="cards-concurrent@test.com")
    campaign_id = seed_campaign(gm_id)
    deck_instance_id = _create_instantiated_deck(campaign_id, gm_id, quantity=2)

    def draw_one() -> tuple[bool, str | None]:
        result = CardService().draw(
            campaign_id=campaign_id,
            user_id=gm_id,
            deck_instance_id=deck_instance_id,
            count=1,
            destination=DrawDestination.HAND,
            mode=DrawMode.TOP,
        )
        if not result.success:
            return False, result.error_key
        return True, result.payload["cards"][0]["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: draw_one(), range(2)))

    assert [success for success, _ in results] == [True, True]
    drawn_ids = [card_id for _success, card_id in results]
    assert len(set(drawn_ids)) == 2
    draw_pile = CardRepository().find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DRAW)
    assert draw_pile is not None
    assert CardRepository().get_pile_order(draw_pile["id"]) == []


def test_play_card_to_scene_update_flip_and_discard(db):
    gm_id = seed_user(name="GM", email="cards-scene@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    deck_instance_id = _create_instantiated_deck(campaign_id, gm_id, quantity=1)
    service = CardService()
    drawn = service.draw(
        campaign_id=campaign_id,
        user_id=gm_id,
        deck_instance_id=deck_instance_id,
        count=1,
        destination=DrawDestination.HAND,
    )
    assert drawn.success, drawn.error_key
    card_id = drawn.payload["cards"][0]["id"]
    hand_pile_id = drawn.payload["target_pile_id"]

    played = service.play_to_scene(
        campaign_id=campaign_id,
        user_id=gm_id,
        card_id=card_id,
        scene_id=scene["id"],
        x=120,
        y=180,
        reveal=True,
    )

    assert played.success, played.error_key
    placement = played.payload["placement"]
    assert placement["scene_id"] == scene["id"]
    assert placement["x"] == 120
    assert played.payload["card"]["front_asset_id"] == "front-0"
    assert CardRepository().get_pile_order(hand_pile_id) == []
    card_on_scene = CardRepository().get_card(card_id)
    assert card_on_scene["current_pile_id"] is None
    assert card_on_scene["current_scene_id"] == scene["id"]

    updated = service.update_scene_placement(
        campaign_id=campaign_id,
        user_id=gm_id,
        placement_id=placement["id"],
        x=200,
        y=240,
        rotation=15,
        face_state=CardFaceState.FACE_DOWN,
    )

    assert updated.success, updated.error_key
    assert updated.payload["placement"]["x"] == 200
    assert updated.payload["placement"]["face_state"] == "face_down"
    state = service.get_state(campaign_id=campaign_id, user_id=gm_id)
    assert state.success
    assert state.payload["scene_placements"][0]["id"] == placement["id"]
    assert state.payload["cards"][0]["back_asset_id"] is None

    discarded = service.discard_scene_placement(
        campaign_id=campaign_id,
        user_id=gm_id,
        placement_id=placement["id"],
    )

    assert discarded.success, discarded.error_key
    discard = CardRepository().find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DISCARD)
    assert discard is not None
    assert CardRepository().get_pile_order(discard["id"]) == [card_id]
    assert CardRepository().get_scene_card_placement(placement["id"]) is None
