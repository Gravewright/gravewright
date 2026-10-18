"""Public rehearsal, live-control and interchange routes retain HTTP boundaries."""

from copy import deepcopy
import json
from unittest.mock import patch
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import Client, TestCase, override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from gravewright.actors.models import Actor
from gravewright.campaigns.models import Membership
from gravewright.maps import universal_vtt
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Receipt, Scene, SceneObject

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import node
from .test_blueprint_events import definition, graph
from . import test_universal_vtt as uvtt_fixtures


def chain(*actions):
    return definition(interact=graph("interact", *actions))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class InterchangeViewTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    uvtt_document = uvtt_fixtures.UniversalVttTests.document

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = chain()
        self.generated()
        self.catalog_url = self.base + "/testing-catalog"
        self.draft_url = self.base + "/test"
        self.scene_url = f"/api/maps/{self.scene.pk}/automation/test/{self.door_object.pk}"
        self.control_url = f"/api/maps/{self.scene.pk}/automation/control/{self.door_object.pk}"
        self.import_url = f"/api/containers/{self.campaign.pk}/universal-vtt/import"
        self.export_url = f"/api/maps/{self.scene.pk}/universal-vtt"

    def draft_payload(self):
        return {"request_id": str(uuid.uuid4()), "document": deepcopy(self.doc),
                "elementId": self.doc["doors"][0]["id"], "event": "interact"}

    def scene_payload(self):
        return {"request_id": str(uuid.uuid4()), "expected_version": self.door_object.version,
                "event": "interact"}

    def control_payload(self):
        return {"request_id": str(uuid.uuid4()), "expected_version": self.door_object.version,
                "action": "state", "value": "open"}

    def upload(self, content=None, **extra):
        return {"file": SimpleUploadedFile("synthetic.uvtt", content if content is not None else
                    json.dumps(self.uvtt_document()).encode(), content_type="application/json"),
                "name": "Imported through HTTP", "request_id": str(uuid.uuid4()), **extra}

    def test_http_methods_are_restricted_before_domain_work(self):
        for url in (self.draft_url, self.scene_url, self.control_url, self.import_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
        for url in (self.catalog_url, self.export_url):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 405)

    def test_anonymous_requests_do_not_run_domain_work_or_read_private_catalog(self):
        self.client.logout()
        with patch("gravewright.maps.universal_vtt.parse") as parser, patch("gravewright.maps.universal_vtt._raster") as raster:
            self.assertEqual(self.client.get(self.catalog_url).status_code, 403)
            self.assertEqual(self.client.post(self.draft_url, self.draft_payload(), content_type="application/json").status_code, 403)
            self.assertEqual(self.client.post(self.scene_url, self.scene_payload(), content_type="application/json").status_code, 404)
            self.assertEqual(self.client.post(self.control_url, self.control_payload(), content_type="application/json").status_code, 404)
            self.assertEqual(self.client.post(self.import_url, self.upload()).status_code, 403)
            self.assertEqual(self.client.get(self.export_url).status_code, 404)
        parser.assert_not_called()
        raster.assert_not_called()

    def test_player_and_active_streamer_cannot_test_control_import_export_or_read_actor_catalog(self):
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            with self.subTest(user=user.pk), patch("gravewright.maps.universal_vtt.parse") as parser, \
                    patch("gravewright.maps.universal_vtt._raster") as raster:
                self.assertEqual(self.client.get(self.catalog_url).status_code, 403)
                self.assertEqual(self.client.post(self.draft_url, self.draft_payload(), content_type="application/json").status_code, 403)
                self.assertEqual(self.client.post(self.scene_url, self.scene_payload(), content_type="application/json").status_code, 403)
                self.assertEqual(self.client.post(self.control_url, self.control_payload(), content_type="application/json").status_code, 403)
                self.assertEqual(self.client.post(self.import_url, self.upload()).status_code, 403)
                self.assertEqual(self.client.get(self.export_url).status_code, 403)
            parser.assert_not_called()
            raster.assert_not_called()

    def test_catalog_is_campaign_scoped_and_success_responses_are_private(self):
        actor = Actor.objects.create(campaign=self.campaign, name="Available", data={})
        Actor.objects.create(campaign=self.other, name="Private foreign actor", data={})
        response = self.client.get(self.catalog_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"actors": [{"id": str(actor.pk), "name": actor.name}]})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("foreign", response.content.decode())

    def test_real_draft_and_scene_endpoints_return_predictions_without_committing(self):
        draft = self.draft_payload()
        draft["document"]["doors"][0]["blueprint"] = chain(node("open", "state", targetState="open"))
        scene = {**self.scene_payload(), "blueprint": chain(node("open", "state", targetState="open"))}
        before_objects = list(SceneObject.objects.values("id", "data", "version"))
        before_projects = list(MapBuilderProject.objects.values("id", "document", "generation", "version"))
        counts = [model.objects.count() for model in (Scene, AutomationRun, AutomationDelay, Receipt)]
        files = self.files()
        for url, body in ((self.draft_url, draft), (self.scene_url, scene)):
            with self.subTest(url=url), patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(url, body, content_type="application/json")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertTrue(response.json()["dryRun"])
            self.assertEqual(response.json()["run"]["stateAfter"], "open")
            send.assert_not_called()
        self.assertEqual(list(SceneObject.objects.values("id", "data", "version")), before_objects)
        self.assertEqual(list(MapBuilderProject.objects.values("id", "document", "generation", "version")), before_projects)
        self.assertEqual([model.objects.count() for model in (Scene, AutomationRun, AutomationDelay, Receipt)], counts)
        self.assertEqual(self.files(), files)

    def test_live_control_endpoint_returns_cas_conflicts_and_receipt_replay(self):
        payload = self.control_payload()
        first = self.client.post(self.control_url, payload, content_type="application/json")
        replay = self.client.post(self.control_url, payload, content_type="application/json")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(Receipt.objects.filter(request_id=payload["request_id"]).count(), 1)
        changed = self.client.post(self.control_url, {**payload, "value": "closed"}, content_type="application/json")
        self.assertEqual(changed.status_code, 409)
        stale = self.client.post(self.scene_url, self.scene_payload(), content_type="application/json")
        self.assertEqual(stale.status_code, 409)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_json_is_bounded_and_malformed_input_never_invokes_services(self):
        bodies = [b"{", b"\xff", b"[" * 1100, b" " * 1_100_001]
        with patch("gravewright.maps.blueprint_testing.run_draft") as service:
            for body in bodies:
                with self.subTest(length=len(body)):
                    response = self.client.post(self.draft_url, body, content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["code"], "invalid_input")
        service.assert_not_called()

    def test_all_mutating_routes_enforce_existing_csrf_middleware(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.gm)
        for url, body in ((self.draft_url, self.draft_payload()), (self.scene_url, self.scene_payload()),
                          (self.control_url, self.control_payload())):
            with self.subTest(url=url):
                self.assertEqual(client.post(url, body, content_type="application/json").status_code, 403)
        self.assertEqual(client.post(self.import_url, self.upload()).status_code, 403)
        # Same-origin requests with a matching cookie/header keep the application's CSRF contract.
        csrf = client.get("/__gravewright/csrf").json()
        header = "HTTP_" + csrf["header"].upper().replace("-", "_")
        response = client.post(self.draft_url, self.draft_payload(), content_type="application/json", **{header: csrf["token"]})
        self.assertEqual(response.status_code, 200, response.content)

    def test_multipart_limits_reject_oversized_files_before_reading_them(self):
        for settings_limit, format_limit in ((16, 1024), (1024, 16)):
            multipart = encode_multipart(BOUNDARY, self.upload(b"X" * 32))
            with self.subTest(settings_limit=settings_limit, format_limit=format_limit), \
                    override_settings(MAP_UPLOAD_MAX_BYTES=settings_limit), \
                    patch("gravewright.maps.universal_vtt.MAX_JSON_BYTES", format_limit), \
                    patch.object(UploadedFile, "read", create=True, side_effect=AssertionError("must not read")), \
                    patch("gravewright.maps.universal_vtt.import_map") as importer:
                response = self.client.generic("POST", self.import_url, multipart, content_type=MULTIPART_CONTENT)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"], "The Universal VTT file exceeds the interchange size limit.")
            importer.assert_not_called()

    def test_import_uses_bounded_read_and_invalid_multipart_or_json_rolls_back(self):
        reads = []
        multipart = encode_multipart(BOUNDARY, self.upload(b"{}"))

        def bounded_read(upload, size=-1):
            reads.append(size)
            return upload.file.read(size)

        with patch("gravewright.maps.universal_vtt.MAX_JSON_BYTES", 128), \
                patch.object(UploadedFile, "read", bounded_read, create=True), \
                patch("gravewright.maps.universal_vtt.import_map", return_value={"synthetic": True}) as importer:
            response = self.client.generic("POST", self.import_url, multipart, content_type=MULTIPART_CONTENT)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(importer.call_args.args[2], b"{}")
            self.assertEqual(reads, [129])
        scenes, receipts, files = Scene.objects.count(), Receipt.objects.count(), self.files()
        for payload in ({"name": "Missing file"}, self.upload(b""), self.upload(b"not json"),
                        self.upload(b'{"format":0.2,"format":0.2}'), self.upload(folderId=str(self.foreign_folder.pk))):
            with self.subTest(payload=str(payload.keys())):
                self.assertEqual(self.client.post(self.import_url, payload).status_code, 400)
        self.assertEqual((Scene.objects.count(), Receipt.objects.count(), self.files()), (scenes, receipts, files))

    def test_export_is_gm_only_even_for_public_scenes_and_does_not_write_files(self):
        before, files = list(SceneObject.objects.values("id", "data", "version")), self.files()
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(response.json()["filename"].endswith(".uvtt"))
        self.assertEqual(response.json()["document"]["format"], .2)
        self.assertEqual(list(SceneObject.objects.values("id", "data", "version")), before)
        self.assertEqual(self.files(), files)
        Membership.objects.filter(campaign=self.other, user=self.gm).delete()
        foreign = Scene.objects.create(campaign=self.other, name="Private", width=64, height=64)
        self.assertEqual(self.client.get(f"/api/maps/{foreign.pk}/universal-vtt").status_code, 404)

