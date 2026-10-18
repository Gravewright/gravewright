"""Builder lights and effects retain native contracts without rasterizing them."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings
from PIL import Image

from gravewright.maps import builder_render, builder_services, objects, services
from gravewright.maps.extra_objects import effect
from gravewright.maps.models import MapBuilderProject, Scene, SceneObject

from . import test_builder_expansion as expanded
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderEffectTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.legacy = deepcopy(self.doc)
        self.doc = expanded.BuilderExpansionTests.expanded(self)
        layer = self.doc["layers"][0]["id"]
        self.doc["lights"][0].update(animation="arcane", angle=95, rotation=135, elevation=3.5)
        self.doc["particles"] = [{"id": str(uuid.uuid4()), "layerId": layer, "x": 1.25, "y": 2.5,
            "kind": "firefly", "scale": 4.5, "density": .75, "color": "#eedd44", "enabled": True,
            "rotation": 270, "light_response": .4, "light_emission": 1.2}]
        self.doc["shaders"] = [{"id": str(uuid.uuid4()), "layerId": layer, "x": 6.5, "y": 1.5,
            "name": "Swirling mist", "source": "void main() { finalColor = vec4(uColor * 0.2, 0.2); }",
            "radius": 2.75, "scale": 1.25, "intensity": .45, "opacity": .6, "speed": 1.5,
            "color": "#5577aa", "rotation": 35, "blend_mode": "screen", "enabled": True,
            "light_response": .3, "light_emission": .2}]

    def generated(self):
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        result = self.generate()
        self.assertEqual(result.status_code, 200, result.content)
        self.scene = Scene.objects.get(pk=result.json()["scene"]["id"])
        return result

    def update(self, document=None):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        if document is not None:
            saved = self.save(document=document, expected_version=source.version)
            self.assertEqual(saved.status_code, 200, saved.content)
            source.refresh_from_db()
        self.scene.refresh_from_db()
        return builder_services.update(self.campaign.pk, self.gm.pk, source.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": source.version,
             "expected_scene_version": self.scene.version})

    def change_native(self, row, **changes):
        id_key = {"lights": "light_id", "particles": "emitter_id", "shaders": "shader_id"}[row.kind]
        return services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": row.kind, "action": "update",
             "data": {id_key: str(row.pk), **changes}}, uuid.uuid4())

    def test_native_settings_roundtrip_and_generation_converts_only_positions(self):
        result = self.generated()
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], self.doc)
        self.assertEqual(self.scene.visibility, "gm")
        for kind in ("particles", "shaders"):
            authored = self.doc[kind][0]
            native = self.scene.elements.get(kind=kind)
            self.assertEqual(native.pk, uuid.uuid5(self.scene.pk, authored["id"]))
            self.assertEqual((native.data["x"], native.data["y"]), (authored["x"] * 64, authored["y"] * 64))
            self.assertEqual({key: native.data[key] for key in builder_services.NATIVE_EFFECT_FIELDS[kind]},
                             {key: authored[key] for key in builder_services.NATIVE_EFFECT_FIELDS[kind]})
            self.assertNotIn("layerId", native.data)
        light = self.scene.elements.get(kind="lights")
        self.assertEqual((light.data["angle"], light.data["rotation"], light.data["animation"], light.data["elevation"]),
                         (95, 135, "arcane", 3.5))
        self.assertEqual(self.scene.elements.get(kind="shaders").data["radius"], 2.75)
        self.assertTrue(result.json()["project"]["canUpdate"])
        manifest = MapBuilderProject.objects.get(pk=self.project_id).generation
        self.assertEqual([row["sourceEnabled"] for row in manifest["objects"]
                          if row["kind"] in builder_services.LIVE_ENABLED_KINDS], [True, True, True])

    def test_old_schema_three_omission_is_preserved_and_new_rows_get_native_defaults(self):
        doc = deepcopy(self.doc)
        del doc["particles"], doc["shaders"]
        cleaned = builder_services.clean_document(doc, self.membership)
        self.assertEqual(cleaned, doc)
        for kind in ("particles", "shaders"):
            source = self.doc[kind][0]
            doc[kind] = [{key: source[key] for key in ("id", "layerId", "x", "y")}]
            if kind == "shaders":
                doc[kind][0]["source"] = source["source"]
        response = self.save(document=doc)
        self.assertEqual(response.status_code, 200, response.content)
        saved = response.json()["project"]["document"]
        self.assertEqual(saved["particles"][0]["kind"], "smoke")
        self.assertEqual((saved["particles"][0]["scale"], saved["particles"][0]["density"]), (3, .6))
        self.assertEqual((saved["shaders"][0]["name"], saved["shaders"][0]["radius"], saved["shaders"][0]["blend_mode"]),
                         ("Shader", 0, "normal"))

    def test_effects_require_version_three_and_invalid_rows_never_save(self):
        for version in (1, 2):
            for kind in ("particles", "shaders"):
                doc = deepcopy(self.legacy)
                doc.update(schemaVersion=version, **{kind: []})
                with self.subTest(version=version, kind=kind), self.assertRaisesMessage(services.MapError, "version 3"):
                    builder_services.clean_document(doc, self.membership)
        invalid = [
            ("particles", "kind", "unknown"), ("particles", "scale", .09),
            ("particles", "density", 1.01), ("particles", "density", True),
            ("particles", "enabled", "true"), ("particles", "light_response", 1.01),
            ("particles", "light_emission", 2.01), ("particles", "x", -1),
            ("particles", "layerId", str(uuid.uuid4())), ("particles", "assetId", str(self.floor.pk)),
            ("particles", "id", self.doc["lights"][0]["id"]), ("shaders", "y", 9),
            ("shaders", "source", " "), ("shaders", "source", "void main() {}\x00"),
            ("shaders", "source", "x" * 32001), ("shaders", "radius", -1),
            ("shaders", "scale", 20.01), ("shaders", "opacity", float("nan")),
            ("shaders", "intensity", 1.01), ("shaders", "speed", 8.01),
            ("shaders", "blend_mode", "overlay"), ("shaders", "name", "x" * 121),
            ("shaders", "unknown", True), ("lights", "animation", "unknown"),
            ("lights", "angle", 4), ("lights", "elevation", True),
        ]
        for kind, key, value in invalid:
            doc = deepcopy(self.doc)
            doc[kind][0][key] = value
            with self.subTest(kind=kind, key=key, value=value):
                response = self.save(document=doc)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertFalse(MapBuilderProject.objects.exists())
        for kind in ("particles", "shaders"):
            doc = deepcopy(self.doc)
            doc[kind] = {}
            self.assertEqual(self.save(document=doc).status_code, 400)

    def test_effects_count_toward_aggregate_object_native_and_document_limits(self):
        with patch.dict(builder_services.LIMITS, maxObjects=6):
            self.assertEqual(self.save().status_code, 400)
        with patch.dict(builder_services.LIMITS, maxNativeObjects=6):
            self.assertEqual(self.save().status_code, 400)
        large = deepcopy(self.doc)
        shader = large["shaders"][0]
        shader["source"] = "x" * 32000
        large["shaders"] = [{**deepcopy(shader), "id": str(uuid.uuid4())} for _ in range(33)]
        self.assertEqual(self.save(document=large).status_code, 400)
        self.assertFalse(MapBuilderProject.objects.exists())

    def test_native_enabled_toggles_survive_updates_and_authored_changes_take_effect(self):
        self.generated()
        for kind in builder_services.LIVE_ENABLED_KINDS:
            self.change_native(self.scene.elements.get(kind=kind), enabled=False)
        changed = deepcopy(self.doc)
        changed["particles"][0]["x"] += .5
        changed["shaders"][0]["radius"] = 4
        changed["lights"][0]["angle"] = 125
        self.update(changed)
        self.assertEqual([row.data["enabled"] for row in self.scene.elements.filter(kind__in=builder_services.LIVE_ENABLED_KINDS)],
                         [False, False, False])
        for kind in builder_services.LIVE_ENABLED_KINDS:
            self.change_native(self.scene.elements.get(kind=kind), enabled=True)
            changed[kind][0]["enabled"] = False
        self.update(changed)
        self.assertTrue(all(not row.data["enabled"] for row in self.scene.elements.filter(kind__in=builder_services.LIVE_ENABLED_KINDS)))
        self.assertEqual(self.scene.elements.get(kind="shaders").data["radius"], 4)

    def test_manual_edits_to_effect_configuration_remain_conflicts_without_partial_replacement(self):
        self.generated()
        before_files = self.files()
        for kind, changes in (("particles", {"density": .1}), ("shaders", {"source": "void main() { finalColor = vec4(0.0); }"}),
                              ("lights", {"color": "#112233"})):
            row = self.scene.elements.get(kind=kind)
            before = deepcopy(row.data)
            self.change_native(row, **changes)
            with self.subTest(kind=kind), self.assertRaisesMessage(services.MapError, "changed in the VTT"):
                self.update()
            self.assertEqual(self.files(), before_files)
            row.refresh_from_db()
            self.assertEqual({key: row.data[key] for key in changes}, changes)
            row.data = before
            row.save(update_fields=["data"])

    def test_update_removes_only_owned_effects_and_preserves_manual_native_objects(self):
        self.generated()
        old_generated = {kind: self.scene.elements.get(kind=kind).pk for kind in ("particles", "shaders")}
        manual = [SceneObject.objects.create(scene=self.scene, kind=kind,
            data=effect(kind, {"x": 17, "y": 29, "source": self.doc["shaders"][0]["source"]}))
            for kind in ("particles", "shaders")]
        manual.append(SceneObject.objects.create(scene=self.scene, kind="lights", data=objects.light({"x": 21, "y": 35})))
        changed = deepcopy(self.doc)
        changed["particles"], changed["shaders"] = [], []
        self.update(changed)
        self.assertFalse(self.scene.elements.filter(pk__in=old_generated.values()).exists())
        for row in manual:
            expected = deepcopy(row.data)
            row.refresh_from_db()
            self.assertEqual(row.data, expected)

    def test_positions_scale_with_grid_changes_but_effect_ranges_keep_native_cell_units(self):
        self.generated()
        changed = deepcopy(self.doc)
        changed["cellSize"] = 128
        self.update(changed)
        particle, shader = (self.scene.elements.get(kind=kind) for kind in ("particles", "shaders"))
        self.assertEqual((particle.data["x"], particle.data["y"]), (160, 320))
        self.assertEqual((shader.data["x"], shader.data["y"], shader.data["radius"]), (832, 192, 2.75))
        self.assertEqual(self.scene.elements.get(kind="lights").data["bright_radius"], 2)

    def test_reusing_an_owned_effect_id_for_another_kind_is_a_conflict(self):
        self.generated()
        before = {str(row.pk): (row.kind, deepcopy(row.data)) for row in self.scene.elements.all()}
        changed = deepcopy(self.doc)
        changed["shaders"].append({**deepcopy(changed["shaders"][0]), "id": changed["particles"][0]["id"]})
        changed["particles"] = []
        with self.assertRaisesMessage(services.MapError, "changed type"):
            self.update(changed)
        self.assertEqual({str(row.pk): (row.kind, row.data) for row in self.scene.elements.all()}, before)

    def test_effects_and_lights_do_not_change_generated_raster_pixels(self):
        without = deepcopy(self.doc)
        without["particles"], without["shaders"], without["lights"] = [], [], []
        first = builder_render.render(without, self.campaign.pk)
        self.addCleanup(first.close)
        second = builder_render.render(self.doc, self.campaign.pk)
        self.addCleanup(second.close)
        with Image.open(first) as first_image, Image.open(second) as second_image:
            self.assertEqual(first_image.tobytes(), second_image.tobytes())

    def test_generate_retry_does_not_duplicate_native_effects(self):
        self.assertEqual(self.save().status_code, 200)
        request = str(uuid.uuid4())
        first = self.generate(request_id=request)
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(self.generate(request_id=request).json(), first.json())
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(SceneObject.objects.filter(kind="particles").count(), 1)
        self.assertEqual(SceneObject.objects.filter(kind="shaders").count(), 1)

    def test_campaign_clone_remaps_effect_ownership_and_preserves_authored_shader_text(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        self.doc["shaders"][0]["name"] = f"Mist {self.floor.pk}"
        self.doc["shaders"][0]["source"] = f"// Texture {self.floor.pk}\n" + self.doc["shaders"][0]["source"]
        self.generated()
        source_text = self.doc["shaders"][0]["source"]
        name = self.doc["shaders"][0]["name"]
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Native effect clone")
        project = MapBuilderProject.objects.get(campaign=restored)
        shader = project.scene.elements.get(kind="shaders")
        self.assertNotEqual(project.scene_id, self.scene.pk)
        self.assertEqual((shader.data["name"], shader.data["source"]), (name, source_text))
        self.assertEqual(project.document["shaders"][0]["source"], source_text)
        generated = next(row for row in project.generation["objects"] if row["kind"] == "shaders")
        self.assertEqual(generated["data"]["source"], source_text)
        self.assertEqual(generated["id"], str(shader.pk))
        builder_services.update(restored.pk, self.gm.pk, project.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": project.version,
             "expected_scene_version": project.scene.version})
        shader.refresh_from_db()
        self.assertEqual(shader.data["source"], source_text)

    @override_settings(DYNAMIC_LIGHTING_ENABLED=False)
    def test_effects_remain_available_when_native_dynamic_lighting_is_disabled(self):
        self.doc["lights"] = []
        self.generated()
        self.assertTrue(self.scene.elements.filter(kind="particles").exists())
        self.assertTrue(self.scene.elements.filter(kind="shaders").exists())
