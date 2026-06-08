from __future__ import annotations

from app.engine.journals import journal_doc


def _doc(*blocks):
    return {"format": "gw-journal-doc-v1", "version": 1, "doc": {"type": "doc", "content": list(blocks)}}


def test_validate_drops_unknown_nodes_and_marks():
    raw = _doc(
        {"type": "paragraph", "content": [
            {"type": "text", "text": "ok", "marks": [{"type": "bold"}, {"type": "evil"}]},
        ]},
        {"type": "scriptBlock", "content": []},
    )
    out = journal_doc.validate_document(raw)
    content = out["doc"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "paragraph"
    assert content[0]["content"][0]["marks"] == [{"type": "bold"}]


def test_validate_sanitizes_link_and_image_src():
    raw = _doc(
        {"type": "paragraph", "content": [
            {"type": "text", "text": "x", "marks": [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}]},
        ]},
        {"type": "gwImage", "attrs": {"src": "data:image/png;base64,AAAA"}},
        {"type": "gwImage", "attrs": {"src": "https://example.com/a.webp"}},
        {"type": "gwImage", "attrs": {
            "assetId": "asset_123",
            "src": "/game/journal/asset/asset_123",
            "align": "weird",
            "width": 99999,
        }},
    )
    out = journal_doc.validate_document(raw)["doc"]["content"]
                                                                    
    assert out[0]["content"][0].get("marks", []) == []
    images = [n for n in out if n["type"] == "gwImage"]
    assert len(images) == 1
    assert images[0]["attrs"]["assetId"] == "asset_123"
    assert images[0]["attrs"]["src"] == "/game/journal/asset/asset_123"
    assert images[0]["attrs"]["align"] == "center"
    assert images[0]["attrs"]["width"] == journal_doc.WIDTH_MAX


def test_callout_is_forced_gm_visibility():
    raw = _doc({
        "type": "gwCallout",
        "attrs": {"kind": "secret", "visibility": "public", "title": "S"},
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hidden"}]}],
    })
    out = journal_doc.validate_document(raw)["doc"]["content"][0]
    assert out["attrs"]["visibility"] == "gm"
    assert out["attrs"]["kind"] == "secret"


def test_filter_removes_gm_blocks_for_players():
    raw = _doc(
        {"type": "paragraph", "attrs": {"visibility": "public"},
         "content": [{"type": "text", "text": "public"}]},
        {"type": "gwCallout", "attrs": {"kind": "gm_note", "visibility": "gm", "title": "N"},
         "content": [{"type": "paragraph", "content": [{"type": "text", "text": "secret"}]}]},
    )
    gm_view = journal_doc.filter_doc_for_role(raw, is_gm=True)["doc"]["content"]
    player_view = journal_doc.filter_doc_for_role(raw, is_gm=False)["doc"]["content"]

    assert len(gm_view) == 2
    assert len(player_view) == 1
    assert player_view[0]["type"] == "paragraph"
    assert all(n.get("attrs", {}).get("visibility") != "gm" for n in player_view)


def test_filter_removes_gm_blocks_nested_in_list():
    raw = _doc({
        "type": "bulletList",
        "content": [{
            "type": "listItem",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "keep"}]},
                {"type": "gwCallout", "attrs": {"kind": "secret", "visibility": "gm", "title": ""},
                 "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}]},
            ],
        }],
    })
    player_view = journal_doc.filter_doc_for_role(raw, is_gm=False)["doc"]["content"]
    item_content = player_view[0]["content"][0]["content"]
    assert [n["type"] for n in item_content] == ["paragraph"]


def test_empty_document_helper():
    assert journal_doc.is_empty_document(journal_doc.EMPTY_DOC)
    assert journal_doc.is_empty_document(None)
    assert not journal_doc.is_empty_document(_doc({"type": "paragraph"}))


def test_validate_rejects_mismatched_image_asset_id_and_src():
    raw = _doc(
        {"type": "gwImage", "attrs": {
            "assetId": "asset_a",
            "src": "/game/journal/asset/asset_b",
        }},
    )

    out = journal_doc.validate_document(raw)["doc"]["content"]

    assert [n for n in out if n["type"] == "gwImage"] == []


def test_validate_derives_asset_id_from_legacy_internal_src():
    raw = _doc(
        {"type": "gwImage", "attrs": {"src": "/game/journal/asset/asset_legacy"}},
    )

    image = journal_doc.validate_document(raw)["doc"]["content"][0]

    assert image["attrs"]["assetId"] == "asset_legacy"
    assert image["attrs"]["src"] == "/game/journal/asset/asset_legacy"
