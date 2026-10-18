"""Scene-directory editing links are campaign-scoped and projected only to GMs."""

from datetime import timedelta
import json

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from gravewright.campaigns.models import StreamerLink
from gravewright.maps import services
from gravewright.maps.models import Broadcast, MapBuilderProject, Scene

from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderSceneDirectoryTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.scene = Scene.objects.create(campaign=self.campaign, folder=self.folder,
            name="Linked builder scene", width=512, height=512, visibility="players")
        self.plain = Scene.objects.create(campaign=self.campaign, name="Ordinary scene", width=512, height=512)
        self.project = MapBuilderProject.objects.create(id=self.project_id, campaign=self.campaign,
            folder=self.folder, scene=self.scene, name="Editable source", document=self.doc,
            generation={"privateMarker": "Synthetic private generation metadata"})
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="a" * 64,
            expires_at=timezone.now() + timedelta(hours=1))
        self.directory_url = f"/api/containers/{self.campaign.pk}/scenes"

    def directory(self, campaign=None, user=None):
        return services.state((campaign or self.campaign).pk, (user or self.gm).pk)

    def test_only_linked_gm_rows_receive_the_editable_project_identifier(self):
        maps = {row["id"]: row for row in self.directory()["maps"]}
        linked = maps[str(self.scene.pk)]
        self.assertEqual(linked["builderProjectId"], str(self.project.pk))
        self.assertNotIn("builderProjectId", maps[str(self.plain.pk)])
        self.assertNotIn("builderProjectId", services.view(self.scene))
        self.assertEqual({key: value for key, value in linked.items() if key != "builderProjectId"},
                         services.view(self.scene))
        self.assertNotIn("privateMarker", json.dumps(maps))
        self.assertNotIn("document", linked)
        response = self.client.get(self.directory_url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["maps"], self.directory()["maps"])

    def test_player_and_active_streamer_keep_exact_public_rows_and_never_query_projects(self):
        for user in (self.player, self.streamer):
            with self.subTest(role=user.name), CaptureQueriesContext(connection) as captured:
                state = self.directory(user=user)
            self.assertFalse(state["is_gm"])
            self.assertEqual(state["maps"], [services.view(self.scene)])
            self.assertEqual(state["folders"], [])
            self.assertNotIn(str(self.project.pk), json.dumps(state))
            self.assertFalse(any("gravewright_maps_mapbuilderproject" in query["sql"] for query in captured))
            self.client.force_login(user)
            response = self.client.get(self.directory_url)
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json(), state)
            self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_untrusted_scene_settings_cannot_forge_or_leak_builder_metadata(self):
        forged = "33333333-3333-4333-8333-333333333333"
        for row in (self.scene, self.plain):
            row.settings = {"builderProjectId": forged}
            row.save(update_fields=["settings"])
        maps = {row["id"]: row for row in self.directory()["maps"]}
        self.assertEqual(maps[str(self.scene.pk)]["builderProjectId"], str(self.project.pk))
        self.assertNotIn("builderProjectId", maps[str(self.plain.pk)])
        for user in (self.player, self.streamer):
            state = self.directory(user=user)
            self.assertEqual(state["maps"], [{key: value for key, value in services.view(self.scene).items()
                                             if key != "builderProjectId"}])
            self.assertNotIn(forged, json.dumps(state))
            self.assertNotIn(str(self.project.pk), json.dumps(state))

    def test_campaign_mismatched_links_do_not_cross_directory_boundaries(self):
        foreign_scene = Scene.objects.create(campaign=self.other, name="Foreign scene", width=512, height=512)
        foreign_source = MapBuilderProject.objects.create(campaign=self.other, scene=self.scene,
            name="Incorrect foreign link", document={})
        local_source = MapBuilderProject.objects.create(campaign=self.campaign, scene=foreign_scene,
            name="Incorrect local link", document={})
        maps = {row["id"]: row for row in self.directory()["maps"]}
        self.assertEqual(maps[str(self.scene.pk)]["builderProjectId"], str(self.project.pk))
        self.assertNotIn(str(foreign_scene.pk), maps)
        self.assertNotIn(str(foreign_source.pk), json.dumps(maps))
        self.assertNotIn(str(local_source.pk), json.dumps(maps))
        other_maps = self.directory(campaign=self.other)["maps"]
        self.assertEqual(len(other_maps), 1)
        self.assertNotIn("builderProjectId", other_maps[0])

    def test_detaching_or_deleting_the_source_removes_the_directory_action(self):
        MapBuilderProject.objects.filter(pk=self.project.pk).update(scene=None)
        self.assertTrue(all("builderProjectId" not in row for row in self.directory()["maps"]))
        MapBuilderProject.objects.filter(pk=self.project.pk).update(scene=self.scene)
        self.assertEqual(next(row for row in self.directory()["maps"] if row["id"] == str(self.scene.pk))["builderProjectId"], str(self.project.pk))
        self.project.delete()
        self.assertTrue(all("builderProjectId" not in row for row in self.directory()["maps"]))
        self.assertTrue(Scene.objects.filter(pk=self.scene.pk).exists())

    def test_regeneration_links_only_the_scene_that_the_project_will_update(self):
        first = self.generate()
        self.assertEqual(first.status_code, 200, first.content)
        first_id = first.json()["scene"]["id"]
        second = self.generate()
        self.assertEqual(second.status_code, 200, second.content)
        second_id = second.json()["scene"]["id"]
        self.assertNotEqual(first_id, second_id)
        maps = {row["id"]: row for row in self.directory()["maps"]}
        self.assertNotIn("builderProjectId", maps[first_id])
        self.assertNotIn("builderProjectId", maps[str(self.scene.pk)])
        self.assertEqual(maps[second_id]["builderProjectId"], str(self.project.pk))
        self.project.refresh_from_db()
        self.assertEqual(str(self.project.scene_id), second_id)

    def test_duplicate_links_choose_latest_source_then_stable_identifier(self):
        duplicate = MapBuilderProject.objects.create(campaign=self.campaign, scene=self.scene,
            name="Newer source", document={})
        linked = next(row for row in self.directory()["maps"] if row["id"] == str(self.scene.pk))
        self.assertEqual(linked["builderProjectId"], str(duplicate.pk))
        same_time = timezone.now()
        MapBuilderProject.objects.filter(pk__in=(self.project.pk, duplicate.pk)).update(updated_at=same_time)
        linked = next(row for row in self.directory()["maps"] if row["id"] == str(self.scene.pk))
        self.assertEqual(linked["builderProjectId"], min(str(self.project.pk), str(duplicate.pk)))

    def test_query_count_stays_constant_and_project_query_reads_only_identifiers(self):
        with CaptureQueriesContext(connection) as baseline:
            self.directory()
        for index in range(20):
            scene = Scene.objects.create(campaign=self.campaign, name=f"Synthetic scene {index}", width=512, height=512)
            MapBuilderProject.objects.create(campaign=self.campaign, scene=scene,
                name=f"Synthetic source {index}", document={"privateDocument": "Not required by the directory"})
        with CaptureQueriesContext(connection) as expanded:
            maps = self.directory()["maps"]
        self.assertEqual(len(maps), 22)
        self.assertEqual(len(expanded), len(baseline))
        project_queries = [query["sql"] for query in expanded if "gravewright_maps_mapbuilderproject" in query["sql"]]
        self.assertEqual(len(project_queries), 1)
        self.assertNotIn('"document"', project_queries[0])
        self.assertNotIn('"generation"', project_queries[0])

    def test_campaign_clone_and_snapshot_keep_the_correct_project_scene_association(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        clone = import_campaign(export_campaign(self.campaign), self.gm, "Cloned builder directory")
        source = MapBuilderProject.objects.get(campaign=clone)
        self.assertNotEqual(source.pk, self.project.pk)
        rows = self.directory(campaign=clone)["maps"]
        linked = next(row for row in rows if row["id"] == str(source.scene_id))
        self.assertEqual(linked["builderProjectId"], str(source.pk))
        self.assertNotIn(str(self.project.pk), json.dumps(rows))
        snapshot = export_campaign(self.campaign, snapshot=True)
        MapBuilderProject.objects.filter(pk=self.project.pk).update(scene=None)
        import_campaign(snapshot, self.gm, target=self.campaign)
        linked = next(row for row in self.directory()["maps"] if row["id"] == str(self.scene.pk))
        self.assertEqual(linked["builderProjectId"], str(self.project.pk))
