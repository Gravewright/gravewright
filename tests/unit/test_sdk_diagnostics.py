"""Phase 1 — SDK diagnostics contract.

These tests pin the *shape* and *machine-readability* of the common SDK
diagnostics contract. They assert on stable ``code`` values and structured
fields, never on human-readable ``message`` text.
"""

from __future__ import annotations

from app.engine.sdk.diagnostics import (
    SDK_ERROR_CODES,
    DoctorFinding,
    SdkActionResult,
    SdkError,
    is_known_namespace,
    is_machine_readable_code,
)


def test_sdk_error_has_stable_shape():
    error = SdkError(
        code="sdk.manifest.id_mismatch",
        message="anything human",
        details={"expected": "foo", "actual": "bar"},
        package_id="foo",
        campaign_id="camp-1",
    )

    data = error.to_dict()
    assert data["code"] == "sdk.manifest.id_mismatch"
    assert data["details"] == {"expected": "foo", "actual": "bar"}
    assert data["package_id"] == "foo"
    assert data["campaign_id"] == "camp-1"
    # Optional fields are omitted, not null, when absent.
    bare = SdkError(code="sdk.manifest.missing").to_dict()
    assert "package_id" not in bare
    assert "campaign_id" not in bare
    assert "details" not in bare


def test_sdk_action_result_has_stable_shape():
    ok = SdkActionResult.ok(package_id="foo")
    assert ok.success is True
    assert ok.to_dict() == {"success": True, "package_id": "foo"}

    error = SdkError(code="sdk.capabilities.forbidden", package_id="foo")
    failed = SdkActionResult.fail(error)
    assert failed.success is False
    assert failed.package_id == "foo"
    assert failed.error is error
    assert failed.to_dict()["error"]["code"] == "sdk.capabilities.forbidden"


def test_doctor_finding_has_stable_shape():
    finding = DoctorFinding(
        code="sdk.storage.path_forbidden",
        severity="error",
        message="human",
        details={"path": "x"},
        package_id="foo",
        campaign_id="camp-1",
    )

    data = finding.to_dict()
    assert data["code"] == "sdk.storage.path_forbidden"
    assert data["severity"] == "error"
    assert data["details"] == {"path": "x"}
    assert data["package_id"] == "foo"
    assert data["campaign_id"] == "camp-1"


def test_error_codes_are_machine_readable():
    # Every catalogued code matches the strict identifier shape and lives under a
    # declared public namespace.
    assert SDK_ERROR_CODES, "code catalogue must not be empty"
    for code in SDK_ERROR_CODES:
        assert is_machine_readable_code(code), code
        assert is_known_namespace(code), code

    # Counter-examples: human text and unknown namespaces are rejected.
    assert not is_machine_readable_code("Invalid manifest!")
    assert not is_machine_readable_code("sdk..manifest")
    assert not is_machine_readable_code("manifest.id_mismatch")
    assert not is_known_namespace("sdk.bogus.thing")


def test_new_services_do_not_return_error_key_as_primary_contract():
    # Guard rail: the diagnostics module — the contract every SDK service speaks
    # — must not expose an ``error_key`` field on any of its structured types.
    # SDK services return SdkError/SdkActionResult/DoctorFinding; ``error_key``
    # is only the HTTP-boundary mirror of the structured ``code``.
    for cls in (SdkError, SdkActionResult, DoctorFinding):
        annotations = getattr(cls, "__annotations__", {})
        assert "error_key" not in annotations, cls.__name__
    assert SdkError(code="sdk.manifest.missing").to_dict().keys() <= {
        "code",
        "message",
        "details",
        "package_id",
        "campaign_id",
    }
