"""Dynamic surfaces preserve raster coverage, ownership and atomic play state."""

from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
import uuid

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image, ImageChops

from gravewright.maps import builder_dynamic, builder_render, builder_services, services
from gravewright.maps.models import Broadcast, MapAsset, MapBuilderProject, Scene, SceneObject
from . import test_builder_free_paint as fixtures
from . import test_builder_projects as project_fixtures
from .test_builder_terrain_brush import brush


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], ALLOWED_HOSTS=["testserver"],
                   GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderDynamicTests(TestCase):
    setUp = fixtures.BuilderFreePaintTests.setUp
    asset = project_fixtures.BuilderProjectTests.asset
    post = project_fixtures.BuilderProjectTests.post
    save = project_fixtures.BuilderProjectTests.save
    generate = project_fixtures.BuilderProjectTests.generate
    files = project_fixtures.BuilderProjectTests.files
    clean = fixtures.BuilderFreePaintTests.clean

    def promoted(self):
        self.doc["floors"][0]["dynamic"] = True
        self.doc["walls"][0]["dynamic"] = True
        return self.doc

    def generated(self):
        response = self.save()
        self.assertEqual(response.status_code, 200, response.content)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        return Scene.objects.get(campaign=self.campaign)

    def image(self, content):
        with Image.open(content) as image:
            return image.convert("RGBA")

    def test_legacy_omission_strict_flags_erasers_and_surface_count(self):
        self.assertEqual(self.clean(), self.doc)
        for flag in (None, 1, "true", [], {}):
            document = deepcopy(self.doc)
            document["floors"][0]["dynamic"] = flag
            with self.subTest(flag=flag), self.assertRaises(services.MapError):
                self.clean(document)
        document = deepcopy(self.legacy)
        document["walls"][0]["dynamic"] = False
        with self.assertRaises(services.MapError):
            self.clean(document)
        self.promoted()
        self.doc["floors"][0].update(assetId=None, brush=brush("erase"))
        with self.assertRaisesRegex(services.MapError, "erase stroke"):
            self.clean()
        self.doc["floors"] = []
        self.doc["walls"] = [{**self.doc["walls"][0], "id": str(uuid.uuid4())} for _ in range(65)]
        with self.assertRaisesRegex(services.MapError, "too many dynamic surfaces"):
            self.clean()

    def test_plane_composition_matches_existing_contours_erasers_layers_and_joined_walls(self):
        floor = self.doc["floors"][0]
        floor.update(dynamic=True, paint={"color": None, "opacity": .7},
                     shape={"contours": [fixtures.RECTANGLE], "cuts": [[[.3, .3], [.7, .3], [.7, .7], [.3, .7]]]})
        self.doc["floors"].append({**deepcopy(floor), "id": str(uuid.uuid4()), "dynamic": False,
                                   "x": 2, "width": 3, "paint": {"color": None, "opacity": .4}})
        self.doc["floors"].append({**deepcopy(floor), "id": str(uuid.uuid4()), "assetId": None,
                                   "dynamic": False, "brush": brush("erase", alpha=.4)})
        self.doc["walls"][0]["dynamic"] = True
        self.doc["walls"].append({**self.doc["walls"][0], "id": str(uuid.uuid4()), "dynamic": False,
                                   "x1": 7, "x2": 7, "y1": 3, "y2": 7})
        original = self.image(builder_render.render(self.doc, self.campaign.pk))
        composed = self.image(builder_render.render(builder_dynamic.baked_document(self.doc), self.campaign.pk))
        try:
            groups = {}
            for plane in builder_dynamic.prepare(self.doc, self.campaign.pk):
                with self.image(plane["content"]) as image:
                    if plane["kind"] == "floors":
                        layer = groups.setdefault(plane["group"], Image.new("RGBA", original.size))
                        if plane["operation"] == "erase":
                            box = plane["bounds"]
                            with layer.crop(box) as previous, previous.getchannel("A") as alpha, image.getchannel("A") as removal:
                                with ImageChops.invert(removal) as keep, ImageChops.multiply(alpha, keep) as faded:
                                    previous.putalpha(faded)
                                layer.paste(previous, box)
                        else:
                            layer.alpha_composite(image, plane["bounds"][:2])
                    else:
                        if groups:
                            for layer in groups.values(): composed.alpha_composite(layer); layer.close()
                            groups.clear()
                        composed.alpha_composite(image, plane["bounds"][:2])
            for layer in groups.values(): composed.alpha_composite(layer); layer.close()
            with ImageChops.difference(original, composed) as delta:
                self.assertLessEqual(max(high for _, high in delta.getextrema()), 2)
        finally:
            original.close(); composed.close()

    def test_original_material_alpha_is_not_baked_into_replacement_mask(self):
        row = self.doc["floors"][0]
        row["dynamic"] = True
        with Image.new("RGBA", (16, 16), (200, 40, 20, 128)) as texture:
            output = BytesIO(); texture.save(output, "PNG")
        self.floor.file.save("translucent.png", ContentFile(output.getvalue()))
        plane = next(row for row in builder_dynamic.prepare(self.doc, self.campaign.pk) if row["dynamic"])
        with self.image(plane["content"]) as artwork, self.image(plane["mask"]) as mask:
            self.assertEqual(artwork.getpixel((20, 20))[3], 128)
            self.assertEqual(mask.getpixel((20, 20))[3], 255)

    def test_plane_and_group_pixel_budget_is_checked_before_rendering_or_storage(self):
        self.doc.update(columns=200, rows=200, cellSize=16)
        row = self.doc["floors"][0]
        row.update(x=0, y=0, width=200, height=200, dynamic=True)
        self.doc["floors"] = [{**row, "id": str(uuid.uuid4())} for _ in range(3)]
        before = self.files()
        with patch("gravewright.maps.builder_render.render") as raster:
            with self.assertRaisesRegex(services.MapError, "dynamic surfaces are too complex"):
                self.clean()
            raster.assert_not_called()
        self.assertEqual(self.files(), before)

    def test_baked_image_has_no_promoted_pixels_and_wall_only_keeps_floor(self):
        self.promoted()
        with self.image(builder_render.render(builder_dynamic.baked_document(self.doc), self.campaign.pk)) as background:
            self.assertEqual(background.getpixel((128, 128))[:3], (17, 34, 51))
            self.assertEqual(background.getpixel((128, 192))[:3], (17, 34, 51))
        self.doc["floors"][0].pop("dynamic")
        with self.image(builder_render.render(builder_dynamic.baked_document(self.doc), self.campaign.pk)) as background:
            self.assertEqual(background.getpixel((128, 128))[:3], (176, 32, 32))

    def test_generation_identity_references_barriers_and_receipt_replay(self):
        self.promoted()
        from gravewright.maps.blueprints import default_blueprint
        blueprint = default_blueprint()
        blueprint["version"] = 2
        blueprint["graphs"] = {"interact": {"nodes": [
            {"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
            {"id": "surfaceRef", "type": "reference", "targetId": self.doc["floors"][0]["id"], "x": 200, "y": 0}], "edges": []}}
        self.doc["doors"][0]["blueprint"] = blueprint
        scene = self.generated()
        for kind in ("floors", "walls"):
            row = scene.elements.get(pk=uuid.uuid5(scene.pk, self.doc[kind][0]["id"]))
            self.assertEqual(row.kind, "images")
            self.assertEqual(row.data["surface"]["kind"], "floor" if kind == "floors" else "wall")
            self.assertNotIn("sourceId", row.data["surface"])
        door = scene.elements.get(kind="walls", data__kind="door")
        self.assertEqual(door.data["blueprint"]["graphs"]["interact"]["nodes"][1]["targetId"],
                         str(uuid.uuid5(scene.pk, self.doc["floors"][0]["id"])))
        self.assertEqual(scene.elements.filter(kind="walls", data__kind="wall").count(), 2)
        count = MapAsset.objects.count()
        request_id = str(uuid.uuid4())
        first = self.generate(request_id=request_id)
        self.assertEqual(first.status_code, 200)
        after = MapAsset.objects.count()
        self.assertGreater(after, count)
        self.assertEqual(self.generate(request_id=request_id).json(), first.json())
        self.assertEqual(MapAsset.objects.count(), after)

    def test_visual_helpers_are_in_memory_only_and_never_change_barriers(self):
        self.promoted(); scene = self.generated()
        row = scene.elements.get(pk=uuid.uuid5(scene.pk, self.doc["walls"][0]["id"]))
        before_files, before_barriers = self.files(), list(scene.elements.filter(kind="walls").values_list("data", flat=True))
        self.assertTrue(builder_dynamic.set_appearance(scene, row, self.floor.pk))
        self.assertTrue(builder_dynamic.set_visibility(scene, row, False))
        self.assertEqual(self.files(), before_files)
        self.assertEqual(row.data["surface"]["materialId"], str(self.floor.pk))
        self.assertIn("materialCrop", row.data["surface"])
        self.assertEqual(row.data["layer"], "gm-image-layer")
        self.assertNotIn("materialId", scene.elements.get(pk=row.pk).data["surface"])
        self.assertEqual(list(scene.elements.filter(kind="walls").values_list("data", flat=True)), before_barriers)
        for asset in (self.foreign_asset, MapAsset.objects.filter(generated_for=scene).first()):
            with self.assertRaises(services.MapError): builder_dynamic.set_appearance(scene, row, asset.pk)

    def test_surface_material_action_is_independent_of_owners_state_asset_role(self):
        from gravewright.maps.blueprints import default_blueprint
        blueprint = default_blueprint(); blueprint["version"] = 2
        blueprint["graphs"] = {"interact": {"nodes": [
            {"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
            {"id": "paint", "type": "setAppearance", "assetId": str(self.floor.pk), "x": 200, "y": 0}],
            "edges": [{"from": "event", "output": "next", "to": "paint", "kind": "execution"}]}}
        self.doc["doors"][0]["blueprint"] = blueprint
        self.assertEqual(self.clean()["doors"][0]["blueprint"]["graphs"]["interact"]["nodes"][1]["assetId"], str(self.floor.pk))
        blueprint["states"]["closed"] = {"appearance": "asset", "assetId": str(self.floor.pk)}
        with self.assertRaises(services.MapError): self.clean()

    def test_update_preserves_runtime_visuals_until_explicit_source_asset_changes(self):
        self.promoted(); scene = self.generated()
        identifier = uuid.uuid5(scene.pk, self.doc["floors"][0]["id"])
        row = scene.elements.get(pk=identifier)
        builder_dynamic.set_appearance(scene, row, self.wall.pk); builder_dynamic.set_visibility(scene, row, False)
        row.save(update_fields=["data"])
        external = SceneObject.objects.create(scene=scene, kind="images", data={"native": "preserved"})
        old_ids = set(MapAsset.objects.filter(generated_for=scene).values_list("pk", flat=True))
        payload = {"request_id": str(uuid.uuid4()), "expected_version": 1, "expected_scene_version": scene.version}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post(self.url + "/update", payload)
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db(); scene.refresh_from_db()
        self.assertEqual(row.data["surface"]["materialId"], str(self.wall.pk))
        self.assertEqual(row.data["layer"], "gm-image-layer")
        self.assertFalse(MapAsset.objects.filter(pk__in=old_ids).exists())
        self.assertTrue(SceneObject.objects.filter(pk=external.pk).exists())
        self.doc["assets"].append({"assetId": str(self.asset("other.png", "#55aa88").pk), "role": "floor"})
        self.doc["floors"][0]["assetId"] = self.doc["assets"][-1]["assetId"]
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        response = self.post(self.url + "/update", {**payload, "request_id": str(uuid.uuid4()),
                                                    "expected_version": 2, "expected_scene_version": scene.version})
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db(); self.assertNotIn("materialId", row.data["surface"])
        self.assertEqual(row.data["layer"], "map")

    def test_failure_after_asset_creation_removes_owned_files_and_rows(self):
        self.promoted(); self.assertEqual(self.save().status_code, 200)
        before = self.files()
        with patch("gravewright.maps.builder_services.SceneObject.objects.bulk_create", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                builder_services.generate(self.campaign.pk, self.gm.pk, self.project_id,
                                          {"request_id": str(uuid.uuid4()), "expected_version": 1})
        self.assertEqual(self.files(), before)
        self.assertFalse(Scene.objects.filter(campaign=self.campaign).exists())
        self.assertFalse(MapAsset.objects.filter(generated_for__isnull=False).exists())

    def test_demotion_rebakes_surfaces_and_removes_only_their_generated_artifacts(self):
        self.promoted(); scene = self.generated()
        for kind in ("floors", "walls"): self.doc[kind][0].pop("dynamic")
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
                                                         "expected_scene_version": scene.version})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(scene.elements.filter(kind="images").exists())
        self.assertFalse(MapAsset.objects.filter(generated_for=scene).exists())
        self.assertEqual(scene.elements.filter(kind="walls").count(), 3)
        self.assertTrue(MapAsset.objects.filter(pk=self.floor.pk).exists())

    def test_generated_assets_are_hidden_protected_and_only_visible_materials_are_authorized(self):
        self.promoted(); scene = self.generated()
        self.assertEqual(self.client.get(self.base).json()["assets"].__len__(), 3)
        generated = MapAsset.objects.filter(generated_for=scene).first()
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(generated.pk)})
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(MapAsset.objects.filter(pk=generated.pk).exists())
        scene.visibility = "players"; scene.save(update_fields=["visibility"])
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        row = scene.elements.get(pk=uuid.uuid5(scene.pk, self.doc["floors"][0]["id"]))
        builder_dynamic.set_appearance(scene, row, self.wall.pk); row.save(update_fields=["data"])
        self.client.force_login(self.player)
        for identifier in (row.data["asset_id"], row.data["surface"]["maskId"], self.wall.pk):
            response = self.client.get(f"/game/map-assets/{identifier}")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b"".join(response.streaming_content))
        builder_dynamic.set_visibility(scene, row, False); row.save(update_fields=["data"])
        self.assertEqual(self.client.get(f'/game/map-assets/{row.data["surface"]["maskId"]}').status_code, 404)

    def test_archive_remaps_generated_ownership_materials_masks_and_private_recipe(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.promoted(); scene = self.generated()
        row = scene.elements.get(pk=uuid.uuid5(scene.pk, self.doc["floors"][0]["id"]))
        builder_dynamic.set_appearance(scene, row, self.wall.pk); row.save(update_fields=["data"])
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Cloned dynamic surfaces")
        project = MapBuilderProject.objects.get(campaign=clone)
        self.assertEqual(project.document["floors"][0]["dynamic"], True)
        self.assertEqual(MapAsset.objects.filter(generated_for=project.scene, campaign=clone).count(), 4)
        copied = project.scene.elements.get(kind="images", data__surface__kind="floor")
        self.assertNotEqual(copied.data["surface"]["maskId"], row.data["surface"]["maskId"])
        self.assertTrue(MapAsset.objects.filter(pk=copied.data["surface"]["materialId"], campaign=clone).exists())
        self.assertEqual(project.generation["dynamicDocument"], project.document)
        response = builder_services.update(clone.pk, self.gm.pk, project.pk,
                                           {"request_id": str(uuid.uuid4()), "expected_version": project.version,
                                            "expected_scene_version": project.scene.version})
        self.assertEqual(response["project"]["sceneId"], str(project.scene_id))

    def test_asset_deletion_cleans_private_recipe_without_adopting_unapplied_geometry(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.maps.blueprints import default_blueprint
        self.promoted()
        behavior = default_blueprint('region')
        behavior['graphs'] = {'presence:enter': {'nodes': [
            {'id': 'event', 'type': 'event', 'event': 'presence:enter', 'x': 0, 'y': 0},
            {'id': 'paint', 'type': 'setAppearance', 'assetId': str(self.floor.pk), 'x': 200, 'y': 0}],
            'edges': [{'kind': 'execution', 'from': 'event', 'to': 'paint', 'output': 'next'}]}}
        self.doc['regions'] = [{'id': str(uuid.uuid4()), 'layerId': self.layer, 'name': 'Palette region',
                                'x': 6, 'y': 6, 'width': 1, 'height': 1, 'enabled': True, 'blueprint': behavior}]
        scene = self.generated()
        wall = scene.elements.get(pk=uuid.uuid5(scene.pk, self.doc['walls'][0]['id']))
        builder_dynamic.set_appearance(scene, wall, self.floor.pk); wall.save(update_fields=['data'])
        self.doc['floors'][0]['x'] = 2
        self.doc['floors'][0]['width'] = 5
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        response = self.post(f'/api/containers/{self.campaign.pk}/library/assets/delete', {'asset_id': str(self.floor.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        project = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(project.document['floors'][0]['x'], 2)
        self.assertEqual(project.generation['dynamicDocument']['floors'][0]['x'], 1)
        self.assertIsNone(project.generation['dynamicDocument']['floors'][0]['assetId'])
        for document in (project.document, project.generation['dynamicDocument']):
            self.assertFalse(any(node['type'] == 'setAppearance' for graph in document['regions'][0]['blueprint']['graphs'].values()
                                 for node in graph['nodes']))
        clone = import_campaign(export_campaign(self.campaign), self.gm, 'Cloned after material deletion')
        self.assertTrue(MapBuilderProject.objects.filter(campaign=clone).exists())

    def test_world_archive_remaps_typed_destinations_handouts_and_gates_but_preserves_message_text(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.actors.models import Actor
        from gravewright.journals.models import Journal
        from gravewright.maps.blueprints import default_blueprint
        from gravewright.tokens.models import Token
        self.promoted()
        handout = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Portable handout')
        authored_text = str(handout.pk)
        source_id, destination_id = str(uuid.uuid4()), str(uuid.uuid4())
        behavior = default_blueprint('region')
        nodes = [{'id': 'event', 'type': 'event', 'event': 'presence:enter', 'x': 0, 'y': 0},
                 {'id': 'message', 'type': 'showMessage', 'text': authored_text, 'audience': {'scope': 'users', 'userIds': [str(self.player.pk)]}, 'x': 200, 'y': 0},
                 {'id': 'paper', 'type': 'showHandout', 'journalId': str(handout.pk), 'audience': {'scope': 'trigger'}, 'x': 400, 'y': 0},
                 {'id': 'travel', 'type': 'teleport', 'destinationId': destination_id, 'x': 600, 'y': 0}]
        behavior['graphs'] = {'presence:enter': {'nodes': nodes, 'edges': [
            {'kind': 'execution', 'from': before, 'to': after, 'output': 'next'}
            for before, after in (('event', 'message'), ('message', 'paper'), ('paper', 'travel'))]}}
        self.doc['regions'] = [{'id': source_id, 'layerId': self.layer, 'name': 'Departure', 'x': 5, 'y': 6,
                                'width': 1, 'height': 1, 'enabled': True, 'blueprint': behavior},
                               {'id': destination_id, 'layerId': self.layer, 'name': 'Arrival', 'x': 6, 'y': 6,
                                'width': 1, 'height': 1, 'enabled': True}]
        scene = self.generated()
        actor = Actor.objects.create(campaign=self.campaign, name='Portable traveler')
        token = Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6)
        destination = scene.elements.get(pk=uuid.uuid5(scene.pk, destination_id))
        destination.data['region'].update(state='occupied', occupants=[str(token.pk)], arrivalGates=[str(token.pk)])
        destination.save(update_fields=['data'])
        project = MapBuilderProject.objects.get(pk=self.project_id)
        next(row for row in project.generation['objects'] if row['id'] == str(destination.pk))['data'] = deepcopy(destination.data)
        project.save(update_fields=['generation'])
        for included in (False, True):
            clone = import_campaign(export_campaign(self.campaign, {'journals': included, 'actors': included}), self.gm, 'Cloned world bindings')
            copied = MapBuilderProject.objects.get(campaign=clone)
            departure = copied.scene.elements.get(kind='zones', data__region__name='Departure')
            arrival = copied.scene.elements.get(kind='zones', data__region__name='Arrival')
            native = departure.data['blueprint']['graphs']['presence:enter']['nodes']
            self.assertEqual(native[1]['text'], authored_text)
            self.assertNotEqual(native[1]['audience']['userIds'], [str(self.player.pk)])
            self.assertEqual(native[3]['destinationId'], str(arrival.pk))
            self.assertNotEqual(native[2]['journalId'], str(handout.pk))
            self.assertEqual(Journal.objects.filter(campaign=clone, pk=native[2]['journalId']).exists(), included)
            for document in (copied.document, copied.generation['dynamicDocument']):
                source = document['regions'][0]['blueprint']['graphs']['presence:enter']['nodes']
                self.assertEqual(source[1]['text'], authored_text)
                self.assertEqual(source[2]['journalId'], native[2]['journalId'])
                self.assertEqual(source[3]['destinationId'], document['regions'][1]['id'])
            gates = arrival.data['region']['arrivalGates']
            if included:
                self.assertEqual(gates, [str(Token.objects.get(scene=copied.scene).pk)])
                self.assertNotEqual(gates, [str(token.pk)])
            else:
                self.assertEqual(gates, [])
