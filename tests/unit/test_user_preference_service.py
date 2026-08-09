from __future__ import annotations

from app.business.users.user_preference_service import DEFAULT_GAME_LAYOUT_MODE
from app.business.users.user_preference_service import DEFAULT_VISION_MODE
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


def test_vision_mode_defaults_to_cinematic(db):
    """Quem nunca abriu as configurações tem de continuar vendo o que já via."""
    user_id = seed_user()

    assert UserPreferenceService().get_vision_mode(user_id) == DEFAULT_VISION_MODE


def test_user_can_choose_the_classic_vision(db):
    user_id = seed_user()
    service = UserPreferenceService()

    result = service.set_vision_mode(user_id=user_id, vision_mode="classic")

    assert result.success
    assert service.get_vision_mode(user_id) == "classic"


def test_rejects_invalid_vision_mode(db):
    user_id = seed_user()
    service = UserPreferenceService()

    result = service.set_vision_mode(user_id=user_id, vision_mode="ultra")

    assert not result.success
    assert service.get_vision_mode(user_id) == DEFAULT_VISION_MODE


def test_the_two_preferences_do_not_overwrite_each_other(db):
    """São colunas da mesma linha, gravadas por upsert. Um upsert que montasse a
    linha inteira apagaria a preferência que não veio no formulário."""
    user_id = seed_user()
    service = UserPreferenceService()

    service.set_game_layout_mode(user_id=user_id, layout_mode="classic")
    service.set_vision_mode(user_id=user_id, vision_mode="classic")

    assert service.get_game_layout_mode(user_id) == "classic"
    assert service.get_vision_mode(user_id) == "classic"

    service.set_vision_mode(user_id=user_id, vision_mode="cinematic")

    assert service.get_game_layout_mode(user_id) == "classic", "layout sobreviveu"
    assert service.get_vision_mode(user_id) == "cinematic"
