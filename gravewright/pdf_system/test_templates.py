"""Portable layout boundaries, GM authorization and atomic batch application."""

import json
from copy import deepcopy
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps.services import MapError

from .schema import normalize
from .templates import apply_bundle, command, list_templates, normalize_bundle, parse_bundle

FIELD_ID = "617f240c-0562-40d1-8c19-28041ed7f707"
FIELD_KEY = "manual_" + FIELD_ID.replace("-", "")


def bundle():
    return {"format": "gravewright.pdf-mapping", "version": 1,
            "manualFields": [{"id": FIELD_ID, "page": 1, "type": "number", "name": "Vitality",
                              "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}],
            "fieldActions": [{"field": FIELD_KEY, "roll": {"formula": "1d20 + @value", "label": "Check"}}],
            "calculatedFields": [], "fieldBindings": [], "bindings": {"bar1Value": FIELD_KEY}}


class MappingBundleTests(SimpleTestCase):
    def test_portable_round_trip_contains_no_source_or_character_values(self):
        raw = bundle()
        self.assertEqual(normalize_bundle(raw), raw)
        self.assertEqual(parse_bundle(json.dumps(raw).encode()), raw)
        self.assertEqual(raw, bundle())

    def test_untrusted_import_rejects_unknown_content_duplicate_keys_and_excess_size(self):
        bad = [{**bundle(), "pdf": "copyrighted bytes"}, {**bundle(), "fields": {"private": 42}},
               {**bundle(), "version": True}, {**bundle(), "version": 2},
               {**bundle(), "manualFields": [{**bundle()["manualFields"][0], "source": "template:generic"}]},
               {**bundle(), "bindings": {"unknown": "HP"}},
               {**bundle(), "bindings": {"bar1Value": 12}}]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(MapError): normalize_bundle(raw)
        for raw in (b"{", b"\xff", b"[]", b'{"version":1,"version":2}', b" " * 1_000_001,
                    json.dumps({**bundle(), "document": {"pageCount": 1, "pages": [], "fingerprint": "x" * 129}})):
            with self.subTest(raw=str(raw)[:40]), self.assertRaises(MapError): parse_bundle(raw)

    def test_document_metadata_is_bounded_and_contains_only_page_geometry(self):
        raw = {**bundle(), "document": {"pageCount": 2, "pages": [{"page": 2, "width": 800, "height": 600, "rotation": 90}], "fingerprint": "opaque-hash"}}
        self.assertEqual(normalize_bundle(raw), raw)
        for document in ({"pageCount": 0}, {"pageCount": 1, "assetId": str(uuid4())},
                         {"pageCount": 1, "pages": [{"page": 1, "width": -1, "height": 10, "rotation": 0}]},
                         {"pageCount": 1, "pages": [{"page": 2, "width": 10, "height": 10, "rotation": 0}]}):
            with self.subTest(document=document), self.assertRaises(MapError): normalize_bundle({**bundle(), "document": document})

    def test_legacy_duplicate_token_bindings_round_trip_without_changing_bar_values(self):
        raw = bundle()
        raw["bindings"] = {"bar1Value": FIELD_KEY, "bar1Max": FIELD_KEY}
        self.assertEqual(parse_bundle(json.dumps(raw)), raw)
        data = normalize({"bars": {"bar_1": {"value": 9, "max": 20}}})
        candidate = apply_bundle(data, raw, "template:generic")
        self.assertEqual(candidate["token"]["bars"]["bar1Value"], FIELD_KEY)
        self.assertEqual(candidate["token"]["bars"]["bar1Max"], FIELD_KEY)
        self.assertEqual(candidate["bars"], data["bars"])

    def test_apply_preserves_other_sources_names_values_and_pdf_settings(self):
        other = {**bundle()["manualFields"][0], "id": str(uuid4()), "source": "template:other"}
        data = normalize({"pdf": {"manualFields": [other], "zoom": 2},
                          "fields": {FIELD_KEY: 13, "Private_notes": "Never export"},
                          "bars": {"bar_1": {"value": 17, "max": 30}}, "bio": "Biography"})
        saved = apply_bundle(data, bundle(), "template:generic")
        self.assertEqual(saved["fields"], data["fields"])
        self.assertEqual(saved["bars"], data["bars"])
        self.assertEqual(saved["bio"], "Biography")
        self.assertEqual(saved["pdf"]["zoom"], 2)
        self.assertIn(other, saved["pdf"]["manualFields"])
        self.assertEqual(data["pdf"]["manualFields"], [other])
        self.assertEqual(saved["token"]["bars"]["bar1Value"], FIELD_KEY)

    def test_apply_rejects_changed_source_and_cross_document_uuid_collision(self):
        data = normalize({})
        with self.assertRaises(MapError) as caught: apply_bundle(data, bundle(), "template:other")
        self.assertEqual(caught.exception.code, "conflict")
        data["pdf"]["manualFields"] = [{**bundle()["manualFields"][0], "source": "template:other"}]
        with self.assertRaises(MapError): apply_bundle(data, bundle(), "template:generic")

    def test_native_bindings_and_calculations_are_portable_and_recomputed_on_apply(self):
        raw = bundle()
        raw["bindings"] = {}
        raw["fieldBindings"] = [{"field": "Ability Score", "path": "sheet.fields.Ability_Score", "type": "number", "name": "Ability"}]
        raw["calculatedFields"] = [{"field": FIELD_KEY, "formula": "@{Ability Score} * 2"}]
        raw["fieldActions"][0]["roll"]["formula"] = "1d20 + @{Ability Score} + @value"
        self.assertEqual(normalize_bundle(raw), raw)
        data = normalize({"fields": {"Ability_Score": 7}})
        applied = apply_bundle(data, raw, "template:generic")
        self.assertEqual(applied["fields"][FIELD_KEY], 14)
        self.assertEqual(applied["fields"]["Ability_Score"], 7)
        raw["calculatedFields"][0]["formula"] = f"@{{{FIELD_KEY}}} + 1"
        with self.assertRaises(MapError): normalize_bundle(raw)

    def test_mapping_document_descriptor_is_retained_for_target_diagnostics(self):
        raw = bundle()
        raw["document"] = {"pageCount": 1, "pages": [{"page": 1, "width": 600, "height": 800, "rotation": 0}], "fingerprint": "expected-document"}
        other = {"source": "template:other", "pageCount": 1, "pages": [], "fingerprint": "other-document"}
        data = normalize({"pdf": {"sourceMetadata": [other]}})
        candidate = apply_bundle(data, raw, "template:generic")
        self.assertEqual(candidate["pdf"]["sourceMetadata"], [other, {"source": "template:generic", **raw["document"]}])
        raw["document"]["pages"][0]["width"] = 32769
        with self.assertRaises(MapError): normalize_bundle(raw)

    def test_binding_import_rejects_prototype_paths_and_unavailable_formula_references(self):
        for path in ("sheet.fields.__proto__", "sheet.fields.a.b", "core.name", "sheet.token.size"):
            raw = bundle()
            raw["fieldBindings"] = [{"field": "HP", "path": path, "type": "number", "name": "HP"}]
            with self.subTest(path=path), self.assertRaises(MapError): normalize_bundle(raw)
        raw = bundle()
        raw["fieldActions"][0]["roll"]["formula"] = "1d20 + @{Unavailable}"
        with self.assertRaises(MapError): normalize_bundle(raw)


@override_settings(ROOT_URLCONF="gravewright.pdf_system.urls", CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class MappingLibraryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from gravewright.accounts.models import User
        from gravewright.actors.models import Actor
        from gravewright.campaigns.models import Campaign, Membership
        cls.gm = User.objects.create(email="mapping-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="mapping-player@example.test", name="Player")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="PDF library", system="gravewright-pdf-system")
        cls.other = Campaign.objects.create(owner=cls.gm, name="Other PDF library", system="gravewright-pdf-system")
        for campaign in (cls.campaign, cls.other): Membership.objects.create(campaign=campaign, user=cls.gm, role="gm")
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role="player")
        cls.first = Actor.objects.create(campaign=cls.campaign, name="Ada", data=normalize({"fields": {FIELD_KEY: 12}}))
        cls.second = Actor.objects.create(campaign=cls.campaign, name="Lin", data=normalize({"fields": {FIELD_KEY: 7}}))

    def create(self):
        return command(self.campaign.pk, self.gm.pk, {"action": "create", "requestId": str(uuid4()), "name": "Shared sheet", "bundle": bundle()})

    def target(self, actor):
        actor.refresh_from_db()
        return {"actorId": str(actor.pk), "version": actor.version, "sheetVersion": actor.sheet_version, "source": "template:generic"}

    def test_receipts_replay_create_and_revision_conflicts_preserve_template(self):
        from .models import MappingTemplate
        payload = {"action": "create", "requestId": str(uuid4()), "name": "Shared sheet", "bundle": bundle()}
        first = command(self.campaign.pk, self.gm.pk, payload)
        self.assertEqual(command(self.campaign.pk, self.gm.pk, payload), first)
        self.assertEqual(MappingTemplate.objects.count(), 1)
        update = {**payload, "requestId": str(uuid4()), "action": "update", "id": first["id"], "revision": 1, "name": "Updated"}
        self.assertEqual(command(self.campaign.pk, self.gm.pk, update)["revision"], 2)
        with self.assertRaises(MapError) as caught: command(self.campaign.pk, self.gm.pk, {**update, "requestId": str(uuid4())})
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual(MappingTemplate.objects.get().name, "Updated")

    def test_gm_only_library_and_cross_campaign_isolation(self):
        row = self.create()
        with self.assertRaises(MapError): list_templates(self.campaign.pk, self.player.pk)
        with self.assertRaises(MapError): command(self.campaign.pk, self.player.pk, {"action": "delete", "id": row["id"], "revision": 1, "requestId": str(uuid4())})
        with self.assertRaises(MapError): command(self.other.pk, self.gm.pk, {"action": "delete", "id": row["id"], "revision": 1, "requestId": str(uuid4())})
        self.assertEqual(len(list_templates(self.campaign.pk, self.gm.pk)["items"]), 1)
        self.assertEqual(list_templates(self.other.pk, self.gm.pk), {"items": []})

    def test_batch_applies_all_and_retries_without_mutating_values_or_names(self):
        row = self.create()
        payload = {"action": "apply", "id": row["id"], "revision": 1, "requestId": str(uuid4()), "targets": [self.target(self.first), self.target(self.second)]}
        first = command(self.campaign.pk, self.gm.pk, payload)
        self.assertEqual(command(self.campaign.pk, self.gm.pk, payload), first)
        for actor, name, value in ((self.first, "Ada", 12), (self.second, "Lin", 7)):
            actor.refresh_from_db()
            self.assertEqual(actor.name, name)
            self.assertEqual(actor.data["fields"][FIELD_KEY], value)
            self.assertEqual(actor.sheet_version, 2)
            self.assertEqual(actor.data["pdf"]["manualFields"][0]["name"], "Vitality")

    def test_batch_stale_revision_and_invalid_second_actor_roll_back_first(self):
        row = self.create()
        targets = [self.target(self.first), self.target(self.second)]
        for invalid in ("revision", "value"):
            with self.subTest(invalid=invalid):
                candidates = deepcopy(targets)
                if invalid == "revision": candidates[1]["sheetVersion"] = 999
                else:
                    self.second.data["fields"][FIELD_KEY] = "Incompatible stored value"
                    self.second.save(update_fields=["data"])
                with self.assertRaises(MapError):
                    command(self.campaign.pk, self.gm.pk, {"action": "apply", "id": row["id"], "revision": 1, "requestId": str(uuid4()), "targets": candidates})
                self.first.refresh_from_db()
                self.assertEqual(self.first.sheet_version, 1)
                self.assertNotIn("manualFields", self.first.data["pdf"])

    def test_batch_rejects_foreign_actor_and_preserves_unlinked_token_snapshots(self):
        from gravewright.actors.models import Actor
        from gravewright.maps.models import Scene
        from gravewright.tokens.models import Token
        row = self.create()
        foreign = Actor.objects.create(campaign=self.other, name="Foreign", data=normalize({}))
        with self.assertRaises(MapError):
            command(self.campaign.pk, self.gm.pk, {"action": "apply", "id": row["id"], "revision": 1,
                                                  "requestId": str(uuid4()), "targets": [self.target(self.first), self.target(foreign)]})
        self.first.refresh_from_db()
        self.assertEqual(self.first.sheet_version, 1)
        scene = Scene.objects.create(campaign=self.campaign, name="Snapshot scene", width=500, height=500)
        snapshot = deepcopy(self.first.data)
        independent = Token.objects.create(scene=scene, actor=self.first, linked=False, snapshot=snapshot)
        linked = Token.objects.create(scene=scene, actor=self.first, linked=True)
        old_linked_version = linked.version
        command(self.campaign.pk, self.gm.pk, {"action": "apply", "id": row["id"], "revision": 1,
                                              "requestId": str(uuid4()), "targets": [self.target(self.first)]})
        independent.refresh_from_db()
        linked.refresh_from_db()
        self.assertEqual(independent.snapshot, snapshot)
        self.assertEqual(independent.sheet_version, 1)
        self.assertEqual(linked.version, old_linked_version + 1)

    def test_http_export_contains_layout_only_and_player_requests_are_denied(self):
        row = self.create()
        base = f"/api/containers/{self.campaign.pk}/pdf-mappings"
        self.client.force_login(self.gm)
        response = self.client.get(f"{base}/{row['id']}/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), bundle())
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertNotIn("Never export", response.content.decode())
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(base).status_code, 403)
        self.assertEqual(self.client.get(f"{base}/{row['id']}/export").status_code, 403)
        self.assertEqual(self.client.post(base, json.dumps({"action": "create", "name": "No", "bundle": bundle(), "requestId": str(uuid4())}), content_type="application/json").status_code, 403)

    def test_http_import_validates_original_json_text_before_creating_any_template(self):
        from .models import MappingTemplate
        self.client.force_login(self.gm)
        base = f"/api/containers/{self.campaign.pk}/pdf-mappings"

        def post(raw):
            return self.client.post(base, json.dumps({"action": "import", "name": "Imported mapping",
                                                     "bundle": raw, "requestId": str(uuid4())}), content_type="application/json")

        original = json.dumps(bundle())
        response = post(original)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["bundle"], bundle())
        self.assertEqual(MappingTemplate.objects.count(), 1)
        for raw in (original[:-1] + ', "version": 1}', original.replace('"x": 0.1', '"x": NaN'),
                    original.replace('"x": 0.1', '"x": Infinity'), "{"):
            with self.subTest(raw=raw[-50:]):
                response = post(raw)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["message"], "Invalid PDF mapping JSON.")
                self.assertEqual(MappingTemplate.objects.count(), 1)
        self.assertEqual(post(bundle()).status_code, 200)
        self.assertEqual(MappingTemplate.objects.count(), 2)
        # The file itself fits 1 MB even when JSON escaping doubles its envelope.
        padded = original + "\t" * (1_000_000 - len(original.encode("utf-8")))
        self.assertEqual(post(padded).status_code, 200)
        self.assertEqual(MappingTemplate.objects.count(), 3)
        self.assertEqual(post(padded + " ").status_code, 400)
        self.assertEqual(MappingTemplate.objects.count(), 3)

    def test_campaign_clone_and_snapshot_restore_keep_templates_and_values(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.actors.models import Actor
        from .models import MappingTemplate
        row = self.create()
        template = MappingTemplate.objects.get(pk=row["id"])
        template.bundle["manualFields"][0]["name"] = str(self.first.pk)
        template.revision = 3
        template.save()
        original = deepcopy(template.bundle)
        raw = export_campaign(self.campaign, snapshot=True)
        cloned = import_campaign(raw, self.gm, "Cloned mapping campaign")
        copied = MappingTemplate.objects.get(campaign=cloned)
        self.assertNotEqual(copied.pk, template.pk)
        self.assertEqual(copied.bundle, original)
        self.assertEqual(copied.revision, 3)
        self.assertEqual(Actor.objects.get(campaign=cloned, name="Ada").data["fields"][FIELD_KEY], 12)
        template.delete()
        self.first.data["fields"][FIELD_KEY] = 99
        self.first.save(update_fields=["data"])
        import_campaign(raw, self.gm, target=self.campaign)
        restored = MappingTemplate.objects.get(pk=row["id"])
        self.assertEqual(restored.bundle, original)
        self.assertEqual(restored.revision, 3)
        self.first.refresh_from_db()
        self.assertEqual(self.first.data["fields"][FIELD_KEY], 12)

    def test_actor_exclusion_also_omits_mapping_library(self):
        from gravewright.administration.archives import options, records
        self.create()
        self.assertNotIn("gravewright_pdf_system.mappingtemplate", {
            row["model"] for row in records(self.campaign, options({"actors": False}))})
