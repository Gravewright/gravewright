"""Base event identities and removal of retired state-triggered graphs."""

REMOVED_EVENTS = frozenset({"change", *(f"{phase}:{state}"
    for phase in ("enter", "exit", "interact")
    for state in ("closed", "open", "locked", "off", "on", "empty", "occupied"))})


def removed_event(value):
    return isinstance(value, str) and value in REMOVED_EVENTS
