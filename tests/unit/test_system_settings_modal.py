from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
NAVIGATION = (ROOT / "static/js/game/settings-navigation.js").read_text(encoding="utf-8")


def test_core_owns_system_modal_and_exposes_ruleset_slot() -> None:
    assert 'data-sdk-slot="settings.system"' in TEMPLATE
    assert '["system", "modules"]' in NAVIGATION
    assert 'playersSection.dataset.systemTrayRoom = roomId' in NAVIGATION


def test_general_modal_combines_interface_and_administration() -> None:
    assert 'sectionName: "general", sourceSectionName: "interface", title: generalTitle' in NAVIGATION
    assert '{ id: "interface", label: labels.interface' in NAVIGATION
    assert "separator.textContent = labels.administration" in NAVIGATION
    assert 'data-settings-section-tab="management"' in NAVIGATION
    assert "prepareAdministration(managementSection, navigation, content, labels" in NAVIGATION
    assert "administration-settings-detail" in NAVIGATION
    assert 'button.classList.remove("settings-open-modal", "settings-open-modal--primary")' in NAVIGATION
    assert 'data-modal-open="invite-{{ room.id }}"' not in TEMPLATE
    assert 'data-modal-id="invite-{{ room.id }}"' not in TEMPLATE
    assert "/static/js/ui/invitations.js" not in TEMPLATE


def test_identity_color_is_owned_only_by_system_tray() -> None:
    assert TEMPLATE.count("data-ping-color-input") == 1
    assert "data-player-identity-color" in TEMPLATE


def test_modules_modal_uses_three_to_nine_layout_and_package_slot() -> None:
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")
    assert 'data-sdk-slot="settings.modules"' in TEMPLATE
    assert "data-modules-packages='{{ room.installed_modules | tojson }}'" in TEMPLATE
    assert 'data-modules-packages="{{ room.installed_modules | tojson | e }}"' not in TEMPLATE
    assert "data-modules-packages" in TEMPLATE
    assert "grid-template-columns: minmax(190px, 3fr) minmax(0, 9fr)" in css
    assert "max-height: calc(100vh - 48px)" in css
    assert 'root.dataset.sdkPackage === selectedId' in NAVIGATION
