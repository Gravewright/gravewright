"""Card artwork imports use public module leases and native image services."""

import io
import json
import uuid
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.cards.models import CardAsset, Deck, DeckDefinition

from .packages import CONTRACTS
from . import tests as fixtures


class CardAssetUploadTests(TestCase):
    package = fixtures.ModuleTests.package
    activate = fixtures.ModuleTests.activate

    def setUp(self):
        fixtures.ModuleTests.setUp(self)
        setting = override_settings(GRAVEWRIGHT_MODULES_ROOT=str(self.host.directory))
        setting.enable()
        self.addCleanup(setting.disable)
        self.state = self.activate()
        self.base = f"/api/tables/{self.campaign.pk}/modules/example.test"
        self.identity = {
            "mountId": "customization-assets",
            "moduleSetRevision": self.state["moduleSetRevision"],
        }
        self.assertEqual(self.open_context().status_code, 200)

    def open_context(self):
        return self.client.post(
            self.base + "/context", {"action": "open", **self.identity},
            content_type="application/json",
        )

    def image(self, image_format="PNG", size=(2, 3)):
        raw = io.BytesIO()
        Image.new("RGB", size, "#428562").save(raw, format=image_format)
        return SimpleUploadedFile(
            f"image.{image_format.lower()}", raw.getvalue(),
            content_type=f"image/{image_format.lower()}",
        )

    def upload(self, image_file=None, purpose="card_front", **extra):
        return self.client.post(self.base + "/call", {
            "metadata": json.dumps({
                **self.identity, "name": "card.asset.upload",
                "payload": {"purpose": purpose, **extra},
            }),
            "file": image_file if image_file is not None else self.image(),
        })

    def cards(self, method, payload):
        return self.client.post(self.base + "/api", {
            **self.identity, "domain": "cards", "method": method,
            "payload": payload, "requestId": str(uuid.uuid4()),
        }, content_type="application/json")

    def files(self):
        return list((Path(self.temp.name) / "cards").rglob("*.webp"))

    def test_supported_images_and_back_are_native_campaign_assets(self):
        for image_format in ("PNG", "JPEG", "WEBP"):
            with self.subTest(image_format=image_format):
                response = self.upload(self.image(image_format))
                self.assertEqual(response.status_code, 200, response.content)
                asset = CardAsset.objects.get(pk=response.json()["value"]["assetId"])
                self.assertEqual(asset.campaign_id, self.campaign.pk)
                self.assertEqual(asset.uploader_id, self.user.pk)
                self.assertEqual(asset.purpose, "card_front")
                with asset.file.open("rb") as source, Image.open(source) as image:
                    self.assertEqual(image.format, "WEBP")
                    self.assertEqual(image.size, (2, 3))
        response = self.upload(purpose="card_back")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(CardAsset.objects.get(pk=response.json()["value"]["assetId"]).purpose, "card_back")
        self.assertEqual(len(self.files()), 4)

    def test_define_and_instantiate_reuse_images_through_same_lease(self):
        front = self.upload().json()["value"]["assetId"]
        back = self.upload(purpose="card_back").json()["value"]["assetId"]
        response = self.cards("define", {
            "name": "Custom cards", "default_back_asset_id": back,
            "cards": [{"name": "One", "front_asset_id": front}],
        })
        self.assertEqual(response.status_code, 200, response.content)
        definition = response.json()["value"]["deck"]["id"]
        decks = []
        for _ in range(2):
            response = self.cards("instantiate", {"deck_definition_id": definition})
            self.assertEqual(response.status_code, 200, response.content)
            deck = Deck.objects.get(pk=response.json()["value"]["id"])
            decks.append(deck)
            self.assertEqual(deck.cards.get().front.name, CardAsset.objects.get(pk=front).file.name)
            self.assertEqual(deck.back.name, CardAsset.objects.get(pk=back).file.name)
        self.assertEqual(len(self.files()), 2)
        response = self.cards("deleteDeck", {
            "deck_instance_id": str(decks[0].pk), "version": decks[0].version,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(self.files()), 2)
        self.assertTrue(decks[1].cards.get().front.storage.exists(decks[1].cards.get().front.name))

    def test_player_and_nonmember_cannot_upload(self):
        for is_member in (True, False):
            with self.subTest(is_member=is_member):
                user = User.objects.create_user(
                    email=f"participant-{is_member}@modules.test", name="Participant",
                    password="test-password-123",
                )
                if is_member:
                    Membership.objects.create(campaign=self.campaign, user=user, role="player")
                self.client.force_login(user)
                opened = self.open_context()
                self.assertEqual(opened.status_code, 200 if is_member else 404)
                response = self.upload()
                self.assertEqual(response.status_code, 403 if is_member else 404, response.content)
                if is_member:
                    self.assertEqual(response.json()["error"], "permission_denied")
                self.assertEqual(CardAsset.objects.count(), 0)
                self.assertEqual(self.files(), [])

    def test_closed_lease_prevents_file_creation(self):
        self.client.post(self.base + "/context", {
            "action": "close", "mountId": self.identity["mountId"],
        }, content_type="application/json")
        response = self.upload()
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error"], "stale_context")
        self.assertEqual(CardAsset.objects.count(), 0)
        self.assertEqual(self.files(), [])

    def test_schema_rejects_invalid_purpose_scope_and_missing_binary(self):
        for payload in ({"purpose": "portrait"}, {"campaignId": str(uuid.uuid4())}):
            with self.subTest(payload=payload):
                response = self.upload(**payload)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"], "invalid_data")
        response = self.client.post(self.base + "/call", {
            **self.identity, "name": "card.asset.upload", "payload": {
                "purpose": "card_front", "file": {
                    "name": "fake.png", "contentType": "image/png", "size": 10,
                },
            },
        }, content_type="application/json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(CardAsset.objects.count(), 0)
        self.assertEqual(self.files(), [])

    def test_native_image_validator_rejects_fake_oversized_and_large_images(self):
        invalid = [
            SimpleUploadedFile("fake.png", b"not an image", content_type="image/png"),
            SimpleUploadedFile("huge.png", b"x" * (10 * 1024 * 1024 + 1), content_type="image/png"),
            self.image(size=(4001, 4000)),
        ]
        for file in invalid:
            with self.subTest(name=file.name, size=file.size):
                response = self.upload(file, file={"size": 0, "name": "lie.png", "contentType": "image/png"})
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"], "invalid_data")
                self.assertEqual(CardAsset.objects.count(), 0)
                self.assertEqual(self.files(), [])

    def test_failed_native_save_removes_uploaded_file_and_database_row(self):
        from gravewright.maps.services import MapError

        with patch.object(CardAsset, "save", side_effect=MapError("Resource unavailable.")):
            response = self.upload()
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(CardAsset.objects.count(), 0)
        self.assertEqual(self.files(), [])

    def test_foreign_table_asset_cannot_be_used_in_native_definition(self):
        other = Campaign.objects.create(owner=self.user, name="Other table")
        Membership.objects.create(campaign=other, user=self.user, role="gm")
        front = self.upload().json()["value"]["assetId"]
        CardAsset.objects.filter(pk=front).update(campaign=other)
        response = self.cards("define", {
            "name": "Foreign image", "cards": [{"name": "One", "front_asset_id": front}],
        })
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(DeckDefinition.objects.count(), 0)

    def test_operation_constants_and_protocol_document_match_registry(self):
        registry = json.loads((CONTRACTS / "registry.json").read_text(encoding="utf-8"))
        generated = (CONTRACTS.parent / "static/gravewright_modules/generated.js").read_text(encoding="utf-8")
        transports = json.loads(generated.split("const OPERATION_TRANSPORTS = ")[1].split(";", 1)[0])
        self.assertEqual(transports, {name: operation.get("transport", "json") for name, operation in registry["operations"].items()})
        for name, domain in registry["domains"].items():
            with self.subTest(domain=name):
                self.assertIn("card.asset.upload", domain["operations"])
        self.host.contracts.validate("schemas/protocol.json", json.loads((CONTRACTS / "api.json").read_text(encoding="utf-8")))
