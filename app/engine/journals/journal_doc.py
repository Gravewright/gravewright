"""``gw-journal-doc-v1`` — the block-document format for Journals.

This is the source of truth for rich Journal content (replacing free Markdown).
A document is untrusted input, so this module is the single place that:

* validates the envelope (``format``/``version``),
* whitelists node types, marks, and attributes (everything else is dropped),
* sanitizes link/image URLs,
* enforces per-block ``visibility`` ("public" | "gm"),
* and filters a document down to what a given role may receive.

Block GM-visibility is enforced server-side: ``filter_doc_for_role`` strips
``visibility == "gm"`` nodes so players never receive GM blocks in the payload.
"""

from __future__ import annotations

DOC_FORMAT = "gw-journal-doc-v1"
DOC_VERSION = 1

VISIBILITIES = {"public", "gm"}
HEADING_LEVELS = {1, 2, 3}
CALLOUT_KINDS = {"gm_note", "secret"}
IMAGE_ALIGN = {"left", "center", "right"}
JOURNAL_ASSET_SRC_PREFIX = "/game/journal/asset/"
ALLOWED_MARKS = {"bold", "italic", "strike", "code", "link"}

                                          
MAX_NODES = 4000
MAX_DEPTH = 12
TEXT_NODE_LIMIT = 20000
TITLE_LIMIT = 120
ALT_LIMIT = 240
WIDTH_MAX = 2000

EMPTY_DOC: dict = {
    "format": DOC_FORMAT,
    "version": DOC_VERSION,
    "doc": {"type": "doc", "content": []},
}

                                                        
_CONTAINER_BLOCKS = {"blockquote", "listItem", "gwCallout"}
                                                               
_TEXT_BLOCKS = {"paragraph", "heading"}
                                            
_LIST_BLOCKS = {"bulletList", "orderedList"}


def _visibility(attrs: object) -> str:
    value = attrs.get("visibility") if isinstance(attrs, dict) else None
    value = str(value or "").strip()
    return value if value in VISIBILITIES else "public"


def _safe_href(value: object) -> str:
    href = str(value or "").strip()[:1024]
    if not href:
        return ""
    lowered = href.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return ""
    if href.startswith(("/", "#")) or lowered.startswith(("http://", "https://", "mailto:")):
        return href
    return ""


def _safe_asset_id(value: object) -> str:
    asset_id = str(value or "").strip()[:120]
    if not asset_id:
        return ""
    if all(ch.isalnum() or ch in {"_", "-"} for ch in asset_id):
        return asset_id
    return ""


def _clean_image_ref(attrs: dict) -> tuple[str, str] | None:
    """Return (asset_id, src) for a valid internal journal asset image.

    gwImage is intentionally stricter than generic links: images must be
    uploaded through Gravewright and referenced by assetId + internal src.
    External http(s), data:, file:, and mismatched assetId/src pairs are
    rejected. If an older document only has a valid internal src, derive the
    assetId from the route for forward compatibility.
    """
    src = str(attrs.get("src") or "").strip()[:1024]
    if not src.startswith(JOURNAL_ASSET_SRC_PREFIX):
        return None
    route_id = src[len(JOURNAL_ASSET_SRC_PREFIX):].split("?", 1)[0].split("#", 1)[0]
    if "/" in route_id:
        return None
    route_id = _safe_asset_id(route_id)
    if not route_id:
        return None
    asset_id = _safe_asset_id(attrs.get("assetId") or attrs.get("asset_id")) or route_id
    if asset_id != route_id:
        return None
    return asset_id, f"{JOURNAL_ASSET_SRC_PREFIX}{asset_id}"


def _clean_marks(raw: object) -> list:
    if not isinstance(raw, list):
        return []
    marks: list = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        mark_type = item.get("type")
        if mark_type not in ALLOWED_MARKS:
            continue
        if mark_type == "link":
            href = _safe_href((item.get("attrs") or {}).get("href"))
            if not href:
                continue
            marks.append({"type": "link", "attrs": {"href": href}})
        else:
            marks.append({"type": mark_type})
    return marks


def _clean_inline(raw: object) -> list:
    """Clean an array of inline nodes (text / hardBreak)."""
    if not isinstance(raw, list):
        return []
    out: list = []
    for node in raw:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if node_type == "text":
            text = node.get("text")
            if not isinstance(text, str) or not text:
                continue
            cleaned: dict = {"type": "text", "text": text[:TEXT_NODE_LIMIT]}
            marks = _clean_marks(node.get("marks"))
            if marks:
                cleaned["marks"] = marks
            out.append(cleaned)
        elif node_type == "hardBreak":
            out.append({"type": "hardBreak"})
    return out


class _Cleaner:
    def __init__(self) -> None:
        self.count = 0

    def blocks(self, raw: object, depth: int) -> list:
        if not isinstance(raw, list) or depth > MAX_DEPTH:
            return []
        out: list = []
        for node in raw:
            if self.count >= MAX_NODES:
                break
            cleaned = self.block(node, depth)
            if cleaned is not None:
                out.append(cleaned)
        return out

    def block(self, node: object, depth: int) -> dict | None:
        if not isinstance(node, dict):
            return None
        node_type = node.get("type")
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
        self.count += 1

        if node_type in _TEXT_BLOCKS:
            out: dict = {"type": node_type, "attrs": {"visibility": _visibility(attrs)}}
            if node_type == "heading":
                level = attrs.get("level")
                out["attrs"]["level"] = level if level in HEADING_LEVELS else 1
            content = _clean_inline(node.get("content"))
            if content:
                out["content"] = content
            return out

        if node_type == "blockquote":
            return {
                "type": "blockquote",
                "attrs": {"visibility": _visibility(attrs)},
                "content": self.blocks(node.get("content"), depth + 1) or [_empty_paragraph()],
            }

        if node_type in _LIST_BLOCKS:
            items = self._list_items(node.get("content"), depth + 1)
            if not items:
                return None
            return {"type": node_type, "attrs": {"visibility": _visibility(attrs)}, "content": items}

        if node_type == "horizontalRule":
            return {"type": "horizontalRule", "attrs": {"visibility": _visibility(attrs)}}

        if node_type == "gwCallout":
            kind = attrs.get("kind")
            kind = kind if kind in CALLOUT_KINDS else "gm_note"
            title = str(attrs.get("title") or "").strip()[:TITLE_LIMIT]
            return {
                "type": "gwCallout",
                                                               
                "attrs": {"kind": kind, "visibility": "gm", "title": title},
                "content": self.blocks(node.get("content"), depth + 1) or [_empty_paragraph()],
            }

        if node_type == "gwImage":
            image_ref = _clean_image_ref(attrs)
            if image_ref is None:
                return None
            asset_id, src = image_ref
            width = attrs.get("width")
            try:
                width = max(0, min(int(width), WIDTH_MAX)) or None
            except (TypeError, ValueError):
                width = None
            align = attrs.get("align")
            return {
                "type": "gwImage",
                "attrs": {
                    "visibility": _visibility(attrs),
                    "assetId": asset_id,
                    "src": src,
                    "alt": str(attrs.get("alt") or "").strip()[:ALT_LIMIT],
                    "caption": str(attrs.get("caption") or "").strip()[:ALT_LIMIT],
                    "align": align if align in IMAGE_ALIGN else "center",
                    "width": width,
                },
            }

        return None

    def _list_items(self, raw: object, depth: int) -> list:
        if not isinstance(raw, list) or depth > MAX_DEPTH:
            return []
        items: list = []
        for node in raw:
            if not isinstance(node, dict) or node.get("type") != "listItem":
                continue
            if self.count >= MAX_NODES:
                break
            self.count += 1
            items.append(
                {
                    "type": "listItem",
                    "content": self.blocks(node.get("content"), depth + 1) or [_empty_paragraph()],
                }
            )
        return items


def _empty_paragraph() -> dict:
    return {"type": "paragraph", "attrs": {"visibility": "public"}}


def validate_document(raw: object) -> dict:
    """Return a sanitized ``gw-journal-doc-v1`` document (never raises)."""
    if not isinstance(raw, dict):
        return _clone_empty()
    doc = raw.get("doc")
    content = doc.get("content") if isinstance(doc, dict) else None
    cleaned = _Cleaner().blocks(content, depth=0)
    return {
        "format": DOC_FORMAT,
        "version": DOC_VERSION,
        "doc": {"type": "doc", "content": cleaned},
    }


def is_empty_document(document: object) -> bool:
    if not isinstance(document, dict):
        return True
    doc = document.get("doc")
    content = doc.get("content") if isinstance(doc, dict) else None
    return not (isinstance(content, list) and len(content) > 0)


def filter_doc_for_role(document: object, *, is_gm: bool) -> dict:
    """Strip ``visibility == "gm"`` nodes for non-GM roles.

    GMs receive the full document; players never receive GM blocks. Filtering
    happens here (server side), not just in the UI.
    """
    document = validate_document(document)
    if is_gm:
        return document
    document["doc"]["content"] = _filter_blocks(document["doc"]["content"])
    return document


def _filter_blocks(blocks: object) -> list:
    if not isinstance(blocks, list):
        return []
    out: list = []
    for node in blocks:
        if not isinstance(node, dict):
            continue
        if (node.get("attrs") or {}).get("visibility") == "gm":
            continue
        if "content" in node and node.get("type") not in _TEXT_BLOCKS:
            if node.get("type") in _LIST_BLOCKS:
                node = {**node, "content": _filter_list_items(node["content"])}
            else:
                node = {**node, "content": _filter_blocks(node["content"])}
        out.append(node)
    return out


def merge_preserving_gm_blocks(submitted: object, stored: object) -> dict:
    """Re-attach top-level ``visibility == "gm"`` blocks from ``stored`` onto a
    ``submitted`` document.

    A non-GM editor never receives GM blocks (they are filtered out), so when
    they save, their document lacks those blocks. Without this merge their save
    would wipe the GM's notes/secrets. GM blocks are appended at the end (their
    original position is not recoverable from the filtered document).
    """
    submitted_doc = validate_document(submitted)
    stored_doc = validate_document(stored)
    gm_blocks = [
        node
        for node in stored_doc["doc"]["content"]
        if (node.get("attrs") or {}).get("visibility") == "gm"
    ]
    if gm_blocks:
        submitted_doc["doc"]["content"].extend(gm_blocks)
    return submitted_doc


def _filter_list_items(items: object) -> list:
    if not isinstance(items, list):
        return []
    out: list = []
    for item in items:
        if isinstance(item, dict) and "content" in item:
            item = {**item, "content": _filter_blocks(item["content"])}
        out.append(item)
    return out


def _clone_empty() -> dict:
    return {
        "format": DOC_FORMAT,
        "version": DOC_VERSION,
        "doc": {"type": "doc", "content": []},
    }
