"""Binary public APIs retain native validators, ACLs, campaign and mount scope."""
import base64
from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from gravewright.actors.models import Actor, Asset as ActorAsset
from gravewright.campaigns.models import StreamerLink
from gravewright.cards.models import CardAsset
from gravewright.journals import services as journals
from gravewright.journals.models import Access, Asset as JournalAsset, Journal
from gravewright.maps.models import AssetFolder, Broadcast, MapAsset, MapBuilderProject, Scene, Tile
from gravewright.maps.tests import test_builder_projects as map_fixtures
from . import tests as module_fixtures


def image_file():
    with Image.new("RGB", (32, 16), "#428562") as image, BytesIO() as output:
        image.save(output, "PNG")
        return SimpleUploadedFile("synthetic.png", output.getvalue(), content_type="image/png")


def pdf_file():
    path = Path(__file__).resolve().parents[1] / "pdf_system/static/gravewright_pdf_system/assets/blank-a4.pdf"
    return SimpleUploadedFile("synthetic-sheet.pdf", path.read_bytes(), content_type="application/pdf")


def uvtt_file():
    with Image.new("RGB", (32, 32), "#112233") as image, BytesIO() as output:
        image.save(output, "PNG")
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
    raw = {"format": .2, "resolution": {"map_origin": {"x": 0, "y": 0},
           "map_size": {"x": 1, "y": 1}, "pixels_per_grid": 32}, "line_of_sight": [],
           "objects_line_of_sight": [], "portals": [], "lights": [],
           "environment": {"baked_lighting": False, "ambient_light": "ffffffff"}, "image": encoded}
    return SimpleUploadedFile("synthetic.uvtt", json.dumps(raw).encode(), content_type="application/json")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class DomainFileTests(TransactionTestCase):
    asset = map_fixtures.BuilderProjectTests.asset

    def setUp(self):
        map_fixtures.BuilderProjectTests.setUp(self)
        self.campaign.system = "gravewright-pdf-system"
        self.campaign.save(update_fields=["system"])
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="d" * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        self.base = f"/api/tables/{self.campaign.pk}/files"
        self.actor = Actor.objects.create(campaign=self.campaign, name="Owned hero",
                                         permissions={str(self.player.pk): "owner"})

    def upload(self, domain, method, payload=None, file=None, *, request_id=None, **extra):
        metadata = {"domain": domain, "method": method, "payload": payload or {},
                    "requestId": str(request_id or uuid.uuid4()), **extra}
        data = {"metadata": json.dumps(metadata)}
        if file is not None:
            data["file"] = file
        return self.client.post(self.base, data)

    def download(self, domain, method, payload):
        return self.client.post(self.base, {"domain": domain, "method": method, "payload": payload},
                                content_type="application/json")

    def assert_binary(self, response, content_type):
        try:
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)
            self.assertEqual(response["Content-Type"], content_type)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
            return b"".join(response.streaming_content)
        finally:
            response.close()

    def test_library_upload_and_opaque_download_use_native_image_files_and_folder(self):
        folder = AssetFolder.objects.create(campaign=self.campaign, name="Owned files")
        response = self.upload("library", "upload", {"folderId": str(folder.pk)}, image_file())
        self.assertEqual(response.status_code, 201, response.content)
        asset = MapAsset.objects.get(pk=response.json()["value"]["id"])
        self.assertEqual((asset.campaign_id, asset.folder_id, asset.width, asset.height),
                         (self.campaign.pk, folder.pk, 32, 16))
        raw = self.assert_binary(self.download("library", "download", {"id": str(asset.pk)}), "image/png")
        with Image.open(BytesIO(raw)) as image:
            self.assertEqual(image.size, (32, 16))

    def test_map_image_upload_uses_binary_file_not_metadata_and_remains_private(self):
        response = self.upload("maps", "upload", {"name": "Synthetic scene",
            "settings": {"gridSize": 32, "visibility": "gm"}}, image_file())
        self.assertEqual(response.status_code, 201, response.content)
        scene = Scene.objects.get(pk=response.json()["value"]["id"])
        self.assertEqual((scene.width, scene.height, scene.visibility), (32, 16, "gm"))
        self.assertEqual(scene.tiles.count(), 1)
        self.assertFalse(Broadcast.objects.exists())

    def test_uvtt_binary_import_retains_native_receipts_and_editable_project(self):
        rid = uuid.uuid4()
        payload = {"name": "Portable synthetic scene", "builderEditable": True}
        first = self.upload("maps", "importUniversalVtt", payload, uvtt_file(), request_id=rid)
        self.assertEqual(first.status_code, 200, first.content)
        repeated = self.upload("maps", "importUniversalVtt", payload, uvtt_file(), request_id=rid)
        self.assertEqual(repeated.json(), first.json())
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(MapBuilderProject.objects.count(), 1)
        self.assertTrue(first.json()["value"]["builderEditable"])
        self.assertTrue(Tile.objects.exists())
        changed = self.upload("maps", "importUniversalVtt", {**payload, "name": "Different operation"},
                              uvtt_file(), request_id=rid)
        self.assertEqual(changed.status_code, 409, changed.content)

    def test_uploads_reject_players_streamers_nonmembers_and_invalid_binary(self):
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            for domain, method, file in (("maps", "upload", image_file()),
                                         ("maps", "importUniversalVtt", uvtt_file()),
                                         ("library", "upload", image_file()),
                                         ("cards", "uploadAsset", image_file())):
                with self.subTest(user=user.pk, domain=domain, method=method):
                    response = self.upload(domain, method, {"name": "Forbidden"}, file)
                    self.assertEqual(response.status_code, 403, response.content)
        self.client.force_login(self.gm)
        before = MapAsset.objects.count()
        response = self.upload("library", "upload", {}, SimpleUploadedFile("fake.png", b"not an image"))
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(MapAsset.objects.count(), before)
        self.membership.delete()
        self.assertEqual(self.upload("library", "upload", {}, image_file()).status_code, 403)

    def test_actor_owner_can_upload_portrait_but_cannot_upload_templates_or_foreign_portraits(self):
        self.client.force_login(self.player)
        response = self.upload("actors", "uploadImage", {"id": str(self.actor.pk), "kind": "portrait"}, image_file())
        self.assertEqual(response.status_code, 200, response.content)
        asset = ActorAsset.objects.get(pk=response.json()["value"]["id"])
        self.assertEqual((asset.actor_id, asset.kind), (self.actor.pk, "portrait"))
        self.assert_binary(self.download("actors", "downloadAsset", {"id": str(asset.pk)}), "image/png")
        denied = self.upload("actors", "uploadAsset", {}, pdf_file())
        self.assertEqual(denied.status_code, 403, denied.content)
        self.actor.permissions = {str(self.player.pk): "read"}
        self.actor.save(update_fields=["permissions"])
        denied = self.upload("actors", "uploadImage", {"id": str(self.actor.pk), "kind": "token"}, image_file())
        self.assertEqual(denied.status_code, 404, denied.content)

    def test_actor_template_upload_cannot_be_retargeted_to_portrait_by_metadata(self):
        response = self.upload("actors", "uploadAsset", {"actorId": str(self.actor.pk), "kind": "portrait"}, pdf_file())
        self.assertEqual(response.status_code, 200, response.content)
        asset = ActorAsset.objects.get(pk=response.json()["value"]["id"])
        self.assertIsNone(asset.actor_id)
        self.assertEqual(asset.kind, "pdf")
        self.assertTrue(self.assert_binary(self.download("actors", "downloadAsset", {"id": str(asset.pk)}),
                                           "application/pdf").startswith(b"%PDF-"))

    def test_journal_upload_and_download_keep_owner_and_page_visibility_checks(self):
        journal_id = journals.command(self.campaign.pk, self.gm.pk, "create", {"title": "Synthetic journal"}, uuid.uuid4())["journal_id"]
        journal = Journal.objects.get(pk=journal_id)
        Access.objects.create(journal=journal, user=self.player, level="owner")
        self.client.force_login(self.player)
        response = self.upload("journals", "uploadAsset", {"journalId": journal_id}, image_file())
        self.assertEqual(response.status_code, 200, response.content)
        asset = JournalAsset.objects.get(pk=response.json()["value"]["asset_id"])
        self.assertEqual(asset.journal_id, journal.pk)
        self.assert_binary(self.download("journals", "downloadAsset", {"id": str(asset.pk)}), "image/png")
        journal.data["sections"] = [{"id": "private-art", "title": "Secret image", "kind": "image",
                                     "audience": "gm", "assetId": str(asset.pk),
                                     "src": f"/game/journal/asset/{asset.pk}"}]
        journal.save(update_fields=["data"])
        self.assertEqual(self.download("journals", "downloadAsset", {"id": str(asset.pk)}).status_code, 404)
        Access.objects.filter(journal=journal, user=self.player).update(level="read")
        denied = self.upload("journals", "uploadAsset", {"journalId": journal_id}, image_file())
        self.assertEqual(denied.status_code, 404, denied.content)

    def test_foreign_download_ids_remain_unavailable_even_to_member_of_both_campaigns(self):
        other_actor = Actor.objects.create(campaign=self.other, name="Other hero")
        foreign_actor_asset = ActorAsset(campaign=self.other, actor=other_actor, kind="portrait", name="Other image")
        foreign_actor_asset.file.save("foreign.png", image_file(), save=True)
        other_journal = Journal.objects.create(campaign=self.other, creator=self.gm, title="Other journal")
        foreign_journal_asset = JournalAsset(journal=other_journal, uploader=self.gm, name="Other file", content_type="image/png")
        foreign_journal_asset.file.save("foreign.png", image_file(), save=True)
        for domain, method, asset_id in (("library", "download", self.foreign_asset.pk),
                                         ("actors", "downloadAsset", foreign_actor_asset.pk),
                                         ("journals", "downloadAsset", foreign_journal_asset.pk)):
            with self.subTest(domain=domain):
                response = self.download(domain, method, {"id": str(asset_id)})
                self.assertEqual(response.status_code, 404, response.content)
        for domain, method, payload in (("actors", "uploadImage", {"id": str(other_actor.pk), "kind": "portrait"}),
                                         ("journals", "uploadAsset", {"journalId": str(other_journal.pk)})):
            with self.subTest(domain=domain):
                self.assertEqual(self.upload(domain, method, payload, image_file()).status_code, 404)

    def test_cards_upload_creates_reusable_native_asset_and_preserves_limits(self):
        response = self.upload("cards", "uploadAsset", {"purpose": "card_back"}, image_file())
        self.assertEqual(response.status_code, 200, response.content)
        asset = CardAsset.objects.get(pk=response.json()["value"]["id"])
        self.assertEqual((asset.campaign_id, asset.uploader_id, asset.purpose), (self.campaign.pk, self.gm.pk, "card_back"))
        with asset.file.open("rb") as source, Image.open(source) as image:
            self.assertEqual(image.format, "WEBP")
        denied = self.upload("cards", "uploadAsset", {"purpose": "portrait"}, image_file())
        self.assertEqual(denied.status_code, 400, denied.content)
        self.assertEqual(CardAsset.objects.count(), 1)

    def test_transport_rejects_forged_identity_unknown_operation_and_absent_real_file(self):
        for domain, method, extra in (("library", "upload", {"userId": str(self.gm.pk)}),
                                      ("__import__", "upload", {}), ("library", "executeSql", {})):
            response = self.upload(domain, method, {}, image_file(), **extra)
            self.assertIn(response.status_code, (400, 503), response.content)
        response = self.upload("library", "upload", {"file": {"size": 10, "name": "fake.png"}})
        self.assertEqual(response.status_code, 400, response.content)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], ALLOWED_HOSTS=["testserver"])
class MountedDomainFileTests(TestCase):
    package = module_fixtures.ModuleTests.package
    activate = module_fixtures.ModuleTests.activate

    def setUp(self):
        module_fixtures.ModuleTests.setUp(self)
        setting = override_settings(GRAVEWRIGHT_MODULES_ROOT=str(self.host.directory))
        setting.enable()
        self.addCleanup(setting.disable)
        state = self.activate()
        self.base = f"/api/tables/{self.campaign.pk}/modules/example.test"
        self.identity = {"mountId": "domain-files", "moduleSetRevision": state["moduleSetRevision"]}
        response = self.client.post(self.base + "/context", {**self.identity, "action": "open"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)

    def upload(self, **extra):
        return self.client.post(self.base + "/files", {"metadata": json.dumps({
            **self.identity, "domain": "library", "method": "upload", "payload": {}, **extra,
        }), "file": image_file()})

    def test_active_module_can_upload_and_closed_lease_prevents_more_files(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.content)
        self.client.post(self.base + "/context", {"mountId": self.identity["mountId"], "action": "close"}, content_type="application/json")
        response = self.upload()
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error"], "stale_context")
        self.assertEqual(MapAsset.objects.count(), 1)

    def test_stale_activation_revision_and_payload_scene_cannot_extend_mount_scope(self):
        response = self.upload(moduleSetRevision="99999")
        self.assertEqual(response.status_code, 409, response.content)
        self.assertFalse(MapAsset.objects.exists())
        scene = Scene.objects.create(campaign=self.campaign, name="Mounted scene", width=32, height=32)
        self.identity["sceneId"] = str(scene.pk)
        self.identity["mountId"] = "scene-files"
        response = self.client.post(self.base + "/context", {**self.identity, "action": "open"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        response = self.upload(payload={"sceneId": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error"], "stale_context")
        self.assertFalse(MapAsset.objects.exists())
