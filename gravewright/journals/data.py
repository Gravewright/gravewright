"""Normalized block documents and structured fields for the four journal types.

Ported from the original VTT journal_data module. Legacy Markdown fields are
retained in the schema; new editing uses gw-journal-doc-v1 documents.
"""

from __future__ import annotations

import uuid
import hashlib
import re

JOURNAL_TYPES = {"diary", "quest", "quest_board", "roll_table"}
VISIBILITIES = {"private", "shared", "handout"}
QUEST_STATUSES = ["draft", "available", "active", "completed", "failed", "archived"]
BOARD_ENTRY_VISIBILITIES = {"public_card"}


PLAYER_VISIBLE_STATUSES = {"available", "active", "completed", "failed"}

RICHTEXT_LIMIT = 20000
TEXT_LIMIT = 240
OBJECTIVE_LIMIT = 64
REWARD_LIMIT = 64
TAG_LIMIT = 32
SECTION_LIMIT = 64
CHAPTER_LIMIT = 128
CHAPTER_DEPTH_LIMIT = 8
PREREQUISITE_LIMIT = 16
ROLL_TABLE_ENTRY_LIMIT = 256


def normalize_visibility(value: object) -> str:
    value = str(value or "").strip()
    return value if value in VISIBILITIES else "private"


def normalize_status(value: object) -> str:
    value = str(value or "").strip()
    return value if value in QUEST_STATUSES else "draft"


def _markdown(value: object) -> str:
    return str(value or "")[:RICHTEXT_LIMIT]


def _doc(raw: object) -> dict:
    """Validate a gw-journal-doc-v1 rich field (lazy import avoids a cycle)."""
    from . import documents as journal_doc

    return journal_doc.validate_document(raw)


def _short(value: object, limit: int = TEXT_LIMIT) -> str:
    return str(value or "").strip()[:limit]


def _bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "yes"}
    return bool(value)


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_src(value: object) -> str:
    """Allow internal/relative or http(s) image URLs; block data:/javascript: etc."""
    src = str(value or "").strip()[:1024]
    if not src:
        return ""
    lowered = src.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return ""
    if src.startswith("/") or lowered.startswith(("http://", "https://")):
        return src
    return ""


def _normalize_image(raw: object) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "assetId": _short(raw.get("assetId"), 120),
        "src": _safe_src(raw.get("src")),
    }


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _normalize_objective(raw: object, fallback_order: int) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "id": _short(raw.get("id"), 40) or _gen_id("obj"),
        "text": _short(raw.get("text"), OBJECTIVE_LIMIT * 4),
        "completed": _bool(raw.get("completed")),
        "optional": _bool(raw.get("optional")),
        "visibleToPlayers": _bool(raw.get("visibleToPlayers")),
        "sortOrder": _int(raw.get("sortOrder"), fallback_order),
    }


def _normalize_reward(raw: object) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "id": _short(raw.get("id"), 40) or _gen_id("reward"),
        "text": _short(raw.get("text"), REWARD_LIMIT * 4),
        "visibleToPlayers": _bool(raw.get("visibleToPlayers")),
    }


def _normalize_section(raw: object, fallback_order: int) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    level = max(1, min(3, _int(raw.get("level"), 1)))
    kind = str(raw.get("kind") or "text").strip().lower()
    if kind not in {"text", "image", "pdf"}:
        kind = "text"
    level = 1
    audience = str(raw.get("audience") or "public").strip()
    src = _short(raw.get("src"), 1024)
    asset_id = _short(raw.get("assetId") or raw.get("asset_id"), 120)
    prefix = "/game/journal/asset/"
    if not asset_id and src.startswith(prefix):
        asset_id = src[len(prefix):].split("?", 1)[0].split("#", 1)[0]
    if asset_id and not all(ch.isalnum() or ch in {"_", "-"} for ch in asset_id):
        asset_id = ""
    if kind == "pdf" and asset_id:
        src = f"{prefix}{asset_id}"
    return {
        "id": _short(raw.get("id"), 40) or _gen_id("section"),
        "title": _short(raw.get("title"), 120) or "Untitled",
        "category": _short(raw.get("category"), 80),
        "chapterId": raw.get("chapterId") if isinstance(raw.get("chapterId"), str) else None,
        "kind": kind,
        "assetId": asset_id,
        "src": src,
        "level": level,
        "audience": audience if audience in {"public", "gm"} else "public",
        "sortOrder": _int(raw.get("sortOrder"), fallback_order),
        "content": _doc(raw.get("content")),
    }


def empty_data_for(journal_type: str) -> dict:
    if journal_type == "quest":
        return normalize_quest_data({})
    if journal_type == "quest_board":
        return normalize_board_data({})
    if journal_type == "diary":
        return normalize_diary_data({})
    if journal_type == "roll_table":
        return normalize_roll_table_data({})
    return {}


def legacy_chapter_id(name: str) -> str:
    """Legacy category identities remain stable across reads, copies and restores."""
    return 'chapter_' + hashlib.sha256(name.encode('utf-8')).hexdigest()[:24]


def validate_diary_structure(raw: dict) -> None:
    """Reject explicit malformed chapter trees without coercing authored input."""
    if not isinstance(raw, dict) or not isinstance(raw.get('sections', []), list):
        raise ValueError('Invalid journal chapters.')
    chapters = raw.get('chapters', [])
    if not isinstance(chapters, list) or len(chapters) > CHAPTER_LIMIT:
        raise ValueError('Invalid journal chapters.')
    indexed = {}
    for row in chapters:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', row['id']) or row['id'] in indexed
                or not isinstance(row.get('name'), str) or not row['name'].strip() or len(row['name']) > 80
                or type(row.get('sortOrder', 0)) is not int or abs(row.get('sortOrder', 0)) > 2**31 - 1
                or row.get('parentId') is not None and not isinstance(row.get('parentId'), str)):
            raise ValueError('Invalid journal chapters.')
        indexed[row['id']] = row
    for row in chapters:
        cursor, visited = row, set()
        while cursor is not None:
            identifier = cursor['id']
            if identifier in visited or len(visited) >= CHAPTER_DEPTH_LIMIT:
                raise ValueError('Invalid journal chapters.')
            visited.add(identifier)
            parent = cursor.get('parentId')
            if parent is not None and parent not in indexed:
                raise ValueError('Invalid journal chapters.')
            cursor = indexed.get(parent)
    names = {_short(row['name'], 80) for row in chapters}
    legacy_names = set()
    for section in raw.get('sections', []):
        if not isinstance(section, dict) or 'chapterId' not in section:
            if isinstance(section, dict):
                name = _short(section.get('category'), 80)
                if name and name not in names:
                    legacy_names.add(name)
            continue
        chapter = section['chapterId']
        if chapter is not None and (not isinstance(chapter, str) or chapter not in indexed):
            raise ValueError('Invalid journal chapters.')
    if len(chapters) + len(legacy_names) > CHAPTER_LIMIT:
        raise ValueError('Invalid journal chapters.')


def normalize_diary_data(raw: object) -> dict:
    """Diary body is a ``gw-journal-doc-v1`` block document under ``content``.

    GM notes/secrets live in dedicated GM-only docs (like quests) so the public
    body never carries GM-visibility blocks.
    """
    raw = raw if isinstance(raw, dict) else {}
    gm = raw.get("gm") if isinstance(raw.get("gm"), dict) else {}
    chapter_rows = raw.get('chapters') if isinstance(raw.get('chapters'), list) else []
    chapters, indexed = [], {}
    for index, row in enumerate(chapter_rows[:CHAPTER_LIMIT]):
        if not isinstance(row, dict):
            continue
        identifier, name = _short(row.get('id'), 40), _short(row.get('name'), 80)
        if not identifier or not name or identifier in indexed:
            continue
        chapter = {'id': identifier, 'name': name, 'parentId': _short(row.get('parentId'), 40) or None,
                   'sortOrder': _int(row.get('sortOrder'), (index + 1) * 10)}
        chapters.append(chapter); indexed[identifier] = chapter
    sections_raw = raw.get("sections") if isinstance(raw.get("sections"), list) else []
    sections = [
        _normalize_section(section, (index + 1) * 10)
        for index, section in enumerate(sections_raw[:SECTION_LIMIT])
    ]
    by_name = {}
    for chapter in chapters:
        by_name.setdefault(chapter['name'], chapter)
    for section, original in zip(sections, sections_raw[:SECTION_LIMIT]):
        if isinstance(original, dict) and 'chapterId' not in original and section['category']:
            name = section['category']
            if name not in by_name:
                identifier, suffix = legacy_chapter_id(name), 0
                while identifier in indexed:
                    suffix += 1
                    identifier = legacy_chapter_id(name + ':' + str(suffix))
                chapter = {'id': identifier, 'name': name, 'parentId': None, 'sortOrder': (len(chapters) + 1) * 10}
                chapters.append(chapter); indexed[identifier] = chapter; by_name[name] = chapter
            section['chapterId'] = by_name[name]['id']
        if section['chapterId'] not in indexed:
            section['chapterId'] = None
        section['category'] = indexed[section['chapterId']]['name'] if section['chapterId'] else ''
    # Stored/legacy input remains readable even if a former import omitted a
    # parent; write validation rejects dangling parents and cycles explicitly.
    for chapter in chapters:
        if chapter['parentId'] not in indexed:
            chapter['parentId'] = None
    chapters.sort(key=lambda chapter: chapter['sortOrder'])
    sections.sort(key=lambda section: section["sortOrder"])
    return {
        "content": _doc(raw.get("content")),
        "cover": _normalize_image(raw.get("cover")),
        "sections": sections,
        "chapters": chapters,
        "gm": {
            "notes": _doc(gm.get("notes")),
            "secrets": _doc(gm.get("secrets")),
        },
    }


def normalize_quest_data(raw: object) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    public = raw.get("public") if isinstance(raw.get("public"), dict) else {}
    gm = raw.get("gm") if isinstance(raw.get("gm"), dict) else {}

    objectives_raw = raw.get("objectives")
    objectives = []
    if isinstance(objectives_raw, list):
        for index, item in enumerate(objectives_raw[:OBJECTIVE_LIMIT]):
            objectives.append(_normalize_objective(item, (index + 1) * 10))
    objectives.sort(key=lambda obj: obj["sortOrder"])

    rewards_raw = raw.get("rewards")
    if not isinstance(rewards_raw, list):
        rewards_raw = public.get("rewards") if isinstance(public.get("rewards"), list) else []
    rewards = [_normalize_reward(item) for item in rewards_raw[:REWARD_LIMIT]]

    tags_raw = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    tags = []
    for tag in tags_raw[:TAG_LIMIT]:
        cleaned = _short(tag, 40)
        if cleaned and cleaned not in tags:
            tags.append(cleaned)

    return {
        "status": normalize_status(raw.get("status")),
        "public": {
            "summary": _short(public.get("summary"), TEXT_LIMIT * 2),
            "description": _doc(public.get("description")),
            "description_markdown": _markdown(public.get("description_markdown")),
            "image": _normalize_image(public.get("image")),
            "location": _short(public.get("location")),
            "giver": _short(public.get("giver")),
        },
        "gm": {
            "notes": _doc(gm.get("notes")),
            "notes_markdown": _markdown(gm.get("notes_markdown")),
            "secrets": _doc(gm.get("secrets")),
            "secrets_markdown": _markdown(gm.get("secrets_markdown")),
        },
        "objectives": objectives,
        "rewards": rewards,
        "tags": tags,
        "assignees": list(dict.fromkeys(str(value) for value in raw.get('assignees', [])[:32])) if isinstance(raw.get('assignees'), list) else [],
        # GM planning links to other quests that should be completed first.
        "prerequisites": list(dict.fromkeys(_short(value, 40) for value in raw.get('prerequisites', [])[:PREREQUISITE_LIMIT] if _short(value, 40))) if isinstance(raw.get('prerequisites'), list) else [],
    }


def normalize_board_data(raw: object) -> dict:
    return {}


def _normalize_roll_table_entry(raw: object, fallback_order: int) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "id": _short(raw.get("id"), 40) or _gen_id("table"),
        "name": _short(raw.get("name"), 160),
        "weight": max(1, min(1_000_000, _int(raw.get("weight"), 1))),
        "result": _markdown(raw.get("result")),
        "active": _bool(raw.get("active")) if "active" in raw else True,
        "drawn": _bool(raw.get("drawn")),
        "sortOrder": _int(raw.get("sortOrder"), fallback_order),
    }


def normalize_roll_table_data(raw: object) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    entries_raw = raw.get("entries") if isinstance(raw.get("entries"), list) else []
    entries = [
        _normalize_roll_table_entry(entry, (index + 1) * 10)
        for index, entry in enumerate(entries_raw[:ROLL_TABLE_ENTRY_LIMIT])
    ]
    entries.sort(key=lambda entry: entry["sortOrder"])
    visibility = str(raw.get("resultVisibility") or "public").strip().lower()
    return {
        "entries": entries,
        "withReplacement": _bool(raw.get("withReplacement")) if "withReplacement" in raw else True,
        "resultVisibility": visibility if visibility in {"public", "gm"} else "public",
    }


def normalize_data_for(journal_type: str, raw: object) -> dict:
    if journal_type == "quest":
        return normalize_quest_data(raw)
    if journal_type == "quest_board":
        return normalize_board_data(raw)
    if journal_type == "diary":
        return normalize_diary_data(raw)
    if journal_type == "roll_table":
        return normalize_roll_table_data(raw)
    return {}


def build_quest_gm_view(*, title: str, data: dict) -> dict:
    data = normalize_quest_data(data)
    visible_objectives = [obj for obj in data["objectives"] if obj["visibleToPlayers"]]
    visible_rewards = [reward for reward in data["rewards"] if reward["visibleToPlayers"]]
    return {
        "title": title,
        "status": data["status"],
        "public": data["public"],
        "gm": data["gm"],
        "objectives": data["objectives"],
        "rewards": data["rewards"],
        "display_objectives": visible_objectives,
        "display_rewards": visible_rewards,
        "tags": data["tags"],
        "assignees": data['assignees'],
        "prerequisites": data["prerequisites"],
    }


def build_quest_player_view(*, title: str, data: dict) -> dict:
    """Player-facing projection: strips GM notes/secrets and hidden items."""
    from . import documents as journal_doc

    data = normalize_quest_data(data)
    visible_objectives = [obj for obj in data["objectives"] if obj["visibleToPlayers"]]
    visible_rewards = [reward for reward in data["rewards"] if reward["visibleToPlayers"]]
    return {
        "title": title,
        "status": data["status"],
        "public": {
            "summary": data["public"]["summary"],
            "description": journal_doc.filter_doc_for_role(
                data["public"]["description"], is_gm=False
            ),
            "description_markdown": data["public"]["description_markdown"],
            "image": data["public"]["image"],
            "location": data["public"]["location"],
            "giver": data["public"]["giver"],
        },
        "objectives": visible_objectives,
        "rewards": visible_rewards,
        "display_objectives": visible_objectives,
        "display_rewards": visible_rewards,
        "tags": data["tags"],
        "assignees": data['assignees'],
    }


def build_quest_card(*, title: str, data: dict) -> dict:
    """Compact public card used on quest boards."""
    view = build_quest_player_view(title=title, data=data)
    return {
        "title": view["title"],
        "status": view["status"],
        "summary": view["public"]["summary"],
        "image": view["public"]["image"],
        "location": view["public"]["location"],
        "giver": view["public"]["giver"],
        "objectives": view["objectives"],
        "rewards": view["rewards"],
    }
