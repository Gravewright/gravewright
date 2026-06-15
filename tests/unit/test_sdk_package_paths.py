from __future__ import annotations

from pathlib import Path

from app.engine.sdk.package_paths import package_id_is_safe, path_is_safe, safe_join


def test_package_id_is_safe():
    assert package_id_is_safe("dnd5e")
    assert package_id_is_safe("dice-so-nice-lite")
    assert not package_id_is_safe("DnD5e")
    assert not package_id_is_safe("with_underscore")
    assert not package_id_is_safe("-leading")
    assert not package_id_is_safe("trailing-")
    assert not package_id_is_safe("a--b")
    assert not package_id_is_safe("")
    assert not package_id_is_safe(None)


def test_path_is_safe_rejects_traversal_and_absolute():
    assert path_is_safe("assets/main.js")
    assert path_is_safe("a/b/c.json")
    assert not path_is_safe("")
    assert not path_is_safe("/etc/passwd")
    assert not path_is_safe("../escape")
    assert not path_is_safe("a/../../b")
    assert not path_is_safe("a//b")
    assert not path_is_safe("a\\b")
    assert not path_is_safe("https://example.com/x")
    assert not path_is_safe("C:/win")
    assert not path_is_safe("dir/")
    assert not path_is_safe("./asset.js")
    assert not path_is_safe("assets/./main.js")
    assert not path_is_safe("assets/main:alt.js")
    assert not path_is_safe("assets/name-with-space ")
    assert not path_is_safe("assets/name-with-dot.")
    assert not path_is_safe("assets/CON")
    assert not path_is_safe("assets/con.txt")
    assert not path_is_safe("assets/AUX.png")
    assert not path_is_safe("assets/COM1")
    assert not path_is_safe("assets/LPT9.map")


def test_safe_join_confines_to_base(tmp_path: Path):
    (tmp_path / "assets").mkdir()
    target = tmp_path / "assets" / "main.js"
    target.write_text("//", encoding="utf-8")

    assert safe_join(tmp_path, "assets/main.js") == target.resolve()
    assert safe_join(tmp_path, "../outside") is None
    assert safe_join(tmp_path, "/abs") is None
    assert safe_join(tmp_path, "") is None
