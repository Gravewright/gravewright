from __future__ import annotations

from enum import StrEnum


class PermissionEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class PermissionSubjectType(StrEnum):
    ROLE = "role"
    USER = "user"


class TablePermission(StrEnum):
    CAMPAIGN_INVITE_MEMBERS = "campaign.invite_members"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_UPDATE_PERMISSIONS = "settings.update_permissions"

    CHAT_VIEW = "chat.view"
    CHAT_SEND = "chat.send"
    CHAT_WHISPER = "chat.whisper"
    CHAT_SEND_TO_GM = "chat.send_to_gm"
    CHAT_DELETE_OWN = "chat.delete_own"
    CHAT_DELETE_ANY = "chat.delete_any"

    COMBAT_VIEW = "combat.view"

    SCENE_VIEW = "scene.view"
    SCENE_CREATE = "scene.create"
    SCENE_MANAGE = "scene.manage"
    SCENE_ACTIVATE = "scene.activate"
    SCENE_DELETE = "scene.delete"

    MAP_UPLOAD = "map.upload"
    MAP_EDIT = "map.edit"
    MAP_PAINT = "map.paint"
    MAP_DELETE = "map.delete"

    FOG_PAINT = "fog.paint"

    GRID_VIEW = "grid.view"
    GRID_MEASURE = "grid.measure"

    BOARD_PING = "board.ping"
    BOARD_DRAW = "board.draw"
    BOARD_MARKER_CREATE = "board.marker.create"
    BOARD_MARKER_DELETE = "board.marker.delete"
    BOARD_MARKER_CLEAR = "board.marker.clear"

    TOKEN_CREATE = "token.create"
    TOKEN_MOVE = "token.move"
    TOKEN_DELETE = "token.delete"
    TOKEN_VISIBILITY = "token.visibility"
    TOKEN_CONDITION_MANAGE = "token.condition_manage"
    TOKEN_OVERRIDE_MANAGE = "token.override_manage"
