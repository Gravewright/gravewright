"""Campaign library isolation, ID-free bindings and independent applied drafts."""

from copy import deepcopy
from io import BytesIO
import hashlib
import json
from unittest.mock import patch
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import blueprint_templates as templates
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import BlueprintTemplate, Receipt
from gravewright.maps.services import MapError


def uid(number):
    return str(uuid.UUID(int=number))


def fixture():
    blueprint = default_blueprint()
    blueprint["version"] = 2
    blueprint["graphs"]["interact"] = {
        "nodes": [
            {"id": "event", "type": "event", "event": "interact", "x": 10, "y": 20},
            {"id": "ref", "type": "reference", "targetId": uid(1), "x": 20, "y": 20},
            {"id": "group", "type": "elementGroup", "name": uid(1), "memberType": "element",
             "targetIds": [uid(1), uid(2)], "x": 20, "y": 40},
            {"id": "light", "type": "light", "targetId": uid(3), "enabled": True, "x": 30, "y": 20},
            {"id": "delay", "type": "delay", "seconds": 5, "x": 40, "y": 20},
            {"id": "variable", "type": "setVariable", "scope": "element", "name": "identity", "valueType": "text", "value": uid(1), "x": 50, "y": 20},
        ],
        "edges": [{"from": "event", "to": "light", "output": "next", "kind": "execution"},
                  {"from": "light", "to": "delay", "output": "next", "kind": "execution"}],
    }
    bindings, seen = [], {}
    for parent, field, kind in templates.resource_slots(blueprint):
        key = (kind, parent[field])
        if key not in seen:
            row = {"id": f"binding{len(bindings) + 1}", "type": kind, "label": f"Target {len(bindings) + 1}"}
            if key == ("element", uid(1)):
                row["self"] = True
            bindings.append(row)
            seen[key] = row["id"]
        parent[field] = {"binding": seen[key]}
    parameters = [{"id": "duration", "label": "Wait", **option}
                  for option in templates.parameter_options(blueprint) if option["path"][-1] == "seconds"]
    return {"version": 1, "blueprint": blueprint, "bindings": bindings, "parameters": parameters}


class TemplateDefinitionTests(SimpleTestCase):
    def test_typed_references_share_slots_self_rebinds_and_applied_copies_are_independent(self):
        definition = fixture()
        original = deepcopy(definition)
        clean = templates.clean_definition(definition)
        self.assertEqual(clean, definition)
        first = templates.resolve_definition(clean, {"binding2": uid(20), "binding3": uid(30)}, {"duration": 2.5}, owner_id=uid(10))
        second = templates.resolve_definition(clean, {"binding2": uid(21), "binding3": uid(31)}, owner_id=uid(11))
        nodes = first["graphs"]["interact"]["nodes"]
        self.assertEqual(nodes[1]["targetId"], uid(10))
        self.assertEqual(nodes[2]["targetIds"], [uid(10), uid(20)])
        self.assertEqual(nodes[3]["targetId"], uid(30))
        self.assertEqual(nodes[4]["seconds"], 2.5)
        self.assertEqual(nodes[2]["name"], uid(1))
        self.assertEqual(nodes[5]["value"], uid(1))
        nodes[2]["targetIds"].reverse()
        nodes[5]["value"] = "changed"
        other = second["graphs"]["interact"]["nodes"]
        self.assertEqual(other[2]["targetIds"], [uid(11), uid(21)])
        self.assertEqual(other[4]["seconds"], 5)
        self.assertEqual(definition, original)

    def test_library_rejects_literal_private_ids_unused_wrong_type_and_illegal_self(self):
        for edit in (
            lambda row: row["blueprint"]["graphs"]["interact"]["nodes"][1].update(targetId=uid(1)),
            lambda row: row["bindings"][0].update(type="light"),
            lambda row: row["bindings"][0].update(self=False),
            lambda row: row["bindings"].append({"id": "unused", "type": "sound", "label": "Unused"}),
            lambda row: row["bindings"].append(deepcopy(row["bindings"][0])),
            lambda row: row["bindings"][0].update(privateId=uid(1)),
        ):
            definition = fixture()
            edit(definition)
            with self.assertRaises(MapError):
                templates.clean_definition(definition)

    def test_parameters_cannot_mutate_identity_layout_type_scope_or_reference_fields(self):
        for field in ("id", "type", "x", "scope", "name", "targetId"):
            definition = fixture()
            definition["parameters"][0]["path"] = ["graphs", "interact", "nodes", 1, field]
            with self.assertRaises(MapError):
                templates.clean_definition(definition)
        for value in (True, "5", 0, 86401, float("nan")):
            with self.assertRaises(MapError):
                templates.resolve_definition(fixture(), {"binding2": uid(2), "binding3": uid(3)}, {"duration": value}, owner_id=uid(1))

    def test_missing_unknown_and_colliding_bindings_fail_instead_of_falling_back_to_self(self):
        for bindings in ({}, {"binding2": uid(2)}, {"binding2": uid(2), "binding3": uid(3), "other": uid(4)},
                         {"binding2": "invalid", "binding3": uid(3)}, {"binding2": uid(1), "binding3": uid(3)}):
            with self.assertRaises(MapError):
                templates.resolve_definition(fixture(), bindings, owner_id=uid(1))

    def test_scalar_defaults_types_and_allowlist_paths_are_strict(self):
        for edit in (lambda row: row["parameters"][0].update(default=7),
                     lambda row: row["parameters"][0].update(type="text"),
                     lambda row: row["parameters"].append(deepcopy(row["parameters"][0])),
                     lambda row: row["parameters"][0].update(path=["__proto__"]),
                     lambda row: row.update(states=[]),
                     lambda row: row["blueprint"].update(states=[])):
            definition = fixture()
            edit(definition)
            with self.assertRaises(MapError):
                templates.clean_definition(definition)

    def test_version_one_is_preserved_and_empty_templates_are_valid(self):
        definition = {"version": 1, "blueprint": default_blueprint(), "bindings": [], "parameters": []}
        self.assertEqual(templates.resolve_definition(definition, {}, owner_id=uid(1)), default_blueprint())

    def test_deeply_nested_untrusted_definitions_fail_before_recursive_copy(self):
        definition = fixture()
        nested = "untrusted"
        for _ in range(600):
            nested = [nested]
        definition["blueprint"]["unexpected"] = nested
        with self.assertRaises(MapError):
            templates.clean_definition(definition)

    def test_presentation_bindings_are_typed_but_authored_message_is_unchanged(self):
        definition = {"version": 1, "blueprint": default_blueprint(), "bindings": [], "parameters": []}
        blueprint = definition["blueprint"]
        blueprint["version"] = 2
        blueprint["graphs"]["interact"] = {"nodes": [
            {"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
            {"id": "message", "type": "showMessage", "text": uid(9), "audience": {"scope": "users", "userIds": [{"binding": "viewer"}]}, "x": 10, "y": 20},
            {"id": "handout", "type": "showHandout", "journalId": {"binding": "handout"}, "audience": {"scope": "trigger"}, "x": 10, "y": 20},
            {"id": "teleport", "type": "teleport", "destinationId": {"binding": "destination"}, "x": 10, "y": 20},
            {"id": "appearance", "type": "setAppearance", "assetId": {"binding": "image"}, "x": 10, "y": 20}], "edges": []}
        definition["bindings"] = [{"id": key, "type": kind, "label": key} for key, kind in
                                  (("viewer", "user"), ("handout", "handout"), ("destination", "element"), ("image", "asset"))]
        resolved = templates.resolve_definition(definition, {"viewer": uid(1), "handout": uid(2), "destination": uid(3), "image": uid(4)}, owner_id=uid(5))
        nodes = resolved["graphs"]["interact"]["nodes"]
        self.assertEqual(nodes[1]["text"], uid(9))
        self.assertEqual(nodes[1]["audience"]["userIds"], [uid(1)])
        self.assertEqual(nodes[2]["journalId"], uid(2))
        self.assertEqual(nodes[3]["destinationId"], uid(3))
        self.assertEqual(nodes[4]["assetId"], uid(4))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], ALLOWED_HOSTS=["testserver"])
class TemplateLibraryTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user("template-gm@example.test", "password-12345", name="GM", role="owner")
        self.player = User.objects.create_user("template-player@example.test", "password-12345", name="Player")
        self.streamer = User.objects.create_user("template-streamer@example.test", None, name="Streamer")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Templates")
        self.other = Campaign.objects.create(owner=self.gm, name="Another campaign")
        for campaign in (self.campaign, self.other):
            Membership.objects.create(campaign=campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        Membership.objects.create(campaign=self.campaign, user=self.streamer, role="streamer")
        self.client.force_login(self.gm)
        self.template_id = uuid.uuid4()
        self.base = f"/api/containers/{self.campaign.pk}/map-builder/templates"
        self.url = f"{self.base}/{self.template_id}"
        self.payload = {"request_id": str(uuid.uuid4()), "expected_version": 0, "name": "Reusable mechanism",
                        "description": "An independent snapshot", "definition": fixture()}

    def save(self, **changes):
        return self.client.post(self.url, {**self.payload, **changes}, content_type="application/json")

    def test_save_catalog_read_update_and_delete_leave_detached_copies_intact(self):
        first = self.save()
        self.assertEqual(first.status_code, 200, first.content)
        saved = first.json()["template"]
        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["definition"], fixture())
        self.assertEqual(self.client.get(self.url).json(), first.json())
        listed = self.client.get(self.base)
        self.assertIn("no-store", listed["Cache-Control"])
        self.assertEqual(listed.json()["templates"][0]["name"], self.payload["name"])
        self.assertNotIn("definition", listed.json()["templates"][0])
        applied = templates.resolve_definition(saved["definition"], {"binding2": uid(20), "binding3": uid(30)}, owner_id=uid(10))
        changed = self.save(request_id=str(uuid.uuid4()), expected_version=1, name="New name")
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(changed.json()["template"]["version"], 2)
        command = {"request_id": str(uuid.uuid4()), "expected_version": 2}
        deleted = self.client.delete(self.url, command, content_type="application/json")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(BlueprintTemplate.objects.exists())
        self.assertEqual(applied["graphs"]["interact"]["nodes"][1]["targetId"], uid(10))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.delete(self.url, command, content_type="application/json").json(), deleted.json())

    def test_request_retries_replay_exactly_and_different_payload_reuse_is_conflict(self):
        first = self.save()
        self.assertEqual(self.save().json(), first.json())
        self.assertEqual(BlueprintTemplate.objects.count(), 1)
        self.assertEqual(self.save(name="Another operation").status_code, 409)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_stale_revision_cannot_update_or_delete(self):
        self.save()
        self.assertEqual(self.save(request_id=str(uuid.uuid4())).status_code, 409)
        self.assertEqual(self.client.delete(self.url, {"request_id": str(uuid.uuid4()), "expected_version": 0}, content_type="application/json").status_code, 409)
        self.assertEqual(BlueprintTemplate.objects.get().version, 1)

    def test_library_is_gm_only_including_retries_after_permission_revocation(self):
        self.save()
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role="player")
        self.assertEqual(self.save().status_code, 403)
        for user in (self.gm, self.player, self.streamer, None):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            self.assertIn(self.client.get(self.base).status_code, (403, 404))
            self.assertIn(self.client.get(self.url).status_code, (403, 404))
            self.assertIn(self.save(request_id=str(uuid.uuid4())).status_code, (403, 404))
            self.assertIn(self.client.delete(self.url, {"request_id": str(uuid.uuid4()), "expected_version": 1}, content_type="application/json").status_code, (403, 404))

    def test_cross_campaign_ids_and_receipts_are_isolated(self):
        self.save()
        url = f"/api/containers/{self.other.pk}/map-builder/templates/{self.template_id}"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.payload, content_type="application/json").status_code, 404)
        self.assertEqual(self.client.delete(url, {"request_id": str(uuid.uuid4()), "expected_version": 1}, content_type="application/json").status_code, 404)
        self.assertEqual(self.client.get(f"/api/containers/{self.other.pk}/map-builder/templates").json()["templates"], [])

    def test_invalid_default_bindings_and_commands_never_write(self):
        definition = fixture()
        definition["blueprint"]["graphs"]["interact"]["nodes"][3]["targetId"] = uid(999)
        for changes in ({"definition": definition}, {"name": " "}, {"description": "x" * 2001}, {"expected_version": True}, {"extra": True}):
            self.assertEqual(self.save(**changes).status_code, 400)
        self.assertFalse(BlueprintTemplate.objects.exists())
        self.assertFalse(Receipt.objects.exists())

    def test_campaign_library_limit_is_enforced(self):
        self.save()
        self.template_id = uuid.uuid4()
        self.url = f"{self.base}/{self.template_id}"
        with patch.object(templates, "MAX_TEMPLATES", 1):
            self.assertEqual(self.save(request_id=str(uuid.uuid4())).status_code, 400)
        self.assertEqual(BlueprintTemplate.objects.count(), 1)

    def test_campaign_archive_roundtrip_preserves_id_free_templates_and_authored_uuid_text(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        definition = fixture()
        nodes = definition["blueprint"]["graphs"]["interact"]["nodes"]
        nodes[2]["name"] = str(self.campaign.pk)
        nodes[5]["value"] = str(self.campaign.pk)
        response = self.save(definition=definition)
        self.assertEqual(response.status_code, 200, response.content)
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported templates")
        copied = BlueprintTemplate.objects.get(campaign=restored)
        self.assertNotEqual(copied.pk, self.template_id)
        self.assertEqual(copied.definition, definition)
        self.assertEqual(copied.name, self.payload["name"])
        self.assertEqual(copied.version, 1)
        excluded = import_campaign(export_campaign(self.campaign, {"blueprintTemplates": False}), self.gm, "No templates")
        self.assertFalse(BlueprintTemplate.objects.filter(campaign=excluded).exists())

    def test_invalid_template_in_checksummed_archive_rolls_back_import(self):
        from gravewright.accounts.services import AuthError
        from gravewright.administration.archives import export_campaign, import_campaign
        self.save()
        with ZipFile(BytesIO(export_campaign(self.campaign))) as original:
            blobs = {name: original.read(name) for name in original.namelist()}
        payload = json.loads(blobs["campaign.json"])
        row = next(row for row in payload["records"] if row["model"] == "gravewright_maps.blueprinttemplate")
        row["fields"]["definition"]["blueprint"]["graphs"]["interact"]["nodes"][1]["targetId"] = uid(999)
        blobs["campaign.json"] = json.dumps(payload).encode()
        manifest = json.loads(blobs["manifest.json"])
        manifest["files"]["campaign.json"] = {"sha256": hashlib.sha256(blobs["campaign.json"]).hexdigest(), "bytes": len(blobs["campaign.json"])}
        blobs["manifest.json"] = json.dumps(manifest).encode()
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for name, value in blobs.items():
                archive.writestr(name, value)
        count = Campaign.objects.count()
        with self.assertRaises(AuthError):
            import_campaign(output.getvalue(), self.gm, "Invalid templates")
        self.assertEqual(Campaign.objects.count(), count)
        self.assertEqual(BlueprintTemplate.objects.count(), 1)
