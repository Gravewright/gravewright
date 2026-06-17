from __future__ import annotations

from typing import Any
from typing import NotRequired
from typing import TypedDict


class RollGroupData(TypedDict):
    notation: str
    results: list[int]


class PresencePlayerData(TypedDict):
    user_id: str
    name: str
    role: str
    is_online: bool


class MemberPlayerData(TypedDict):
    user_id: str
    name: str
    email: str
    role: str
    is_online: bool


class PresenceUpdatedPayload(TypedDict):
    room_id: str
    user_id: str
    is_online: bool
    last_seen_at: int


class PresenceSnapshotPayload(TypedDict):
    room_id: str
    players: list[PresencePlayerData]


class MemberJoinedPayload(TypedDict):
    room_id: str
    player: MemberPlayerData


class MemberRemovedPayload(TypedDict):
    room_id: str
    user_id: str
    name: str
    role: str
    reason: str


class ChatMessageCreatedPayload(TypedDict):
    message_id: str
    room_id: str
    author: str
    author_id: str
    role: str
    kind: str
    visibility: str
    content: NotRequired[str]
    expression: NotRequired[str]
    groups: NotRequired[list[RollGroupData]]
    modifier: NotRequired[int | None]
    total: NotRequired[int | float]
    sender_player_id: NotRequired[str]
    target_player_ids: NotRequired[list[str]]


class ChatMessageDeletedPayload(TypedDict):
    message_id: str
    room_id: str


class ChatMessagesClearedPayload(TypedDict):
    room_id: str


class JournalEventPayload(TypedDict):
    room_id: str
    journal_id: str
    type: str
    version: NotRequired[int]
    updated_by: str
    changed_paths: NotRequired[list[str]]


class ActorEventPayload(TypedDict):
    room_id: str
    actor_id: str
    system_id: str
    type: NotRequired[str]
    version: NotRequired[int]
    updated_by: str


class SheetDataUpdatedPayload(TypedDict):
    room_id: str
    system_id: str
    actor_id: str
    version: int
    updated_by: str
    changed_paths: list[str]


class SceneCreatedPayload(TypedDict):
    room_id: str
    scene_id: str
    name: str
    width: int
    height: int
    tile_size: int
    chunk_size: int


class SceneActivatedPayload(TypedDict):
    room_id: str
    scene_id: str
    previous_scene_id: NotRequired[str | None]
    scene_epoch: NotRequired[int]
    scene: NotRequired[dict[str, Any]]


class SceneUpdatedPayload(TypedDict):
    room_id: str
    scene_id: str
    version: int


class SceneLayerPayload(TypedDict):
    room_id: str
    scene_id: str
    layer_id: str
    name: str
    kind: str
    visibility: str
    order: int
    encoding: str


class SceneLayerDeletedPayload(TypedDict):
    room_id: str
    scene_id: str
    layer_id: str


class SceneChunkUpdatedPayload(TypedDict):
    room_id: str
    scene_id: str
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    byte_size: int


class SceneChunkDeletedPayload(TypedDict):
    room_id: str
    scene_id: str
    layer_id: str
    cx: int
    cy: int


class TokenBarData(TypedDict):
    value: int | float
    max: int | float
    visibility: str


class TokenStatusSummary(TypedDict):
    count: int
    has_negative: bool
    has_positive: bool


class TokenViewPayload(TypedDict):
    token_id: str
    scene_id: str
    actor_id: NotRequired[str | None]
    grid_x: int
    grid_y: int
    width_cells: int
    height_cells: int
    name: str
    asset_url: NotRequired[str | None]
    disposition: str
    hidden: bool
    locked: bool
    bars: dict[str, TokenBarData]
    status_summary: TokenStatusSummary
    controlled_by_role: str
    controlled_by_user_ids: list[str]
    version: int


class TokensSnapshotPayload(TypedDict):
    room_id: str
    scene_id: str
    tokens: list[TokenViewPayload]


class TokensCreatedPayload(TypedDict):
    room_id: str
    scene_id: str
    tokens: list[TokenViewPayload]


class TokensMovedPayload(TypedDict):
    room_id: str
    scene_id: str
    tokens: list[dict]


class TokensUpdatedPayload(TypedDict):
    room_id: str
    scene_id: str
    tokens: list[dict]


class TokensDeletedPayload(TypedDict):
    room_id: str
    scene_id: str
    token_ids: list[str]


class TokensVisibilityChangedPayload(TypedDict):
    room_id: str
    scene_id: str
    tokens: list[dict]


class TokensConditionsUpdatedPayload(TypedDict):
    room_id: str
    scene_id: str
    token_id: str
    conditions: list[dict]
