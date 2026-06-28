from __future__ import annotations

from enum import StrEnum


class TransportEvent(StrEnum):
    ERROR = "error"

    MEMBER_JOINED = "member.joined"
    MEMBER_REMOVED = "member.removed"
    PRESENCE_UPDATED = "presence.updated"
    PRESENCE_SNAPSHOT = "presence.snapshot"

    CAMPAIGN_SYSTEM_CHANGED = "campaign.system.changed"
    CAMPAIGN_PACKAGES_CHANGED = "campaign.packages.changed"

    CHAT_MESSAGE_CREATED = "chat.message.created"
    CHAT_MESSAGE_DELETED = "chat.message.deleted"
    CHAT_MESSAGES_CLEARED = "chat.messages.cleared"

    JOURNAL_CREATED = "journal.created"
    JOURNAL_UPDATED = "journal.updated"
    JOURNAL_DELETED = "journal.deleted"
    JOURNAL_ACCESS_CHANGED = "journal.access_changed"
    QUEST_STATUS_CHANGED = "quest.status_changed"
    QUEST_OBJECTIVE_UPDATED = "quest.objective_updated"
    QUEST_BOARD_UPDATED = "quest_board.updated"

    ACTOR_CREATED = "actor.created"
    ACTOR_UPDATED = "actor.updated"
    ACTOR_DELETED = "actor.deleted"
    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"
    SHEET_DATA_UPDATED = "sheet.data.updated"
    SHEET_DROP_APPLIED = "sheet.drop.applied"
    CONTENT_ENTRY_IMPORTED = "content.entry.imported"

    TOKEN_CREATED = "token.created"
    TOKEN_MOVED = "token.moved"
    TOKEN_UPDATED = "token.updated"
    TOKEN_DELETED = "token.deleted"

    TOKENS_SNAPSHOT = "tokens.snapshot"
    TOKENS_CREATED = "tokens.created"
    TOKENS_UPDATED = "tokens.updated"
    TOKENS_MOVED = "tokens.moved"
    TOKENS_DELETED = "tokens.deleted"
    TOKENS_VISIBILITY_CHANGED = "tokens.visibility_changed"
    TOKENS_CONDITIONS_UPDATED = "tokens.conditions.updated"

    ROLL_CREATED = "roll.created"

    CARDS_STATE_UPDATED = "cards.state.updated"

    ASSETS_LIBRARY_UPDATED = "assets.library.updated"
    SCENE_IMAGES_UPDATED = "scene.images.updated"

    SCENE_UPLOAD_PROGRESS = "scene.upload.progress"
    SCENE_CREATED = "scene.created"
    SCENE_ACTIVATED = "scene.activated"
    SCENE_UPDATED = "scene.updated"
    SCENE_DELETED = "scene.deleted"
    SCENE_LAYER_CREATED = "scene.layer.created"
    SCENE_LAYER_UPDATED = "scene.layer.updated"
    SCENE_LAYER_DELETED = "scene.layer.deleted"
    SCENE_CHUNK_UPDATED = "scene.chunk.updated"
    SCENE_CHUNK_DELETED = "scene.chunk.deleted"

    FOG_UPDATED = "fog.updated"

    BOARD_PING = "board.ping"
    BOARD_AREA_MARKER_UPSERTED = "board.area_marker.upserted"
    BOARD_AREA_MARKER_DELETED = "board.area_marker.deleted"
    BOARD_AREA_MARKER_CLEARED = "board.area_marker.cleared"
    BOARD_DRAW_UPSERTED = "board.draw.upserted"
    BOARD_DRAW_CLEARED = "board.draw.cleared"
    BOARD_MEASURE_FLASHED = "board.measure.flashed"
    BOARD_MEASURE_DELETED = "board.measure.deleted"
    BOARD_MEASURE_CLEARED = "board.measure.cleared"

    COMBAT_STARTED = "combat.started"
    COMBAT_UPDATED = "combat.updated"
    COMBAT_ENDED = "combat.ended"
    COMBAT_STATE_UPDATED = "combat.state.updated"
    COMBAT_PARTICIPANT_ADDED = "combat.participant.added"
    COMBAT_PARTICIPANT_REMOVED = "combat.participant.removed"
    COMBAT_TURN_STARTED = "combat.turn.started"
    COMBAT_TURN_ENDED = "combat.turn.ended"
    COMBAT_ROUND_STARTED = "combat.round.started"
    COMBAT_ROUND_ENDED = "combat.round.ended"
    COMBAT_ACTIVITY_RECORDED = "combat.activity.recorded"
    COMBAT_EFFECT_TRIGGERED = "combat.effect.triggered"
