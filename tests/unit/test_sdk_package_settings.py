"""Phase 4 — stable settings coercion.

Boolean coercion is explicit (no ``bool("false") is True``); integer/number/enum
reject invalid input with the stable code ``sdk.settings.invalid_value`` instead
of silently falling back to a default; corrupted stored JSON is reported by the
doctor rather than crashing reads.
"""

from __future__ import annotations

import pytest

from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_manifest import PackageSetting
from app.engine.sdk.package_settings_service import (
    SETTING_INVALID_VALUE,
    PackageSettingsService,
    SettingValueError,
    coerce_setting_value,
)
from app.persistence.repositories.package_setting_repository import (
    PackageSettingRepository,
)
from tests.conftest import install_system, seed_user


def _setting(type_: str, *, default=None, options=None, scope="global") -> PackageSetting:
    return PackageSetting(
        key="opt", scope=scope, type=type_, default=default, options=options or []
    )


# --- boolean -----------------------------------------------------------------


@pytest.mark.parametrize("value", [True, "true", "1", "yes", "on", 1, "TRUE", " on "])
def test_boolean_true_values(value):
    assert coerce_setting_value(_setting("boolean"), value) is True


@pytest.mark.parametrize("value", [False, "false", "0", "no", "off", "", 0, "FALSE"])
def test_boolean_false_values(value):
    assert coerce_setting_value(_setting("boolean"), value) is False


@pytest.mark.parametrize("value", ["maybe", "2", 2, "tru", None, [], {}])
def test_boolean_invalid_value_rejected(value):
    with pytest.raises(SettingValueError):
        coerce_setting_value(_setting("boolean"), value)


# --- enum / integer / number -------------------------------------------------


def test_enum_invalid_value_rejected():
    definition = _setting("enum", options=["a", "b"], default="a")
    assert coerce_setting_value(definition, "b") == "b"
    with pytest.raises(SettingValueError):
        coerce_setting_value(definition, "c")


@pytest.mark.parametrize("value", ["abc", "1.5", None, True, [], "3x"])
def test_integer_invalid_value_rejected(value):
    with pytest.raises(SettingValueError):
        coerce_setting_value(_setting("integer"), value)


def test_integer_valid_values():
    assert coerce_setting_value(_setting("integer"), "42") == 42
    assert coerce_setting_value(_setting("integer"), 42) == 42
    assert coerce_setting_value(_setting("integer"), 7.0) == 7


@pytest.mark.parametrize("value", ["abc", None, True, [], "1.2.3"])
def test_number_invalid_value_rejected(value):
    with pytest.raises(SettingValueError):
        coerce_setting_value(_setting("number"), value)


def test_number_valid_values():
    assert coerce_setting_value(_setting("number"), "1.5") == 1.5
    assert coerce_setting_value(_setting("number"), 3) == 3.0


# --- stable error code -------------------------------------------------------


def test_invalid_setting_returns_stable_error_code():
    with pytest.raises(SettingValueError) as exc:
        coerce_setting_value(_setting("integer"), "not-an-int")
    assert exc.value.error.code == SETTING_INVALID_VALUE


def test_set_invalid_value_returns_failed_action_result(db, monkeypatch):
    service = PackageSettingsService()
    monkeypatch.setattr(
        service, "_definitions", lambda pid: [_setting("boolean", scope="global")]
    )
    result = service.set(
        package_id="pkg", key="opt", value="not-a-bool", campaign_id=None, user_id=None
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == SETTING_INVALID_VALUE


# --- precedence --------------------------------------------------------------


def test_effective_values_precedence_default_campaign_user(db, monkeypatch):
    service = PackageSettingsService()
    repo = PackageSettingRepository()
    monkeypatch.setattr(
        service,
        "_definitions",
        lambda pid: [_setting("string", default="d", scope="user")],
    )

    # No stored rows -> default.
    assert service.effective_values("pkg", "camp", "user")["opt"] == "d"

    # Global row overrides default.
    repo.set(package_id="pkg", setting_key="opt", value_json='"g"', campaign_id=None, user_id=None)
    assert service.effective_values("pkg", "camp", "user")["opt"] == "g"

    # Campaign row overrides global.
    repo.set(package_id="pkg", setting_key="opt", value_json='"c"', campaign_id="camp", user_id=None)
    assert service.effective_values("pkg", "camp", None)["opt"] == "c"

    # User row overrides campaign.
    repo.set(package_id="pkg", setting_key="opt", value_json='"u"', campaign_id=None, user_id="user")
    assert service.effective_values("pkg", "camp", "user")["opt"] == "u"


def test_corrupted_setting_value_does_not_crash_read(db, monkeypatch):
    service = PackageSettingsService()
    repo = PackageSettingRepository()
    monkeypatch.setattr(
        service, "_definitions", lambda pid: [_setting("string", default="safe")]
    )
    repo.set(package_id="pkg", setting_key="opt", value_json="{not json", campaign_id=None, user_id=None)
    # Falls back to the default rather than raising.
    assert service.effective_values("pkg", None, None)["opt"] == "safe"


def test_corrupted_setting_json_is_reported_by_doctor(db):
    gm = seed_user(email="settings-corrupt@test.com")
    install_system(gm, package_id="valid-addon")  # declares the user setting "ui.color"
    PackageSettingRepository().set(
        package_id="valid-addon",
        setting_key="ui.color",
        value_json="{corrupt",
        campaign_id=None,
        user_id=gm,
    )

    findings = PackageDoctorService().audit()
    corrupted = [f for f in findings if f.code == "setting_value_corrupted"]
    assert corrupted, "doctor should report the corrupted setting value"
    assert corrupted[0].package_id == "valid-addon"
