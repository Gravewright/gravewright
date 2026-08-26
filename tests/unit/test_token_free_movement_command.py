from app.engine.tokens.token_service import TokenResult
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.token_command_handler import TokenCommandHandler


class RecordingTokenService:
    def __init__(self):
        self.move_args = None

    async def move(self, **kwargs):
        self.move_args = kwargs
        return TokenResult(success=True, token={"version": 2})


async def test_token_move_accepts_fractional_coordinates():
    service = RecordingTokenService()
    result = await TokenCommandHandler(service=service).handle(
        {
            "id": "move-1",
            "command": "token.move",
            "room_id": "room-1",
            "payload": {
                "scene_id": "scene-1",
                "token_id": "token-1",
                "grid_x": 2.375,
                "grid_y": 4.625,
                "movement_path": [{"grid_x": 2.375, "grid_y": 4.625}],
            },
        },
        context=ClientCommandContext(user_id="user-1", room_ids=("room-1",)),
    )

    assert result.handled
    assert service.move_args["grid_x"] == 2.375
    assert service.move_args["grid_y"] == 4.625
