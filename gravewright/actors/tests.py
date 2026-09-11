import uuid
from copy import deepcopy
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase, override_settings
from PIL import Image

from gravewright.journals.services import JournalError
from gravewright.maps.models import Broadcast, Scene
from gravewright.maps.services import MapError
from gravewright.pdf_system.schema import normalize
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.tokens.models import Token

from . import services
from .models import Actor, Asset, Folder


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    ALLOWED_HOSTS=["testserver"],
)
class ActorTests(TransactionTestCase):
    def setUp(self):
        fixtures.SocketTests.setUp(self)
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        override = override_settings(MEDIA_ROOT=temp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.actor = Actor.objects.create(
            campaign=self.campaign, name="Hero", data=normalize({})
        )

    def command(self, action, data, user=None):
        return services.command(
            self.campaign.pk, (user or self.gm).pk, action, data, uuid.uuid4()
        )

    def test_directory_and_sheet_require_explicit_access(self):
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["actors"], [])
        with self.assertRaises(MapError):
            services.sheet(self.campaign.pk, self.player.pk, self.actor.pk)
        self.command(
            "actor.permissions",
            {"id": str(self.actor.pk), "permissions": {str(self.player.pk): "read"}},
        )
        view = services.sheet(self.campaign.pk, self.player.pk, self.actor.pk)
        self.assertFalse(view["canEdit"])
        with self.assertRaises(MapError):
            self.command(
                "sheet.save", {**view, "actorId": str(self.actor.pk)}, self.player
            )
        with self.assertRaises(MapError):
            self.command(
                "actor.permissions",
                {
                    "id": str(self.actor.pk),
                    "permissions": {str(self.outsider.pk): "owner"},
                },
            )
        with self.assertRaises(JournalError):
            services.state(self.campaign.pk, self.outsider.pk)

    def test_player_directory_keeps_shared_actor_folder_ancestors(self):
        parent = Folder.objects.create(campaign=self.campaign, name="Characters")
        child = Folder.objects.create(
            campaign=self.campaign, name="Party", parent=parent
        )
        secret = Folder.objects.create(campaign=self.campaign, name="GM secrets")
        self.actor.folder = child
        self.actor.permissions = {str(self.player.pk): "read"}
        self.actor.save()
        result = services.state(self.campaign.pk, self.player.pk)
        self.assertEqual(result["actors"][0]["folderId"], str(child.pk))
        self.assertEqual(
            {f["id"] for f in result["folders"]}, {str(parent.pk), str(child.pk)}
        )
        self.assertNotIn(str(secret.pk), str(result))

    def test_sheet_conflict_unknown_properties_and_foreign_assets(self):
        value = services.sheet(self.campaign.pk, self.gm.pk, self.actor.pk)
        self.command(
            "sheet.save", {**value, "actorId": str(self.actor.pk), "name": "Changed"}
        )
        with self.assertRaises(MapError):
            self.command(
                "sheet.save", {**value, "actorId": str(self.actor.pk), "name": "Stale"}
            )
        value = services.sheet(self.campaign.pk, self.gm.pk, self.actor.pk)
        value["data"]["pdf"]["asset"] = str(uuid.uuid4())
        with self.assertRaises(MapError):
            self.command("sheet.save", {**value, "actorId": str(self.actor.pk)})
        for bad in [
            {"system": "malicious"},
            {"bars": {"extra": {"value": 1, "max": 2}}},
            {"token": {"size": True}},
            {"fields": {"__proto__": {}}},
            {"pdf": {"zoom": float("inf")}},
        ]:
            with self.assertRaises((MapError, ValueError)):
                normalize(bad)
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.name, "Changed")

    def test_upload_csrf_private_images_and_file_cleanup(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.gm)
        url = f"/api/containers/{self.campaign.pk}/actor-upload"
        self.assertEqual(client.post(url, {}).status_code, 403)
        client.get(f"/game/{self.campaign.pk}")
        csrf = client.cookies["gravewright-csrf"].value
        img = BytesIO()
        Image.new("RGB", (20, 20), "red").save(img, "PNG")
        response = client.post(
            url,
            {
                "kind": "token",
                "actorId": str(self.actor.pk),
                "file": SimpleUploadedFile("token.png", img.getvalue()),
            },
            HTTP_X_CSRF_TOKEN=csrf,
        )
        self.assertEqual(response.status_code, 200, response.content)
        image_url = response.json()["url"]
        asset = Asset.objects.get(pk=response.json()["id"])
        path = asset.file.path
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(image_url).status_code, 404)
        scene = Scene.objects.create(
            campaign=self.campaign, name="Map", width=500, height=500
        )
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        token = Token.objects.create(scene=scene, actor=self.actor)
        self.assertEqual(self.client.get(image_url).status_code, 200)
        token.hidden = True
        token.save()
        self.assertEqual(self.client.get(image_url).status_code, 404)
        self.command("actor.delete", {"id": str(self.actor.pk)})
        from pathlib import Path

        self.assertFalse(Path(path).exists())

    def test_pdf_upload_and_delete_repair_all_sheet_sources(self):
        self.client.force_login(self.gm)
        url = f"/api/containers/{self.campaign.pk}/actor-upload"
        response = self.client.post(
            url, {"file": SimpleUploadedFile("sheet.pdf", b"%PDF-1.4\n%%EOF")}
        )
        self.assertEqual(response.status_code, 200)
        aid = response.json()["id"]
        self.actor.data["pdf"]["asset"] = aid
        self.actor.save()
        scene = Scene.objects.create(
            campaign=self.campaign, name="Map", width=500, height=500
        )
        token = Token.objects.create(
            scene=scene,
            actor=self.actor,
            linked=False,
            snapshot=deepcopy(self.actor.data),
        )
        self.command("asset.delete", {"id": aid})
        self.actor.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual(self.actor.data["pdf"]["asset"], "")
        self.assertEqual(token.snapshot["pdf"]["asset"], "")
        self.assertEqual(token.sheet_version, 2)
        self.client.force_login(self.player)
        self.assertEqual(
            self.client.post(
                url, {"file": SimpleUploadedFile("x.pdf", b"%PDF-1.4")}
            ).status_code,
            400,
        )
