from pathlib import Path

from scripts import setup_local_env


def point_setup_at(monkeypatch, root: Path) -> Path:
    env = root / ".env"
    monkeypatch.setattr(setup_local_env, "ENV", env)
    monkeypatch.setattr(setup_local_env, "EXAMPLE", root / ".env.example")
    monkeypatch.setattr(
        setup_local_env,
        "DEVELOPMENT_EXAMPLE",
        root / ".env.development.example",
    )
    return env


def test_missing_templates_create_a_sqlite_environment(tmp_path, monkeypatch):
    env = point_setup_at(monkeypatch, tmp_path)

    assert setup_local_env.main() == 0

    content = env.read_text(encoding="utf-8")
    assert "APP_ENV=development" in content
    assert "APP_DEBUG=false" in content
    assert "DATABASE_URL=sqlite:///storage/gravewright.sqlite3" in content
    assert "GRAVEWRIGHT_DATA_DIR=./data" in content
    assert "SESSION_SECRET=dev-only-change-me" not in content


def test_existing_environment_is_not_replaced(tmp_path, monkeypatch):
    env = point_setup_at(monkeypatch, tmp_path)
    env.write_text(
        "DATABASE_URL=sqlite:///custom.sqlite3\nSESSION_SECRET=already-safe\n",
        encoding="utf-8",
    )

    assert setup_local_env.main() == 0

    assert env.read_text(encoding="utf-8") == (
        "DATABASE_URL=sqlite:///custom.sqlite3\nSESSION_SECRET=already-safe\n"
    )
