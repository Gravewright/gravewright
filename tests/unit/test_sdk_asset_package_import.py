from pathlib import Path
from types import SimpleNamespace

from app.engine.sdk.package_asset_import_service import PackageAssetImportService


def test_sync_asset_package_routes_run_off_the_event_loop() -> None:
    source = Path("app/actions/game/manage_assets.py").read_text(encoding="utf-8")
    assert '@get("/game/assets/packages/{campaign_id:str}", sync_to_thread=True)' in source
    assert '@get("/game/assets/packages/{campaign_id:str}/{package_id:str}", sync_to_thread=True)' in source


class _Folders:
    def __init__(self):
        self.rows = []

    def list_for_campaign(self, *, campaign_id):
        return list(self.rows)


class _Assets:
    def __init__(self):
        self.rows = []

    def list_for_campaign(self, *, campaign_id):
        return list(self.rows)


class _Library:
    def __init__(self):
        self.folders = _Folders()
        self.assets = _Assets()
        self.created = []

    def create_folder(self, **kwargs):
        folder = {"id": "assets-folder", "name": kwargs["name"], "parent_id": None}
        self.folders.rows.append(folder)
        return SimpleNamespace(success=True, payload={"folder": folder})

    def create_asset(self, **kwargs):
        digest = __import__("hashlib").sha256(kwargs["data"]).hexdigest()
        self.created.append(kwargs)
        asset = {"id": "imported", "hash": digest, "folder_id": kwargs["folder_id"]}
        self.assets.rows.append(asset)
        return SimpleNamespace(success=True, payload={"asset": asset})


class _Install:
    def get(self, package_id):
        return {"package_dir": "assets/sample-assets", "status": "enabled", "name": "Sample Assets"}

    def get_manifest(self, package_id):
        provides = SimpleNamespace(
            asset_entries=lambda: [
                (
                    "images",
                    {
                        "id": "sample-banner",
                        "label": "Banner",
                        "folder": "Examples/Maps",
                        "path": "assets/sample-banner.webp",
                    },
                )
            ]
        )
        return SimpleNamespace(kind="assets", provides=provides)


def test_asset_package_goes_to_assets_folder_without_duplicates(tmp_path, monkeypatch):
    package = tmp_path / "assets" / "sample-assets" / "assets"
    package.mkdir(parents=True)
    (package / "sample-banner.webp").write_bytes(b"RIFF-test-webp")
    monkeypatch.setattr(
        "app.engine.sdk.package_asset_import_service.package_registry.PACKAGES_DIR", tmp_path
    )
    library = _Library()
    service = PackageAssetImportService(install=_Install(), library=library)

    assert service.import_package(campaign_id="campaign", package_id="sample-assets", user_id="gm")
    assert library.folders.rows[0]["name"] == "Assets"
    assert library.created[0]["folder_id"] == "assets-folder"

    assert service.import_package(campaign_id="campaign", package_id="sample-assets", user_id="gm")
    assert len(library.created) == 1


class _Campaigns:
    def get_member_role(self, *, campaign_id, user_id):
        return "gm"


class _CampaignPackages:
    def list_for_campaign(self, campaign_id):
        return [{"package_id": "sample-assets", "activation_role": "assets", "status": "active"}]

    def get(self, *, campaign_id, package_id):
        return {"package_id": package_id, "activation_role": "assets", "status": "active"}


def test_active_asset_package_can_be_browsed_and_imported(tmp_path, monkeypatch):
    package = tmp_path / "assets" / "sample-assets" / "assets"
    package.mkdir(parents=True)
    (package / "sample-banner.webp").write_bytes(b"RIFF-test-webp")
    monkeypatch.setattr(
        "app.engine.sdk.package_asset_import_service.package_registry.PACKAGES_DIR", tmp_path
    )
    library = _Library()
    service = PackageAssetImportService(
        install=_Install(),
        library=library,
        campaigns=_Campaigns(),
        campaign_packages=_CampaignPackages(),
    )

    assert service.list_active_packages(campaign_id="campaign", user_id="gm") == [
        {"id": "sample-assets", "name": "Sample Assets"}
    ]
    entries = service.list_entries(
        campaign_id="campaign", package_id="sample-assets", user_id="gm"
    )
    assert entries[0]["id"] == "sample-banner"
    imported = service.import_entry(
        campaign_id="campaign",
        package_id="sample-assets",
        asset_id="sample-banner",
        user_id="gm",
    )
    assert imported and imported["id"] == "imported"
    assert library.created[0]["folder_id"] == "assets-folder"
    assert [folder["name"] for folder in library.folders.rows] == ["Examples", "Maps"]
