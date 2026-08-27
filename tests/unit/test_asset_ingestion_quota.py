import base64

from app.engine.assets.asset_ingestion_service import (
    AssetIngestionService,
    CAMPAIGN_QUOTA_BYTES,
)


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_sdk_campaign_asset_quota_supports_real_vtt_libraries():
    assert CAMPAIGN_QUOTA_BYTES == 1024 * 1024 * 1024


def test_quota_failure_is_not_reported_as_rate_limiting(monkeypatch):
    service = AssetIngestionService()
    monkeypatch.setattr(service.campaigns, "get_member_role", lambda **_kwargs: "gm")
    monkeypatch.setattr(service, "_recent_count", lambda *_args: 0)
    monkeypatch.setattr(service.audit, "record", lambda **_kwargs: None)
    monkeypatch.setattr(
        service.assets,
        "list_for_campaign",
        lambda **_kwargs: [{"byte_size": CAMPAIGN_QUOTA_BYTES}],
    )

    result = service.ingest(
        campaign_id="c1",
        user_id="u1",
        package_id="test-package",
        source={
            "kind": "browser-file",
            "name": "asset.png",
            "mime": "image/png",
            "base64": base64.b64encode(PNG).decode("ascii"),
        },
    )

    assert result.success is False
    assert result.error_key == "QUOTA_EXCEEDED"
