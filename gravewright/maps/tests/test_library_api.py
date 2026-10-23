"""The extracted file library retains native projection and transactional cleanup."""
from datetime import timedelta
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import uuid

from django.db import transaction
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from api import library
from gravewright.campaigns.models import Membership, StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import builder_services, extra_objects, library_services, objects, services
from gravewright.maps.models import (AssetFolder, Broadcast, MapAsset, MapBuilderProject,
                                    Receipt, Scene, SceneObject)
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class LibraryApiTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="e" * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))

    def command(self, action, payload, *, request_id=None, user=None):
        return library.command(self.campaign.pk, (user or self.gm).pk, action, payload, request_id or uuid.uuid4())

    def test_facade_aliases_and_folder_crud_support_retry_without_duplicate_folders(self):
        self.assertIs(library.state, library_services.state)
        self.assertIs(library.command, library_services.command)
        rid = uuid.uuid4()
        created = self.command("folder-create", {"name": "Reusable images"}, request_id=rid)
        self.assertEqual(self.command("folder-create", {"name": "Reusable images"}, request_id=rid), created)
        self.assertEqual(AssetFolder.objects.count(), 1)
        self.command("folder-rename", {"folderId": created["id"], "name": "Renamed images"})
        self.command("move", {"assetId": str(self.floor.pk), "folderId": created["id"]})
        self.floor.refresh_from_db()
        self.assertEqual(str(self.floor.folder_id), created["id"])
        self.assertEqual(library.state(self.campaign.pk, self.gm.pk)["folders"][0]["name"], "Renamed images")
        self.command("folder-delete", {"folderId": created["id"]})
        self.floor.refresh_from_db()
        self.assertIsNone(self.floor.folder_id)
        self.assertFalse(AssetFolder.objects.exists())

    def test_folder_mutations_deliver_after_commit_and_outer_rollback_has_no_receipt(self):
        with patch("gravewright.maps.views.notify") as notify, patch("gravewright.table.media.announce") as announce:
            with self.captureOnCommitCallbacks(execute=True):
                created = self.command("folder-create", {"name": "Committed"})
                notify.assert_not_called()
                announce.assert_not_called()
            notify.assert_called_once_with(self.campaign.pk)
            announce.assert_called_once_with(self.campaign.pk)
        rid = uuid.uuid4()
        with patch("gravewright.maps.views.notify") as notify, patch("gravewright.table.media.announce"):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        self.command("folder-rename", {"folderId": created["id"], "name": "Rolled back"}, request_id=rid)
                        raise RuntimeError("Abort integration")
            notify.assert_not_called()
        self.assertEqual(AssetFolder.objects.get(pk=created["id"]).name, "Committed")
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())

    def test_current_membership_is_checked_before_replaying_old_receipt(self):
        rid = uuid.uuid4()
        self.command("folder-create", {"name": "Owned"}, request_id=rid)
        Membership.objects.filter(pk=self.membership.pk).update(role="player")
        with self.assertRaises(services.MapError):
            self.command("folder-create", {"name": "Owned"}, request_id=rid)
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), self.assertRaises((services.MapError, JournalError)):
                self.command("delete", {"assetId": str(self.floor.pk)}, user=user)
        self.membership.delete()
        with self.assertRaises(JournalError):
            library.state(self.campaign.pk, self.gm.pk)

    def test_foreign_assets_and_folders_cannot_be_modified_even_by_gm_of_both_campaigns(self):
        foreign_folder = AssetFolder.objects.create(campaign=self.other, name="Other files")
        for action, payload in (("delete", {"assetId": str(self.foreign_asset.pk)}),
                                ("move", {"assetId": str(self.floor.pk), "folderId": str(foreign_folder.pk)}),
                                ("folder-rename", {"folderId": str(foreign_folder.pk), "name": "Stolen"}),
                                ("folder-delete", {"folderId": str(foreign_folder.pk)})):
            with self.subTest(action=action), self.assertRaises(services.MapError):
                self.command(action, payload)
        self.assertTrue(MapAsset.objects.filter(pk=self.foreign_asset.pk).exists())
        self.assertTrue(self.foreign_asset.file.storage.exists(self.foreign_asset.file.name))
        self.assertEqual(AssetFolder.objects.get(pk=foreign_folder.pk).name, "Other files")
        self.assertFalse(Receipt.objects.exists())

    def test_non_gm_state_exposes_only_visible_assets_in_broadcast_scene_and_their_folders(self):
        visible_folder = AssetFolder.objects.create(campaign=self.campaign, name="Visible")
        hidden_folder = AssetFolder.objects.create(campaign=self.campaign, name="Hidden")
        self.floor.folder = visible_folder
        self.floor.save(update_fields=["folder"])
        self.wall.folder = hidden_folder
        self.wall.save(update_fields=["folder"])
        scene = Scene.objects.create(campaign=self.campaign, name="Broadcast", width=32, height=32, visibility="players")
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        for asset, layer in ((self.floor, "map"), (self.wall, "gm")):
            SceneObject.objects.create(scene=scene, kind="images", data=extra_objects.image(scene, {
                "asset_id": str(asset.pk), "x": 16, "y": 8, "layer": layer,
            }))
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk):
                state = library.state(self.campaign.pk, user.pk)
                self.assertEqual([row["id"] for row in state["assets"]], [str(self.floor.pk)])
                self.assertEqual([row["id"] for row in state["folders"]], [str(visible_folder.pk)])
        scene.visibility = "gm"
        scene.save(update_fields=["visibility"])
        self.assertEqual(library.state(self.campaign.pk, self.player.pk), {"assets": [], "folders": []})

    def test_generated_surfaces_are_neither_library_entries_nor_movable_deletable_assets(self):
        scene = Scene.objects.create(campaign=self.campaign, name="Generated", width=32, height=32)
        surface = MapAsset.objects.create(campaign=self.campaign, generated_for=scene,
            name="Internal surface", width=16, height=16, file=self.floor.file.name)
        state = library.state(self.campaign.pk, self.gm.pk)
        self.assertNotIn(str(surface.pk), {row["id"] for row in state["assets"]})
        for action in ("delete", "move"):
            with self.subTest(action=action), self.assertRaises(services.MapError):
                self.command(action, {"assetId": str(surface.pk)})
        self.assertTrue(MapAsset.objects.filter(pk=surface.pk).exists())
        self.assertTrue(surface.file.storage.exists(surface.file.name))

    def test_asset_delete_detaches_builder_art_and_placements_but_preserves_door_geometry_until_commit(self):
        source = builder_services.save(self.campaign.pk, self.gm.pk, self.project_id, {
            "request_id": str(uuid.uuid4()), "expected_version": 0,
            "folder_id": str(self.folder.pk), "document": self.doc,
        })["project"]
        scene = Scene.objects.create(campaign=self.campaign, name="Scene", width=128, height=128)
        picture = SceneObject.objects.create(scene=scene, kind="images", data=extra_objects.image(scene, {
            "asset_id": str(self.door.pk), "x": 32, "y": 32,
        }))
        data = {**objects.wall({"kind": "door", "x1": 0, "y1": 20, "x2": 64, "y2": 20}),
                "asset_id": str(self.door.pk), "thickness": 16}
        door = SceneObject.objects.create(scene=scene, kind="walls", data=data)
        storage, path = self.door.file.storage, self.door.file.name
        with patch("gravewright.maps.views.notify"), patch("gravewright.table.media.announce"):
            with self.captureOnCommitCallbacks(execute=True):
                self.command("delete", {"assetId": str(self.door.pk)})
                self.assertTrue(storage.exists(path))
                self.assertFalse(MapAsset.objects.filter(pk=self.door.pk).exists())
            self.assertFalse(storage.exists(path))
        self.assertFalse(SceneObject.objects.filter(pk=picture.pk).exists())
        door.refresh_from_db()
        self.assertEqual((door.data["kind"], door.data["x1"], door.data["x2"], door.data["door_state"]),
                         ("door", 0, 64, "closed"))
        self.assertNotIn("asset_id", door.data)
        project = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(project.version, source["version"] + 1)
        self.assertNotIn(str(self.door.pk), json.dumps(project.document))

    def test_rolled_back_asset_delete_keeps_file_and_data_and_suppresses_delivery(self):
        storage, path = self.floor.file.storage, self.floor.file.name
        rid = uuid.uuid4()
        with patch("gravewright.maps.views.notify") as notify, patch("gravewright.table.media.announce"):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        self.command("delete", {"assetId": str(self.floor.pk)}, request_id=rid)
                        raise RuntimeError("Abort integration")
            notify.assert_not_called()
        self.assertTrue(MapAsset.objects.filter(pk=self.floor.pk).exists())
        self.assertTrue(storage.exists(path))
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())

    def test_conflicting_identifier_aliases_do_not_move_or_delete_an_asset(self):
        with self.assertRaises(services.MapError):
            self.command("delete", {"assetId": str(self.floor.pk), "asset_id": str(self.wall.pk)})
        self.assertTrue(MapAsset.objects.filter(pk=self.floor.pk).exists())
        self.assertTrue(MapAsset.objects.filter(pk=self.wall.pk).exists())
        self.assertFalse(Receipt.objects.exists())

    def pdf_actor_and_snapshot(self):
        from gravewright.actors.models import Actor, Asset
        from gravewright.pdf_system.schema import normalize
        from gravewright.tokens.models import Token

        self.campaign.system = "gravewright-pdf-system"
        self.campaign.save(update_fields=["system"])
        asset = Asset(campaign=self.campaign, kind="pdf", name="Synthetic library PDF")
        fixture = Path(__file__).resolve().parents[2] / "pdf_system/static/gravewright_pdf_system/assets/blank-a4.pdf"
        asset.file.save("synthetic-library.pdf", ContentFile(fixture.read_bytes()), save=True)
        data = normalize({"pdf": {"asset": str(asset.pk)}, "notes": "Preserve authored notes"})
        actor = Actor.objects.create(campaign=self.campaign, name="Synthetic PDF hero", data=data)
        scene = Scene.objects.create(campaign=self.campaign, name="Synthetic PDF scene", width=32, height=32)
        token = Token.objects.create(scene=scene, actor=actor, linked=False, snapshot=deepcopy(data))
        return asset, actor, token

    def test_pdf_delete_unlinks_actor_and_snapshot_once_and_notifies_after_file_cleanup(self):
        from gravewright.actors.models import Asset

        asset, actor, token = self.pdf_actor_and_snapshot()
        actor_revision, token_revision = actor.sheet_version, token.sheet_version
        storage, path, asset_id = asset.file.storage, asset.file.name, str(asset.pk)
        rid = uuid.uuid4()
        with patch("gravewright.maps.views.notify"), patch("gravewright.table.media.announce"), \
                patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.command("delete", {"assetId": asset_id}, request_id=rid)
                self.assertTrue(storage.exists(path))
                send.assert_not_called()
                self.assertFalse(Asset.objects.filter(pk=asset_id).exists())
            self.assertFalse(storage.exists(path))
            actor.refresh_from_db()
            token.refresh_from_db()
            self.assertEqual((actor.data["pdf"]["asset"], token.snapshot["pdf"]["asset"]), ("", ""))
            self.assertEqual((actor.data["pdf"]["template"], token.snapshot["pdf"]["template"]), ("generic", "generic"))
            self.assertEqual((actor.sheet_version, token.sheet_version), (actor_revision + 1, token_revision + 1))
            self.assertEqual(actor.data["notes"], "Preserve authored notes")
            self.assertEqual(token.snapshot["notes"], "Preserve authored notes")
            self.assertIn("room.actors", [call.args[1]["type"] for call in send.call_args_list])
            self.assertIn("room.tokens", [call.args[1]["type"] for call in send.call_args_list])
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.command("delete", {"assetId": asset_id}, request_id=rid), result)
            send.assert_not_called()
        actor.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual((actor.sheet_version, token.sheet_version), (actor_revision + 1, token_revision + 1))

    def test_rolled_back_pdf_delete_restores_actor_snapshot_revisions_and_file(self):
        from gravewright.actors.models import Asset

        asset, actor, token = self.pdf_actor_and_snapshot()
        original_actor, original_snapshot = deepcopy(actor.data), deepcopy(token.snapshot)
        actor_revision, token_revision = actor.sheet_version, token.sheet_version
        storage, path, asset_id = asset.file.storage, asset.file.name, str(asset.pk)
        rid = uuid.uuid4()
        with patch("gravewright.maps.views.notify"), patch("gravewright.table.media.announce"), \
                patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        self.command("delete", {"assetId": asset_id}, request_id=rid)
                        raise RuntimeError("Abort integration")
            send.assert_not_called()
        actor.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual((actor.data, token.snapshot), (original_actor, original_snapshot))
        self.assertEqual((actor.sheet_version, token.sheet_version), (actor_revision, token_revision))
        self.assertTrue(Asset.objects.filter(pk=asset_id).exists())
        self.assertTrue(storage.exists(path))
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())
