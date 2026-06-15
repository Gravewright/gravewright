from __future__ import annotations

import json

from app.cli import main
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import install_system, seed_campaign, seed_system, seed_user


def _out(capsys) -> str:
    return capsys.readouterr().out


def test_package_list_json_shows_status(db, capsys):
    install_system(seed_user(email="pm-list@test.com"), package_id="dice-so-nice-lite")
    assert main(["package", "list", "--json"]) == 0
    payload = json.loads(_out(capsys))
    by_id = {p["id"]: p for p in payload["packages"]}
    assert by_id["dice-so-nice-lite"]["status"] == "enabled"
    assert by_id["dnd5e"]["status"] == "available"


def test_install_shows_capabilities_and_enables(db, capsys):
    assert main(["addon", "install", "dice-so-nice-lite", "--yes", "--enable"]) == 0
    out = _out(capsys)
    assert "Requested capabilities:" in out
    assert "assets.scripts" in out
    assert PackageInstallService().get("dice-so-nice-lite")["status"] == "enabled"


def test_install_aborts_without_confirmation(db, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert main(["addon", "install", "dice-so-nice-lite"]) == 3  # EXIT_UNSAFE
    assert "Aborted." in _out(capsys)
    assert PackageInstallService().get("dice-so-nice-lite") is None


def test_install_wrong_kind_is_incompatible(db, capsys):
    assert main(["addon", "install", "dnd5e", "--yes"]) == 5  # EXIT_INCOMPATIBLE
    assert "expected 'addon'" in _out(capsys)


def test_install_missing_source(db, capsys):
    assert main(["package", "install", "does-not-exist", "--yes"]) == 1
    assert "sdk.errors.not_found" in _out(capsys)


def test_enable_then_disable_roundtrip(db, capsys):
    install_system(seed_user(email="pm-toggle@test.com"), package_id="dice-so-nice-lite")
    assert main(["package", "disable", "dice-so-nice-lite"]) == 0
    assert PackageInstallService().get("dice-so-nice-lite")["status"] == "disabled"
    assert main(["package", "enable", "dice-so-nice-lite"]) == 0
    assert PackageInstallService().get("dice-so-nice-lite")["status"] == "enabled"


def test_remove_refuses_active_in_campaign_without_force(db, capsys):
    gm = seed_user(email="pm-remove@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")  # ruleset active in the campaign

    assert main(["package", "remove", "dnd5e"]) == 3  # EXIT_UNSAFE
    out = _out(capsys)
    assert "package_active_in_campaign" in out
    assert campaign in out  # lists the blocking campaign

    assert main(["package", "remove", "dnd5e", "--force"]) == 0
    assert PackageInstallService().get("dnd5e") is None


def test_update_all_preserves_enabled_status(db, capsys):
    install_system(seed_user(email="pm-update@test.com"), package_id="dice-so-nice-lite")
    assert main(["package", "update", "all", "--json"]) == 0
    payload = json.loads(_out(capsys))
    assert "dice-so-nice-lite" in payload["updated"]
    assert PackageInstallService().get("dice-so-nice-lite")["status"] == "enabled"


def test_campaign_activate_deactivate_flow(db, capsys):
    gm = seed_user(email="pm-campaign@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")
    install_system(gm, package_id="dice-so-nice-lite")

    assert main(["campaign", "package", "activate", campaign, "dice-so-nice-lite"]) == 0
    capsys.readouterr()
    assert main(["campaign", "package", "list", campaign, "--json"]) == 0
    rows = json.loads(_out(capsys))["packages"]
    assert any(r["package_id"] == "dice-so-nice-lite" for r in rows)

    assert main(["campaign", "package", "deactivate", campaign, "dice-so-nice-lite"]) == 0


def test_campaign_activate_unknown_campaign(db, capsys):
    install_system(seed_user(email="pm-ghost@test.com"), package_id="dice-so-nice-lite")
    assert main(["campaign", "package", "activate", "ghost", "dice-so-nice-lite"]) == 1
    assert "campaign not found" in _out(capsys)


def test_package_doctor_reports_enabled(db, capsys):
    install_system(seed_user(email="pm-doctor@test.com"), package_id="dnd5e")
    assert main(["package", "doctor", "dnd5e"]) == 0
    assert "manifest valid" in _out(capsys)
