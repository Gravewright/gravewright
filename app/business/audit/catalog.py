from __future__ import annotations

CATALOG_VERSION = 1


EVENT_METADATA_KEYS: dict[str, frozenset[str]] = {
    "join_code.generated": frozenset({"expires_at", "max_uses"}),
    "join_code.rotated": frozenset({"expires_at", "max_uses"}),
    "join_code.revoked": frozenset(),
    "membership.created": frozenset({"role", "source"}),
    "membership.removed": frozenset({"role", "reason"}),
    "membership.role_changed": frozenset({"previous_role", "next_role"}),
    "permission.updated": frozenset({"role", "changed_count"}),
    "package.activated": frozenset({"activation_role"}),
    "package.deactivated": frozenset({"activation_role", "forced"}),
    "ruleset.changed": frozenset({"previous_package_id", "next_package_id"}),
    "snapshot.created": frozenset({"kind", "format_version"}),
    "snapshot.restored": frozenset({"safety_snapshot_id", "scenes_restored"}),
    "snapshot.deleted": frozenset({"kind"}),
    "handout.granted": frozenset({"resource_type", "audience_type"}),
    "handout.revoked": frozenset({"resource_type", "audience_type"}),
    "handout.presented": frozenset({"resource_type", "audience_type"}),
    "campaign.exported": frozenset({"format_version", "selected_count"}),
}




EVENT_TYPES: tuple[str, ...] = tuple(EVENT_METADATA_KEYS)

METADATA_FIELDS: tuple[str, ...] = tuple(
    sorted({key for keys in EVENT_METADATA_KEYS.values() for key in keys})
)


SENSITIVE_KEY_FRAGMENTS = (
    "token", "secret", "password", "cookie", "csrf", "authorization",
    "email", "code", "hash", "session", "payload",
)


def safe_metadata(event_type: str, metadata: dict | None) -> dict:
    allowed = EVENT_METADATA_KEYS.get(event_type)
    if allowed is None:
        raise ValueError(f"unknown audit event type: {event_type}")
    source = metadata or {}
    result = {}
    for key in allowed:
        if key not in source:
            continue
        lowered = key.lower()
        if (
            any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)
            or lowered == "ip"
            or lowered.endswith("_ip")
        ):
            continue
        value = source[key]
        if value is None or isinstance(value, (str, int, float, bool)):
            result[key] = value
    return result
