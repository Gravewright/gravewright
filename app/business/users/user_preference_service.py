from __future__ import annotations

from dataclasses import dataclass

from app.persistence.repositories.user_preference_repository import UserPreferenceRepository


DEFAULT_GAME_LAYOUT_MODE = "gravewright"
GAME_LAYOUT_MODES = {DEFAULT_GAME_LAYOUT_MODE, "classic"}



DEFAULT_VISION_MODE = "cinematic"
VISION_MODES = {DEFAULT_VISION_MODE, "classic"}
DEFAULT_PING_COLOR = "#f2c679"


@dataclass(frozen=True)
class UserPreferenceResult:
    success: bool
    layout_mode: str = DEFAULT_GAME_LAYOUT_MODE
    error_key: str | None = None


@dataclass(frozen=True)
class VisionModeResult:
    success: bool
    vision_mode: str = DEFAULT_VISION_MODE
    error_key: str | None = None


@dataclass(frozen=True)
class PingColorResult:
    success: bool
    ping_color: str = DEFAULT_PING_COLOR
    error_key: str | None = None


class UserPreferenceService:
    def __init__(self) -> None:
        self.preferences = UserPreferenceRepository()

    def get_game_layout_mode(self, user_id: str) -> str:
        layout_mode = self.preferences.get_game_layout_mode(user_id)

        if layout_mode in GAME_LAYOUT_MODES:
            return layout_mode

        return DEFAULT_GAME_LAYOUT_MODE

    def set_game_layout_mode(self, *, user_id: str, layout_mode: str) -> UserPreferenceResult:
        normalized_mode = layout_mode.strip().lower()

        if normalized_mode not in GAME_LAYOUT_MODES:
            return UserPreferenceResult(
                success=False,
                error_key="game.settings.errors.invalid_layout_mode",
            )

        self.preferences.set_game_layout_mode(
            user_id=user_id,
            layout_mode=normalized_mode,
        )

        return UserPreferenceResult(success=True, layout_mode=normalized_mode)

    def get_vision_mode(self, user_id: str) -> str:
        vision_mode = self.preferences.get_vision_mode(user_id)

        if vision_mode in VISION_MODES:
            return vision_mode

        return DEFAULT_VISION_MODE

    def set_vision_mode(self, *, user_id: str, vision_mode: str) -> VisionModeResult:
        normalized_mode = vision_mode.strip().lower()

        if normalized_mode not in VISION_MODES:
            return VisionModeResult(
                success=False,
                error_key="game.settings.errors.invalid_vision_mode",
            )

        self.preferences.set_vision_mode(user_id=user_id, vision_mode=normalized_mode)

        return VisionModeResult(success=True, vision_mode=normalized_mode)

    def get_ping_color(self, user_id: str) -> str:
        value = (self.preferences.get_ping_color(user_id) or "").strip().lower()
        return value if self._valid_ping_color(value) else DEFAULT_PING_COLOR

    def set_ping_color(self, *, user_id: str, ping_color: str) -> PingColorResult:
        normalized = (ping_color or "").strip().lower()
        if not self._valid_ping_color(normalized):
            return PingColorResult(success=False, error_key="game.settings.errors.invalid_ping_color")
        self.preferences.set_ping_color(user_id=user_id, ping_color=normalized)
        return PingColorResult(success=True, ping_color=normalized)

    @staticmethod
    def _valid_ping_color(value: str) -> bool:
        return len(value) == 7 and value.startswith("#") and all(
            character in "0123456789abcdef" for character in value[1:]
        )
