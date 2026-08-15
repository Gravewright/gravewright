from __future__ import annotations

from enum import StrEnum


class ClientCommand(StrEnum):
    PING = "ping"
    BOARD_PING = "board.ping"
    BOARD_AREA_MARKER_UPSERT = "board.area_marker.upsert"
    BOARD_AREA_MARKER_DELETE = "board.area_marker.delete"
    BOARD_AREA_MARKER_CLEAR = "board.area_marker.clear"
    BOARD_DRAW_UPSERT = "board.draw.upsert"
    BOARD_DRAW_CLEAR = "board.draw.clear"
    BOARD_MEASURE_FLASH = "board.measure.flash"
    BOARD_MEASURE_DELETE = "board.measure.delete"
    BOARD_MEASURE_CLEAR = "board.measure.clear"
    VIEWPORT_SUBSCRIBE = "viewport.subscribe"
    VIEWPORT_UPDATE = "viewport.update"
    VIEWPORT_UNSUBSCRIBE = "viewport.unsubscribe"
    GM_HINT_SAMPLE = "gm_hint.sample"
    SESSION_RESUME = "session.resume"
    CHUNK_ACK = "chunk.ack"
    CHUNK_NACK = "chunk.nack"
    CHAT_MESSAGE_CREATE = "chat.message.create"
    TOKEN_MOVE_REQUEST = "token.move.request"
    TOKEN_CREATE = "token.create"
    TOKEN_CREATE_MANY_FROM_ACTORS = "token.create_many_from_actors"
    TOKEN_DUPLICATE_MANY = "token.duplicate_many"
    TOKEN_MOVE = "token.move"
    TOKEN_UPDATE_OVERRIDE = "token.update_override"
    TOKEN_HIDE = "token.hide"
    TOKEN_REVEAL = "token.reveal"
    TOKEN_SET_VISION = "token.set_vision"
    TOKEN_REMOVE_FROM_SCENE = "token.remove_from_scene"
    TOKEN_CONDITION_ADD = "token.condition.add"
    TOKEN_CONDITION_REMOVE = "token.condition.remove"
    ROLL_CREATE_REQUEST = "roll.create.request"
    SCENE_ACTIVATE_REQUEST = "scene.activate.request"
    FOG_ENABLE = "fog.enable"
    FOG_DISABLE = "fog.disable"
    FOG_PAINT = "fog.paint"
    FOG_RESET = "fog.reset"


KNOWN_COMMANDS: frozenset[str] = frozenset(command.value for command in ClientCommand)


UNKNOWN_COMMAND_LABEL = "unknown"


def command_label(command: str | None) -> str:
    """Return a bounded label for ``command``, safe to use as a dict/metric key.

    The command name arrives as arbitrary client JSON and is read *before* the
    dispatcher rejects unknown commands, so using it directly as a key lets a
    client mint unlimited distinct keys in per-process state. Anything not in
    the enum collapses to a single shared label.
    """
    if command in KNOWN_COMMANDS:
        return str(command)
    return UNKNOWN_COMMAND_LABEL
