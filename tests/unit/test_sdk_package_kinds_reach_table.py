from types import SimpleNamespace

from app.engine.sdk.package_asset_service import PackageAssetService
from app.engine.sdk.package_manifest import PackageKind


def _manifest(kind: str):
    return SimpleNamespace(
        id=f"pkg-{kind}",
        kind=kind,
        version="1.0.0",
        capabilities=(f"test.{kind}",),
        raw={"interop": {}},
        entrypoint_styles=lambda entrypoint: [f"styles/{kind}.css"] if entrypoint == "game" else [],
        entrypoint_scripts=lambda entrypoint: [f"scripts/{kind}.js"] if entrypoint == "game" else [],
    )


def test_every_package_kind_is_transmitted_to_the_table(monkeypatch):
    """A mesa recebe todos os kinds pelo mesmo pipeline usado por content packs.

    Ruleset e library possuem fontes especiais; os outros quatro kinds sao
    ativacoes da campanha. O teste cobre tanto o manifesto consumido pelo SDK
    quanto os assets declarados para o entrypoint ``game``.
    """
    service = PackageAssetService()
    optional_kinds = ("addon", "theme", "assets", "content")

    monkeypatch.setattr(
        service.campaigns,
        "get",
        lambda campaign_id: {"id": campaign_id, "active_system_id": "pkg-ruleset"},
    )
    monkeypatch.setattr(
        service.install.installed,
        "list_by_kind",
        lambda kind: [
            {"id": "pkg-library", "kind": "library", "status": "enabled"}
        ] if kind == "library" else [],
    )
    monkeypatch.setattr(
        service.campaign_packages,
        "list_for_campaign",
        lambda campaign_id: [
            {"package_id": f"pkg-{kind}", "status": "active", "load_order": index}
            for index, kind in enumerate(optional_kinds)
        ],
    )

    manifests = {kind: _manifest(kind) for kind in PackageKind.values()}
    records = {
        f"pkg-{kind}": {
            "id": f"pkg-{kind}",
            "kind": kind,
            "status": "enabled",
            "package_dir": f"{kind}/pkg-{kind}",
        }
        for kind in PackageKind.values()
    }
    monkeypatch.setattr(service.install, "get", lambda package_id: records.get(package_id))
    monkeypatch.setattr(
        service,
        "_enabled_record_manifest",
        lambda package_id: (
            records[package_id], manifests[records[package_id]["kind"]]
        ) if package_id in records else None,
    )
    monkeypatch.setattr(service.settings, "definitions", lambda package_id: [])
    monkeypatch.setattr(
        service.settings,
        "effective_values",
        lambda package_id, campaign_id, user_id: {},
    )
    monkeypatch.setattr(service.locales, "get_locale", lambda package_id, locale: {})

    client_manifests = service.list_client_manifests("campaign", user_id="player")
    assets = service.list_assets_for_campaign("campaign", entrypoint="game")

    expected = PackageKind.values()
    assert {item["kind"] for item in client_manifests} == expected
    assert {item["kind"] for item in assets} == expected
    assert all(item["styles"] and item["scripts"] for item in assets)

