import base64
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership

from .models import Package
from .packages import ModuleFailure, ModulePackages, canonical


class ModuleTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.key = Ed25519PrivateKey.generate()
        keys = {
            "test": base64.b64encode(self.key.public_key().public_bytes_raw()).decode()
        }
        keyfile = Path(self.temp.name) / "keys.json"
        keyfile.write_text(json.dumps(keys))
        setting = override_settings(
            MEDIA_ROOT=self.temp.name, GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=str(keyfile)
        )
        setting.enable()
        self.addCleanup(setting.disable)
        self.host = ModulePackages(Path(self.temp.name) / "modules", keys)
        self.user = User.objects.create_user(
            email="owner@modules.test",
            name="Owner",
            password="test-password-123",
            role="owner",
        )
        self.campaign = Campaign.objects.create(owner=self.user, name="Modules")
        Membership.objects.create(campaign=self.campaign, user=self.user, role="gm")
        self.client.force_login(self.user)

    def package(self, files=None):
        manifest = {
            "id": "example.test",
            "version": "1.0.0",
            "name": "Test",
            "description": "Test module",
            "author": "Test",
            "license": "MIT",
            "sdk": {"requires": ">=1.0.0 <2.0.0", "tested": "1.0.0"},
            "entry": "main.js",
        }
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("main.js", "export default {start(){},stop(){}}")
            for name, raw in (files or {}).items():
                archive.writestr(name, raw)
        raw = out.getvalue()
        record = {
            "id": manifest["id"],
            "version": "1.0.0",
            "sdk": manifest["sdk"]["requires"],
            "download": "https://example.test/module.zip",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "keyId": "test",
        }
        record["signature"] = base64.b64encode(
            self.key.sign(canonical(record))
        ).decode()
        return record, raw

    def activate(self):
        record, raw = self.package()
        self.host.install(record, raw)
        return self.host.configure(self.campaign.pk, {"example.test": "1.0.0"}, {}, "0")

    def test_signature_digest_and_zip_traversal(self):
        record, raw = self.package()
        with self.assertRaises(ModuleFailure):
            self.host.install(record, raw + b"changed")
        record["signature"] = base64.b64encode(b"x" * 64).decode()
        with self.assertRaises(ModuleFailure):
            self.host.install(record, raw)
        record, raw = self.package({"../escape.js": "bad"})
        with self.assertRaises(ModuleFailure):
            self.host.install(record, raw)
        self.assertEqual(Package.objects.count(), 0)

    def test_activation_rechecks_bytes_and_revision(self):
        state = self.activate()
        with self.assertRaises(ModuleFailure):
            self.host.configure(self.campaign.pk, {}, {}, "0")
        row = Package.objects.get()
        path = (
            self.host.directory
            / "packages"
            / row.module_id
            / row.version
            / row.digest
            / "main.js"
        )
        path.write_text("changed")
        with self.assertRaises(ModuleFailure):
            self.host.configure(
                self.campaign.pk,
                {"example.test": "1.0.0"},
                {},
                state["moduleSetRevision"],
            )

    def test_revision_checked_storage_and_revocation(self):
        state = self.activate()
        rev = state["moduleSetRevision"]
        value = self.host.storage(
            self.campaign.pk, "example.test", "", rev, "set", "key", {"a": 1}
        )
        with self.assertRaises(ModuleFailure):
            self.host.storage(
                self.campaign.pk, "example.test", "", rev, "set", "key", {"a": 2}
            )
        self.assertEqual(
            self.host.storage(self.campaign.pk, "example.test", "", rev, "get", "key"),
            value,
        )
        record, _ = self.package()
        record["status"] = "revoked"
        record["signature"] = base64.b64encode(
            self.key.sign(canonical(record))
        ).decode()
        self.host.revoke(record)
        self.assertEqual(self.host.state(self.campaign.pk)["modules"], [])
        with self.assertRaises(ModuleFailure):
            self.host.storage(self.campaign.pk, "example.test", "", rev, "get", "key")

    def test_sdk_calls_and_closed_context(self):
        state = self.activate()
        base = f"/api/tables/{self.campaign.pk}/modules/example.test"
        identity = {
            "mountId": "test-mount",
            "moduleSetRevision": state["moduleSetRevision"],
        }
        response = self.client.post(
            base + "/context",
            {"action": "open", **identity},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.post(
            base + "/call",
            {**identity, "name": "actor.create", "payload": {"name": "SDK Hero"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        actor = response.json()["value"]
        response = self.client.post(
            base + "/call",
            {
                **identity,
                "name": "actor.update",
                "payload": {
                    "id": actor["id"],
                    "expectedRevision": actor["revision"],
                    "changes": {"name": "Updated"},
                },
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["value"]["name"], "Updated")
        self.client.post(
            base + "/context",
            {"action": "close", "mountId": "test-mount"},
            content_type="application/json",
        )
        response = self.client.post(
            base + "/call",
            {**identity, "name": "actor.list", "payload": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)

    def test_player_cannot_configure_or_write_table_storage(self):
        state = self.activate()
        player = User.objects.create_user(
            email="player@modules.test", name="Player", password="test-password-123"
        )
        Membership.objects.create(campaign=self.campaign, user=player, role="player")
        self.client.force_login(player)
        base = f"/api/tables/{self.campaign.pk}/modules"
        self.assertEqual(
            self.client.post(
                base,
                {
                    "modules": {},
                    "replacements": {},
                    "expectedRevision": state["moduleSetRevision"],
                },
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/marketplace").status_code, 403)
        response = self.client.post(
            base + "/example.test/storage",
            {
                "scope": "table",
                "action": "set",
                "key": "key",
                "value": 1,
                "mountId": "test",
                "moduleSetRevision": state["moduleSetRevision"],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_sdk_upload_and_player_wall_validation(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from gravewright.actors.models import Actor
        from gravewright.maps.models import Broadcast, Scene, SceneObject
        from gravewright.pdf_system.schema import normalize
        from gravewright.tokens.models import Token

        state = self.activate()
        base = f"/api/tables/{self.campaign.pk}/modules/example.test"
        identity = {
            "mountId": "upload",
            "moduleSetRevision": state["moduleSetRevision"],
        }
        self.client.post(
            base + "/context",
            {"action": "open", **identity},
            content_type="application/json",
        )
        response = self.client.post(
            base + "/call",
            {
                "metadata": json.dumps(
                    {**identity, "name": "asset.upload", "payload": {}}
                ),
                "file": SimpleUploadedFile(
                    "sheet.pdf", b"%PDF-1.7\n", content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["value"]["contentType"], "application/pdf")
        player = User.objects.create_user(
            email="mover@modules.test", name="Mover", password="test-password-123"
        )
        Membership.objects.create(campaign=self.campaign, user=player)
        scene = Scene.objects.create(
            campaign=self.campaign, name="Room", width=700, height=700
        )
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        actor = Actor.objects.create(
            campaign=self.campaign,
            name="Hero",
            data=normalize({}),
            permissions={str(player.pk): "owner"},
        )
        token = Token.objects.create(scene=scene, actor=actor, grid_x=1, grid_y=1)
        SceneObject.objects.create(
            scene=scene,
            kind="walls",
            data={
                "kind": "wall",
                "x1": 140,
                "y1": 0,
                "x2": 140,
                "y2": 700,
                "movement_behavior": "block",
            },
        )
        self.client.force_login(player)
        identity = {
            "mountId": "move",
            "moduleSetRevision": state["moduleSetRevision"],
            "sceneId": str(scene.pk),
        }
        self.client.post(
            base + "/context",
            {"action": "open", **identity},
            content_type="application/json",
        )
        response = self.client.post(
            base + "/call",
            {**identity, "name": "token.read", "payload": {"id": str(token.pk)}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        revision = response.json()["value"]["revision"]
        response = self.client.post(
            base + "/call",
            {
                **identity,
                "name": "token.move",
                "payload": {
                    "id": str(token.pk),
                    "expectedRevision": revision,
                    "position": {"x": 245, "y": 105},
                },
            },
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 1)

    def test_marketplace_install_endpoint_verifies_catalog_and_package(self):
        from unittest.mock import patch

        record, raw = self.package()
        with override_settings(
            GRAVEWRIGHT_MARKETPLACE_URL="https://example.test/catalog.json"
        ):
            with patch(
                "gravewright.modules.views.download",
                side_effect=lambda url, limit: (
                    json.dumps([record]).encode()
                    if url.endswith("catalog.json")
                    else raw
                ),
            ):
                response = self.client.post(
                    "/api/marketplace/install",
                    {"id": record["id"], "version": record["version"]},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(Package.objects.get().digest, record["sha256"])
