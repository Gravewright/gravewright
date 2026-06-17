from app.business import inside_settings_service as service_module
from app.business.inside_settings_service import InsideSettingsService
from app.business.inside_settings_service import InsideSettingsUpdate
from app.business.inside_settings_service import PrivacySettingsUpdate


def test_inside_settings_persist_app_and_privacy(tmp_path, monkeypatch):
    monkeypatch.setattr(service_module, "SETTINGS_PATH", tmp_path / "inside" / "settings.json")

    service = InsideSettingsService()
    service.update_app(InsideSettingsUpdate(app_name="Mesa Local", default_locale="pt-BR"))
    service.update_privacy(
        PrivacySettingsUpdate(
            enabled=True,
            title="Política da mesa",
            content="Texto público.",
            data_controller="Owner",
            dpo_contact="DPO",
            contact_email="owner@example.com",
            legal_basis="Consentimento.",
            retention_policy="Enquanto a conta existir.",
            data_subject_rights="Acesso, correção e exclusão.",
        )
    )

    settings = service.read()
    assert settings["app"]["app_name"] == "Mesa Local"
    assert settings["app"]["default_locale"] == "pt-BR"
    assert settings["privacy"]["enabled"] is True
    assert settings["privacy"]["title"] == "Política da mesa"
    assert settings["privacy"]["updated_at"]

    login_privacy = service.privacy_for_login()
    assert "Texto público." in login_privacy["content"]
    assert "Consentimento." in login_privacy["content"]
    assert "owner@example.com" in login_privacy["content"]
