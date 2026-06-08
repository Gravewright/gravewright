from __future__ import annotations

from app.business.users.user_preference_service import DEFAULT_GAME_LAYOUT_MODE
from app.business.users.user_preference_service import UserPreferenceService
from tests.conftest import seed_user


def test_game_layout_mode_defaults_to_gravewright(db):
    user_id = seed_user()

    assert UserPreferenceService().get_game_layout_mode(user_id) == DEFAULT_GAME_LAYOUT_MODE


def test_user_can_update_game_layout_mode(db):
    user_id = seed_user()
    service = UserPreferenceService()

    result = service.set_game_layout_mode(user_id=user_id, layout_mode="classic")

    assert result.success
    assert service.get_game_layout_mode(user_id) == "classic"


def test_rejects_invalid_game_layout_mode(db):
    user_id = seed_user()
    service = UserPreferenceService()

    result = service.set_game_layout_mode(user_id=user_id, layout_mode="invalid")

    assert not result.success
    assert service.get_game_layout_mode(user_id) == DEFAULT_GAME_LAYOUT_MODE
