from __future__ import annotations

from enum import StrEnum


class SheetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class SheetArchiveReason(StrEnum):
    SYSTEM_CHANGED = "system_changed"
    MANUAL_ARCHIVE = "manual_archive"
    IMPORTED_ARCHIVE = "imported_archive"
