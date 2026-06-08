from __future__ import annotations

from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole


CORE_PERMISSION_GROUPS = [
    {
        "key": "campaign",
        "label_key": "permissions.groups.campaign",
        "permissions": [
            TablePermission.CAMPAIGN_INVITE_MEMBERS,
        ],
    },
    {
        "key": "settings",
        "label_key": "permissions.groups.settings",
        "permissions": [
            TablePermission.SETTINGS_VIEW,
            TablePermission.SETTINGS_UPDATE_PERMISSIONS,
        ],
    },
    {
        "key": "chat",
        "label_key": "permissions.groups.chat",
        "permissions": [
            TablePermission.CHAT_VIEW,
            TablePermission.CHAT_SEND,
            TablePermission.CHAT_WHISPER,
            TablePermission.CHAT_SEND_TO_GM,
            TablePermission.CHAT_DELETE_OWN,
            TablePermission.CHAT_DELETE_ANY,
        ],
    },
    {
        "key": "combat",
        "label_key": "permissions.groups.combat",
        "permissions": [
            TablePermission.COMBAT_VIEW,
        ],
    },
    {
        "key": "scene",
        "label_key": "permissions.groups.scene",
        "permissions": [
            TablePermission.SCENE_VIEW,
            TablePermission.SCENE_CREATE,
            TablePermission.SCENE_MANAGE,
            TablePermission.SCENE_ACTIVATE,
            TablePermission.SCENE_DELETE,
            TablePermission.MAP_UPLOAD,
            TablePermission.MAP_EDIT,
            TablePermission.MAP_PAINT,
            TablePermission.MAP_DELETE,
            TablePermission.FOG_PAINT,
            TablePermission.GRID_VIEW,
            TablePermission.GRID_MEASURE,
            TablePermission.TOKEN_CREATE,
            TablePermission.TOKEN_MOVE,
            TablePermission.TOKEN_DELETE,
            TablePermission.TOKEN_VISIBILITY,
            TablePermission.TOKEN_CONDITION_MANAGE,
            TablePermission.TOKEN_OVERRIDE_MANAGE,
        ],
    },
    {
        "key": "board",
        "label_key": "permissions.groups.board",
        "permissions": [
            TablePermission.BOARD_PING,
            TablePermission.BOARD_DRAW,
            TablePermission.BOARD_MARKER_CREATE,
            TablePermission.BOARD_MARKER_DELETE,
            TablePermission.BOARD_MARKER_CLEAR,
        ],
    },
]

ALL_CORE_PERMISSION_KEYS = {
    permission.value
    for group in CORE_PERMISSION_GROUPS
    for permission in group["permissions"]
}

CONFIGURABLE_ROLES = [
    PlayerRole.ASSISTANT_GM.value,
    PlayerRole.PLAYER.value,
    PlayerRole.STREAMER.value,
]

DISPLAY_ROLES = [
    PlayerRole.GM.value,
    PlayerRole.ASSISTANT_GM.value,
    PlayerRole.PLAYER.value,
    PlayerRole.STREAMER.value,
]
