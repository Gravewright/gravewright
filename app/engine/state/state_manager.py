from __future__ import annotations

import copy
import json
from typing import Any


StatePayload = dict[str, Any]


def clone_state(state: StatePayload) -> StatePayload:
    return copy.deepcopy(state)


def encode_state(state: StatePayload) -> str:
    return json.dumps(
        state,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decode_state(state_json: str | None) -> StatePayload:
    if not state_json:
        return {}

    value = json.loads(state_json)

    if not isinstance(value, dict):
        return {}

    return value


def create_state_pair(initial_state: StatePayload) -> tuple[str, str]:
    initial = clone_state(initial_state)
    persistent = clone_state(initial_state)

    return encode_state(initial), encode_state(persistent)


def reset_persistent_from_initial(initial_state_json: str) -> str:
    return encode_state(decode_state(initial_state_json))