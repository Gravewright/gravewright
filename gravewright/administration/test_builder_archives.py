"""Editable map projects travel with campaign and scene content archives."""

from copy import deepcopy
from io import BytesIO
import tempfile
import uuid

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Folder, MapAsset, MapBuilderProject, Scene, SceneObject

from .archives import export_campaign, import_campaign, options, records


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BuilderArchiveTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        media = override_settings(MEDIA_ROOT=temporary.name)
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user("builder-archive@example.test", "password-12345", name="GM")
        self.campaign = Campaign.objects.create(owner=self.user, name="Map workshop")
        Membership.objects.create(campaign=self.campaign, user=self.user, role="gm")
        self.folder = Folder.objects.create(campaign=self.campaign, label="Workshop maps")
        self.scene = Scene.objects.create(campaign=self.campaign, folder=self.folder,
            name="Workshop room", width=560, height=420)
        image = BytesIO()
        Image.new("RGB", (8, 8), "#876b42").save(image, "PNG")
        self.asset = MapAsset.objects.create(campaign=self.campaign, name="Floor texture",
            width=8, height=8, file=ContentFile(image.getvalue(), name="floor.png"))
        self.document = {"schemaVersion": 1, "name": "Workshop room", "columns": 8, "rows": 6,
            "cellSize": 70, "background": "#253038", "assets": [{"assetId": str(self.asset.pk), "role": "floor"}],
            "floors": [{"id": str(uuid.uuid4()), "assetId": str(self.asset.pk), "x": 1, "y": 1, "width": 6, "height": 4}],
            "walls": [], "doors": []}
        self.project = MapBuilderProject.objects.create(campaign=self.campaign, folder=self.folder,
            scene=self.scene, name="Workshop room", document=self.document, version=3)
        SceneObject.objects.create(scene=self.scene, kind="walls", data={
            "kind": "door", "asset_id": str(self.asset.pk), "x1": 70, "y1": 70, "x2": 140, "y2": 70})

    def test_clone_remaps_project_scene_folder_and_asset_references(self):
        restored = import_campaign(export_campaign(self.campaign), self.user, "Imported workshop")
        project = MapBuilderProject.objects.get(campaign=restored)
        asset = MapAsset.objects.get(campaign=restored)
        self.assertNotEqual(project.pk, self.project.pk)
        self.assertNotEqual(asset.pk, self.asset.pk)
        self.assertEqual(project.version, 3)
        self.assertEqual(project.folder.campaign_id, restored.pk)
        self.assertEqual(project.scene.campaign_id, restored.pk)
        self.assertEqual(project.document["floors"][0]["assetId"], str(asset.pk))
        self.assertEqual(project.document["assets"][0]["assetId"], str(asset.pk))
        self.assertEqual(SceneObject.objects.get(scene=project.scene).data["asset_id"], str(asset.pk))
        with asset.file.open("rb") as source:
            self.assertEqual(Image.open(source).size, (8, 8))

    def test_snapshot_restores_project_and_scene_pack_includes_its_source(self):
        raw = export_campaign(self.campaign, snapshot=True)
        MapBuilderProject.objects.filter(pk=self.project.pk).update(name="Changed", document={})
        import_campaign(raw, self.user, target=self.campaign)
        project = MapBuilderProject.objects.get(pk=self.project.pk)
        self.assertEqual(project.document, self.document)
        self.assertEqual(project.scene_id, self.scene.pk)
        from gravewright.compendiums.graph import select
        graph = select(records(self.campaign, options()), ("gravewright_maps.scene", str(self.scene.pk)))
        selected = {(row["model"], str(row["pk"])) for row in graph}
        self.assertIn(("gravewright_maps.mapbuilderproject", str(project.pk)), selected)
        self.assertIn(("gravewright_maps.mapasset", str(self.asset.pk)), selected)

    def test_excluded_audio_keeps_typed_nodes_with_consistent_inert_bindings(self):
        from gravewright.audio.models import Track
        from gravewright.maps.blueprint_runtime import clean_native_blueprint
        from gravewright.maps.tests.test_blueprint_references import blueprint, execution, node
        sound = Track.objects.create(campaign=self.campaign, name="Bell", duration=1)
        sound_id = str(sound.pk)
        authored_name = "Group " + sound_id
        raw = blueprint({"interact": ([node("sound", "soundReference", trackId=sound_id),
            node("group", "elementGroup", name=authored_name, memberType="sound", targetIds=[sound_id]),
            node("text", "getVariable", scope="element", name="Text", valueType="text", default=sound_id),
            node("move", "move", dx=1, dy=0)], [execution("event", "move")])})
        original = self.scene.elements.get()
        original.data["blueprint"] = deepcopy(raw)
        original.save(update_fields=["data"])
        self.project.document["doors"] = [{"id": str(uuid.uuid4()), "blueprint": deepcopy(raw)}]
        self.project.generation = {"objects": [{"id": str(original.pk), "kind": "walls", "data": deepcopy(original.data)}]}
        self.project.save(update_fields=["document", "generation"])
        restored = import_campaign(export_campaign(self.campaign, {"audio": False}), self.user, "Silent workshop")
        source = MapBuilderProject.objects.get(campaign=restored)
        native = source.scene.elements.get()
        candidates = [native.data["blueprint"], source.document["doors"][0]["blueprint"],
                      source.generation["objects"][0]["data"]["blueprint"]]
        bindings = []
        for candidate in candidates:
            clean_native_blueprint(candidate, restored.pk, source.scene_id)
            nodes = candidate["graphs"]["interact"]["nodes"]
            bindings.append(nodes[1]["trackId"])
            self.assertEqual(nodes[2]["targetIds"], [nodes[1]["trackId"]])
            self.assertEqual(nodes[2]["name"], authored_name)
            self.assertEqual(nodes[3]["default"], sound_id)
            self.assertEqual(candidate["graphs"]["interact"]["edges"], raw["graphs"]["interact"]["edges"])
        self.assertEqual(len(set(bindings)), 1)
        self.assertNotEqual(bindings[0], sound_id)
        self.assertFalse(Track.objects.filter(pk=bindings[0]).exists())
        original.refresh_from_db()
        self.assertEqual(original.data["blueprint"], raw)

    def test_region_filters_remap_included_and_omitted_actor_and_token_bindings(self):
        from gravewright.actors.models import Actor
        from gravewright.maps.regions import clean_filters
        from gravewright.tokens.models import Token
        actor = Actor.objects.create(campaign=self.campaign, name="Traveler", data={})
        token = Token.objects.create(scene=self.scene, actor=actor)
        filters = {"actorIds": [str(actor.pk)], "tokenIds": [str(token.pk)], "dispositions": [], "visibility": "any"}
        native = SceneObject.objects.create(scene=self.scene, kind="zones", data={"region": {
            "name": "Visitors", "filters": deepcopy(filters)}})
        self.project.document["regions"] = [{"id": str(uuid.uuid4()), "name": "Visitors", "filters": deepcopy(filters)}]
        self.project.generation = {"objects": [{"id": str(native.pk), "kind": "zones", "data": deepcopy(native.data)}]}
        self.project.save(update_fields=["document", "generation"])
        for included in (False, True):
            with self.subTest(actors=included):
                restored = import_campaign(export_campaign(self.campaign, {"actors": included}), self.user, "Filtered workshop")
                source = MapBuilderProject.objects.get(campaign=restored)
                region = source.scene.elements.get(kind="zones")
                copied = region.data["region"]["filters"]
                self.assertEqual(clean_filters(copied, campaign_id=restored.pk, scene_id=source.scene_id), copied)
                self.assertEqual(source.document["regions"][0]["filters"], copied)
                self.assertEqual(source.generation["objects"][0]["data"]["region"]["filters"], copied)
                self.assertNotEqual(copied["actorIds"], filters["actorIds"])
                self.assertNotEqual(copied["tokenIds"], filters["tokenIds"])
                self.assertEqual(Actor.objects.filter(campaign=restored, pk=copied["actorIds"][0]).exists(), included)
                self.assertEqual(Token.objects.filter(scene=source.scene, pk=copied["tokenIds"][0]).exists(), included)
        native.refresh_from_db()
        self.assertEqual(native.data["region"]["filters"], filters)
