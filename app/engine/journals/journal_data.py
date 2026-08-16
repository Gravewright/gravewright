"""Structured data shapes and normalization for Journals (RC1).

The journal *body* is stored as Markdown (the rich-text format the project
already ships), while the structured, per-type fields live in ``data_json``.
This module is the single place that knows the shape of that JSON, keeps it
sanitized, and builds the player/GM views described in the RC1 spec.
"""

from __future__ import annotations

import uuid

JOURNAL_TYPES = {"diary", "quest", "quest_board"}
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
    from app.engine.journals import journal_doc

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
    return {}


def normalize_diary_data(raw: object) -> dict:
    """Diary body is a ``gw-journal-doc-v1`` block document under ``content``.

    GM notes/secrets live in dedicated GM-only docs (like quests) so the public
    body never carries GM-visibility blocks.
    """
    raw = raw if isinstance(raw, dict) else {}
    gm = raw.get("gm") if isinstance(raw.get("gm"), dict) else {}
    sections_raw = raw.get("sections") if isinstance(raw.get("sections"), list) else []
    sections = [
        _normalize_section(section, (index + 1) * 10)
        for index, section in enumerate(sections_raw[:SECTION_LIMIT])
    ]
    sections.sort(key=lambda section: section["sortOrder"])
    return {
        "content": _doc(raw.get("content")),
        "cover": _normalize_image(raw.get("cover")),
        "sections": sections,
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
    }


def normalize_board_data(raw: object) -> dict:
    return {}


def normalize_data_for(journal_type: str, raw: object) -> dict:
    if journal_type == "quest":
        return normalize_quest_data(raw)
    if journal_type == "quest_board":
        return normalize_board_data(raw)
    if journal_type == "diary":
        return normalize_diary_data(raw)
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
    }


def build_quest_player_view(*, title: str, data: dict) -> dict:
    """Player-facing projection: strips GM notes/secrets and hidden items."""
    from app.engine.journals import journal_doc

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
