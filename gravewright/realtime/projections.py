"""Per-socket projection differences, in the format realtime-state.js merges.

A delta is computed only from the recipient's own complete projection and the
previous projection this socket received, so it can never carry data that the
complete projection would not. List fields whose rows are dicts with unique ids
travel as ``upserts``/``removes`` (plus ``order`` when the merged order differs);
any other changed top-level value travels whole, and dropped keys are ``unset``.
"""

import json

# Projections that may travel as deltas, with the key that identifies their scene.
DELTA_KEYS = {"tokens.state": "mapId", "maps.layers": "sceneId"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def rows_by_id(value):
    """Rows keyed by id, or None when the list is not a set of identified rows."""
    if not isinstance(value, list):
        return None
    rows = {}
    for row in value:
        if not isinstance(row, dict) or "id" not in row:
            return None
        key = str(row["id"])
        if key in rows:
            return None
        rows[key] = row
    return rows


def merged_order(previous_ids, upserted_ids, removed_ids):
    """The order realtime-state.js produces without an explicit ``order``."""
    removed = set(removed_ids)
    kept = [key for key in previous_ids if key not in removed]
    known = set(previous_ids)
    return kept + [key for key in upserted_ids if key not in known]


def delta(kind, previous, current):
    """The frame turning ``previous`` into ``current``, or None when they are equal."""
    upserts, removes, order, metadata = {}, {}, {}, {}
    unset = sorted(set(previous) - set(current))
    for field, value in current.items():
        if field in previous and canonical(previous[field]) == canonical(value):
            continue
        old_rows = rows_by_id(previous.get(field)) if field in previous else None
        new_rows = rows_by_id(value)
        if old_rows is None or new_rows is None:
            metadata[field] = value
            continue
        changed = [row for key, row in new_rows.items()
                   if key not in old_rows or canonical(old_rows[key]) != canonical(row)]
        removed = [key for key in old_rows if key not in new_rows]
        if changed:
            upserts[field] = changed
        if removed:
            removes[field] = removed
        if merged_order(list(old_rows), [str(row["id"]) for row in changed], removed) != list(new_rows):
            order[field] = list(new_rows)
    if not (upserts or removes or order or metadata or unset):
        return None
    identity = DELTA_KEYS[kind]
    frame = {"delta": True, identity: current[identity], **metadata}
    for name, value in (("upserts", upserts), ("removes", removes), ("order", order), ("unset", unset)):
        if value:
            frame[name] = value
    return frame


def apply(previous, frame):
    """Reference merge used by tests; mirrors createProjectionState in realtime-state.js."""
    frame = dict(frame)
    frame.pop("delta")
    upserts, removes = frame.pop("upserts", {}), frame.pop("removes", {})
    order, unset = frame.pop("order", {}), frame.pop("unset", [])
    result = {**json.loads(canonical(previous)), **frame}
    for field in unset:
        result.pop(field, None)
    for field in set(upserts) | set(removes) | set(order):
        rows = {str(row["id"]): row for row in previous.get(field, [])}
        for key in removes.get(field, []):
            rows.pop(str(key), None)
        for row in upserts.get(field, []):
            rows[str(row["id"])] = row
        result[field] = [rows[str(key)] for key in order[field]] if field in order else list(rows.values())
    return result
