"""Project asset families preserve concrete painted choices across persistence."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings
from PIL import Image

from gravewright.administration.archives import export_campaign, import_campaign
from gravewright.maps import builder_render, builder_services
from gravewright.maps.models import MapAsset, MapBuilderProject, Scene
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderFamilyTests(TestCase):
    setUp = fixtures.BuilderProjectTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate

    def family_document(self):
        doc = deepcopy(self.doc)
        doc["schemaVersion"] = 3
        layer_id = str(uuid.uuid4())
        doc["layers"] = [{"id": layer_id, "name": "Base", "visible": True, "locked": False}]
        blue = self.asset("dungeon-blue.png", "#2040b0")
        green = self.asset("dungeon-green.png", "#20b040")
        family = [self.floor, blue, green]
        doc["assets"][0].update(family="Dungeon", name="Red stone", collection="Textures")
        doc["assets"].extend({"assetId": str(asset.pk), "role": "floor", "family": "Dungeon"}
                             for asset in family[1:])
        doc["floors"] = [{"id": str(uuid.uuid4()), "assetId": str(asset.pk), "layerId": layer_id,
                          "x": index, "y": 0, "width": 1, "height": 1, "rotation": 0}
                         for index, asset in enumerate(family)]
        doc["walls"], doc["doors"], doc["decorations"], doc["lights"] = [], [], [], []
        return doc

    def pixels(self, document):
        with builder_render.render(document, self.campaign.pk) as source, Image.open(source) as image:
            return tuple(image.getpixel((index * 64 + 32, 32)) for index in range(3))

    def test_family_roundtrip_trims_names_and_keeps_existing_asset_metadata(self):
        doc = self.family_document()
        doc["assets"][0]["family"] = "  Dungeon  "
        response = self.save(document=doc)
        self.assertEqual(response.status_code, 200, response.content)
        expected = deepcopy(doc)
        expected["assets"][0]["family"] = "Dungeon"
        self.assertEqual(response.json()["project"]["document"], expected)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], expected)

    def test_family_names_reject_invalid_types_blank_nul_and_excess_length(self):
        original = self.family_document()
        for name in (None, True, 7, [], {}, "", " \t\n ", "bad\x00name", "x" * 81):
            doc = deepcopy(original)
            doc["assets"][0]["family"] = name
            with self.subTest(name=name):
                response = self.save(document=doc)
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(MapBuilderProject.objects.exists())
        for entry in original["assets"]:
            if "family" in entry:
                entry["family"] = "x" * 80
        self.assertEqual(self.save(document=original).status_code, 200)

    def test_one_family_cannot_mix_asset_types_even_after_trimming(self):
        original = self.family_document()
        for role in ("wall", "door", "decoration"):
            doc = deepcopy(original)
            doc["assets"][1].update(role=role, family=" Dungeon ")
            with self.subTest(role=role):
                response = self.save(document=doc)
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(MapBuilderProject.objects.exists())

    def test_family_allows_each_image_type_and_rejects_lights_and_foreign_images(self):
        original = self.family_document()
        who = builder_services.authority(self.campaign.pk, self.gm.pk)
        for role in ("floor", "wall", "door", "decoration"):
            doc = deepcopy(original)
            doc["floors"] = []
            for entry in doc["assets"]:
                if "family" in entry:
                    entry["role"] = role
            with self.subTest(role=role):
                cleaned = builder_services.clean_document(doc, who)
                self.assertEqual(cleaned, doc)
        for entry in ({"assetId": str(self.floor.pk), "role": "light", "family": "Torches"},
                      {"assetId": str(self.foreign_asset.pk), "role": "floor", "family": "Dungeon"}):
            doc = deepcopy(original)
            doc["assets"][0] = entry
            with self.subTest(entry=entry):
                response = self.save(document=doc)
                self.assertEqual(response.status_code, 400, response.content)

    def test_save_generate_and_update_keep_the_concrete_painted_tiles(self):
        doc = self.family_document()
        response = self.save(document=doc)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.pixels(response.json()["project"]["document"]),
                         ((176, 32, 32), (32, 64, 176), (32, 176, 64)))
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        self.assertEqual(generated.json()["project"]["document"], doc)
        doc["name"] = "Renamed dungeon"
        saved = self.save(document=doc, expected_version=1)
        self.assertEqual(saved.status_code, 200, saved.content)
        updated = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()),
                            "expected_version": 2, "expected_scene_version": 1})
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["project"]["document"], doc)
        self.assertEqual(self.pixels(updated.json()["project"]["document"]),
                         ((176, 32, 32), (32, 64, 176), (32, 176, 64)))
        self.assertEqual(Scene.objects.count(), 1)

    def test_deleted_image_removes_just_its_family_membership_and_keeps_other_tiles(self):
        doc = self.family_document()
        self.assertEqual(self.save(document=doc).status_code, 200)
        builder_services.detach_project_art(self.campaign.pk, self.floor.pk)
        saved = self.client.get(self.url).json()["project"]
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["document"]["assets"], doc["assets"][1:])
        self.assertIsNone(saved["document"]["floors"][0]["assetId"])
        self.assertEqual(saved["document"]["floors"][1:], doc["floors"][1:])

    def test_clone_and_snapshot_preserve_family_names_and_remap_image_members(self):
        doc = self.family_document()
        family_name = f"Dungeon {self.floor.pk}"
        for entry in doc["assets"]:
            if "family" in entry:
                entry["family"] = family_name
        self.assertEqual(self.save(document=doc).status_code, 200)
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Cloned dungeon")
        project = MapBuilderProject.objects.get(campaign=clone)
        original_names = {str(row.pk): row.name for row in MapAsset.objects.filter(campaign=self.campaign)}
        cloned_ids = {row.name: str(row.pk) for row in MapAsset.objects.filter(campaign=clone)}
        expected = deepcopy(doc)
        for kind in ("assets", "floors"):
            for entry in expected[kind]:
                entry["assetId"] = cloned_ids[original_names[entry["assetId"]]]
        self.assertEqual(project.document, expected)
        who = builder_services.authority(clone.pk, self.gm.pk)
        self.assertEqual(builder_services.clean_document(project.document, who), expected)
        snapshot = export_campaign(self.campaign, snapshot=True)
        MapBuilderProject.objects.filter(pk=self.project_id).update(document={})
        import_campaign(snapshot, self.gm, target=self.campaign)
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document, doc)

    def test_reading_existing_sources_without_families_does_not_modify_them(self):
        expanded = self.family_document()
        for entry in expanded["assets"]:
            entry.pop("family", None)
        for version in (1, 2, 3):
            doc = deepcopy(expanded if version == 3 else self.doc)
            doc["schemaVersion"] = version
            if version == 1:
                doc["doors"] = []
            project = MapBuilderProject.objects.create(campaign=self.campaign, name=doc["name"], document=doc)
            with self.subTest(version=version):
                response = self.client.get(f"{self.base}/projects/{project.pk}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["project"]["document"], doc)
                project.refresh_from_db()
                self.assertEqual(project.document, doc)
                self.assertEqual(project.version, 1)
