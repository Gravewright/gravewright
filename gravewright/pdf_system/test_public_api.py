"""Public PDF capabilities retain native permissions, revisions and receipts."""

from copy import deepcopy
import json
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase, override_settings

from api import pdf_system
from gravewright.maps.services import MapError

from . import public
from .schema import normalize

SCORE_ID = "bb0f62bd-12df-463a-b432-02072c5e2a31"
TOTAL_ID = "bb0f62bd-12df-463a-b432-02072c5e2a32"
SCORE = "manual_" + SCORE_ID.replace("-", "")
TOTAL = "manual_" + TOTAL_ID.replace("-", "")
SOURCE = "template:generic"


def definition(identifier, name, page=1):
    return {"id": identifier, "source": SOURCE, "page": page, "type": "number", "name": name,
            "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.04}


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class PublicPdfApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from gravewright.accounts.models import User
        from gravewright.actors.models import Actor
        from gravewright.campaigns.models import Campaign, Membership
        from gravewright.maps.models import Broadcast, Scene
        from gravewright.tokens.models import Token
        cls.gm = User.objects.create(email="pdf-public-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="pdf-public-player@example.test", name="Player")
        cls.observer = User.objects.create(email="pdf-public-reader@example.test", name="Observer")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="Public PDF API", system="gravewright-pdf-system")
        cls.other = Campaign.objects.create(owner=cls.gm, name="Other PDF API", system="gravewright-pdf-system")
        for campaign in (cls.campaign, cls.other): Membership.objects.create(campaign=campaign, user=cls.gm, role="gm")
        Membership.objects.create(campaign=cls.campaign, user=cls.player, role="player")
        Membership.objects.create(campaign=cls.campaign, user=cls.observer, role="player")
        data = normalize({"pdf": {"manualFields": [definition(SCORE_ID, "Score", 2), definition(TOTAL_ID, "Total")],
                                  "fieldActions": [{"source": SOURCE, "field": SCORE, "roll": {"formula": f"1d1 + @value + @{{{TOTAL}}}", "label": "Check"}}],
                                  "sourceMetadata": [{"source": SOURCE, "pageCount": 2, "pages": [{"page": 1, "width": 600, "height": 800, "rotation": 0}], "fingerprint": "expected"}]},
                          "fields": {SCORE: 10, TOTAL: 20}, "notes": "BASE_PRIVATE"})
        cls.actor = Actor.objects.create(campaign=cls.campaign, name="Base Hidden", data=data,
                                         permissions={str(cls.player.pk): "owner", str(cls.observer.pk): "observer"})
        cls.foreign = Actor.objects.create(campaign=cls.other, name="Foreign", data=normalize({}))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name="PDF scene", width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)
        snapshot = deepcopy(data)
        snapshot["token"]["name"] = "Snapshot Ada"
        snapshot["notes"] = "SNAPSHOT_PRIVATE"
        snapshot["fields"].update({SCORE: 4, TOTAL: 8})
        cls.token = Token.objects.create(scene=cls.scene, actor=cls.actor, linked=False, snapshot=snapshot)

    def view(self, user=None, snapshot=False):
        return pdf_system.state(self.campaign.pk, (user or self.gm).pk, self.actor.pk, self.token.pk if snapshot else None)

    def configure(self, changes, *, user=None, view=None, request_id=None, snapshot=False):
        view = view or self.view(user, snapshot)
        return pdf_system.configure(self.campaign.pk, (user or self.gm).pk, self.actor.pk, changes, request_id or uuid4(),
                                    version=view["version"], sheet_version=view["sheetVersion"], source=view["source"],
                                    token_id=self.token.pk if snapshot else None)

    def test_public_facade_is_explicit_and_snapshot_reads_do_not_substitute_base_data(self):
        self.assertIs(pdf_system.configure, public.configure)
        self.assertNotIn("normalize", pdf_system.__all__)
        view = self.view(self.player, True)
        self.assertEqual(view["name"], "Snapshot Ada")
        self.assertEqual(view["data"]["fields"][SCORE], 4)
        self.assertEqual(view["data"]["notes"], "SNAPSHOT_PRIVATE")
        self.assertNotIn("BASE_PRIVATE", json.dumps(view))
        self.assertNotIn("Base Hidden", json.dumps(view))

    def test_reads_recheck_membership_actor_permission_and_campaign_isolation(self):
        with self.assertRaises(MapError): pdf_system.state(self.campaign.pk, self.gm.pk, self.foreign.pk)
        with self.assertRaises(MapError): pdf_system.state(self.campaign.pk, self.gm.pk, self.foreign.pk, self.token.pk)
        self.campaign.memberships.filter(user=self.player).delete()
        from gravewright.journals.services import JournalError
        with self.assertRaises(JournalError): self.view(self.player)

    def test_configure_is_gm_only_and_does_not_replace_omitted_layout_or_values(self):
        changes = {"fieldActions": [{"field": SCORE, "roll": {"formula": "2d6 + @value", "label": "New check"}}]}
        with self.assertRaises(MapError): self.configure(changes, user=self.player)
        before = self.view()
        result = self.configure(changes)
        saved = self.view()
        self.assertEqual(result["sheetVersion"], before["sheetVersion"] + 1)
        self.assertEqual(saved["data"]["fields"], before["data"]["fields"])
        self.assertEqual(saved["data"]["pdf"]["manualFields"], before["data"]["pdf"]["manualFields"])
        self.assertEqual(saved["data"]["notes"], "BASE_PRIVATE")
        self.assertEqual(saved["data"]["pdf"]["fieldActions"][0]["roll"]["formula"], "2d6 + @value")

    def test_configure_replays_native_receipts_before_source_guard_without_redelivery(self):
        from gravewright.actors import services as actors
        request = uuid4()
        original = self.view()
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                result = self.configure({"bindings": {"bar1Value": SCORE}}, view=original, request_id=request)
            self.assertTrue(send.called)
            current = self.view()
            current["data"]["pdf"]["template"] = "other"
            actors.command(self.campaign.pk, self.gm.pk, "sheet.save", {**current, "actorId": str(self.actor.pk)}, uuid4())
            send.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.configure({"bindings": {}}, view=original, request_id=request), result)
            self.assertFalse(send.called)
        self.assertEqual(self.view()["source"], "template:other")

    def test_source_and_revision_conflicts_leave_data_unchanged(self):
        before = self.view()
        wrong = {**before, "source": "template:other"}
        with self.assertRaises(MapError) as caught: self.configure({"bindings": {}}, view=wrong)
        self.assertEqual(caught.exception.code, "conflict")
        stale = {**before, "sheetVersion": 99}
        with self.assertRaises(MapError) as caught: self.configure({"bindings": {}}, view=stale)
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual(self.view(), before)

    def test_outer_rollback_discards_writes_receipts_and_notifications(self):
        from gravewright.maps.models import Receipt
        request = uuid4()
        before = self.view()
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        self.configure({"bindings": {"bar1Value": SCORE}}, request_id=request)
                        raise RuntimeError("Abort")
                except RuntimeError: pass
            self.assertFalse(send.called)
        self.assertEqual(self.view(), before)
        self.assertFalse(Receipt.objects.filter(request_id=request).exists())

    def test_export_mapping_contains_layout_only_and_apply_can_target_snapshot(self):
        exported = pdf_system.export_mapping(self.campaign.pk, self.gm.pk, self.actor.pk)
        self.assertNotIn("BASE_PRIVATE", json.dumps(exported))
        self.assertNotIn("source", exported["manualFields"][0])
        self.assertNotIn("fields", exported)
        with self.assertRaises(MapError): pdf_system.export_mapping(self.campaign.pk, self.player.pk, self.actor.pk)
        exported["manualFields"][0]["name"] = "Snapshot score"
        view, base = self.view(snapshot=True), self.view()
        pdf_system.apply_mapping(self.campaign.pk, self.gm.pk, self.actor.pk, exported, uuid4(),
                                 version=view["version"], sheet_version=view["sheetVersion"], source=SOURCE, token_id=self.token.pk)
        self.assertEqual(self.view(), base)
        saved = self.view(snapshot=True)
        self.assertEqual(saved["name"], "Snapshot Ada")
        self.assertEqual(saved["data"]["pdf"]["manualFields"][0]["name"], "Snapshot score")
        self.assertEqual(saved["data"]["fields"][SCORE], 4)

    def test_export_filters_other_source_token_bindings_without_resetting_partial_configure(self):
        from gravewright.actors import services as actors
        view = self.view()
        other_id = "bb0f62bd-12df-463a-b432-02072c5e2a33"
        other_key = "manual_" + other_id.replace("-", "")
        view["data"]["pdf"]["manualFields"].append({**definition(other_id, "Other source"), "source": "template:other"})
        view["data"]["token"]["bars"].update(bar1Value=SCORE, bar1Max=other_key, bar2Value="Unindexed legacy PDF field")
        actors.command(self.campaign.pk, self.gm.pk, "sheet.save", {**view, "actorId": str(self.actor.pk)}, uuid4())
        original_choices = self.view()["data"]["token"]["bars"]
        exported = pdf_system.export_mapping(self.campaign.pk, self.gm.pk, self.actor.pk)
        self.assertEqual(exported["bindings"]["bar1Value"], SCORE)
        self.assertEqual(exported["bindings"]["bar1Max"], "")
        self.assertEqual(exported["bindings"]["bar2Value"], "")
        self.configure({"fieldActions": []})
        self.assertEqual(self.view()["data"]["token"]["bars"], original_choices)

    def test_diagnostics_compare_observations_and_never_persist_calculated_values(self):
        changes = {"calculatedFields": [{"field": TOTAL, "formula": f"100 / @{{{SCORE}}}"}]}
        self.configure(changes)
        from gravewright.actors import services as actors
        view = self.view(self.player)
        view["data"]["fields"][SCORE] = 0
        actors.command(self.campaign.pk, self.player.pk, "sheet.save", {**view, "actorId": str(self.actor.pk)}, uuid4())
        before = self.view()
        observed = {"pageCount": 1, "pages": [{"page": 1, "width": 800, "height": 600, "rotation": 90}], "fingerprint": "different"}
        result = pdf_system.diagnostics(self.campaign.pk, self.player.pk, self.actor.pk, document=observed)
        self.assertEqual({row["code"] for row in result["issues"]}, {"page-count", "page-geometry", "field-page", "calculation-value"})
        self.assertEqual(self.view(), before)

    def test_template_facade_crud_import_export_and_batch_apply_keep_native_receipts(self):
        bundle = pdf_system.export_mapping(self.campaign.pk, self.gm.pk, self.actor.pk)
        request = uuid4()
        created = pdf_system.create_template(self.campaign.pk, self.gm.pk, "Portable", bundle, request)
        self.assertEqual(pdf_system.create_template(self.campaign.pk, self.gm.pk, "Ignored retry", bundle, request), created)
        self.assertEqual(pdf_system.read_template(self.campaign.pk, self.gm.pk, created["id"]), created)
        self.assertEqual(pdf_system.list_templates(self.campaign.pk, self.gm.pk)["items"], [created])
        self.assertEqual(pdf_system.export_template(self.campaign.pk, self.gm.pk, created["id"]), bundle)
        updated = pdf_system.update_template(self.campaign.pk, self.gm.pk, created["id"], 1, "Updated", bundle, uuid4())
        view = self.view()
        result = pdf_system.apply_template(self.campaign.pk, self.gm.pk, created["id"], updated["revision"],
                                          [{"actorId": str(self.actor.pk), "version": view["version"], "sheetVersion": view["sheetVersion"], "source": SOURCE}], uuid4())
        self.assertEqual(result["items"][0]["sheetVersion"], view["sheetVersion"] + 1)
        with self.assertRaises(MapError): pdf_system.import_template(self.campaign.pk, self.gm.pk, "Bad", '{"version":1,"version":2}', uuid4())
        imported = pdf_system.import_template(self.campaign.pk, self.gm.pk, "Imported", json.dumps(bundle), uuid4())
        self.assertEqual(imported["bundle"], bundle)
        pdf_system.delete_template(self.campaign.pk, self.gm.pk, imported["id"], 1, uuid4())
        with self.assertRaises(MapError): pdf_system.read_template(self.campaign.pk, self.player.pk, created["id"])

    def test_roll_resolves_persisted_actor_and_snapshot_values_and_replays_without_rng(self):
        for snapshot, expected in ((False, 31), (True, 13)):
            with self.subTest(snapshot=snapshot):
                request = uuid4()
                result = pdf_system.roll_field(self.campaign.pk, self.player.pk, self.actor.pk, SCORE, request,
                                               token_id=self.token.pk if snapshot else None, visibility="gm")
                self.assertEqual(result["roll"]["result"]["value"]["value"], expected)
                with patch("gravewright.dice.engine.evaluate", side_effect=AssertionError("No second RNG")):
                    self.assertEqual(pdf_system.roll_field(self.campaign.pk, self.player.pk, self.actor.pk, SCORE, request,
                                                          token_id=self.token.pk if snapshot else None), result)

    def test_roll_rejects_readonly_and_source_mismatch_without_chat_messages(self):
        from gravewright.chat.models import Message
        with self.assertRaises(MapError): pdf_system.roll_field(self.campaign.pk, self.observer.pk, self.actor.pk, SCORE, uuid4())
        with self.assertRaises(MapError): pdf_system.roll_field(self.campaign.pk, self.player.pk, self.actor.pk, SCORE, uuid4(), source="template:other")
        self.assertEqual(Message.objects.count(), 0)

    def test_roll_rejects_removed_manual_target_instead_of_substituting_zero(self):
        from gravewright.chat.models import Message
        self.configure({"manualFields": [
            {key: value for key, value in definition(TOTAL_ID, "Total").items() if key != "source"}]})
        with self.assertRaises(MapError): pdf_system.roll_field(self.campaign.pk, self.player.pk, self.actor.pk, SCORE, uuid4())
        self.assertEqual(Message.objects.count(), 0)

    def test_generic_dispatch_registers_pdf_capabilities_and_rejects_streamer_writes(self):
        from api import systems
        from gravewright.campaigns.models import StreamerLink
        from gravewright.campaigns.streamer import issue
        from gravewright.journals.services import JournalError
        capabilities = systems.capabilities(self.campaign.pk, self.player.pk)
        self.assertEqual(capabilities["systemId"], "gravewright-pdf-system")
        self.assertIn("pdf.read", {row["name"] for row in capabilities["operations"]})
        read = systems.call(self.campaign.pk, self.player.pk, "pdf.read", {"actorId": str(self.actor.pk)})
        self.assertEqual(read["data"]["fields"][SCORE], 10)
        issue(self.gm, self.campaign.pk)
        guest = StreamerLink.objects.latest("expires_at").guest
        with self.assertRaises(JournalError):
            systems.call(self.campaign.pk, guest.pk, "pdf.configure", {"actorId": str(self.actor.pk)}, uuid4())
        self.assertEqual(self.view()["sheetVersion"], 1)

    def test_generic_roll_uses_authoritative_scene_and_private_audience(self):
        from api import systems
        from api.errors import AuthError
        from gravewright.maps.models import Scene
        hidden = Scene.objects.create(campaign=self.campaign, name="Hidden", visibility="gm", width=500, height=500)
        with self.assertRaises(AuthError) as caught:
            systems.call(self.campaign.pk, self.player.pk, "pdf.roll",
                         {"actorId": str(self.actor.pk), "field": SCORE, "mapId": str(hidden.pk)}, uuid4())
        self.assertEqual(caught.exception.code, "invalid_scene")
        result = systems.call(self.campaign.pk, self.player.pk, "pdf.roll",
                              {"actorId": str(self.actor.pk), "field": SCORE, "visibility": "gm"}, uuid4(), scene_id=self.scene.pk)
        from gravewright.chat.models import Message
        message = Message.objects.get(pk=result["id"])
        self.assertEqual(message.scene_id, self.scene.pk)
        self.assertEqual(set(message.recipients.values_list("user_id", flat=True)), {self.gm.pk, self.player.pk})

    def test_generic_import_allows_escaped_json_envelope_but_keeps_file_size_limit(self):
        from api import systems
        from .models import MappingTemplate
        bundle = pdf_system.export_mapping(self.campaign.pk, self.gm.pk, self.actor.pk)
        raw = json.dumps(bundle) + "\n" * 600_000
        payload = {"name": "Escaped text", "bundle": raw}
        self.assertGreater(len(json.dumps(payload)), 1_100_000)
        imported = systems.call(self.campaign.pk, self.gm.pk, "pdf.templates.import", payload, uuid4())
        self.assertEqual(imported["bundle"], bundle)
        self.assertEqual(MappingTemplate.objects.count(), 1)
        with self.assertRaises(MapError) as caught:
            systems.call(self.campaign.pk, self.gm.pk, "pdf.templates.import", {"name": "Too large", "bundle": "{}" + "\n" * 1_000_000}, uuid4())
        self.assertEqual(str(caught.exception), "Use a mapping JSON file no larger than 1 MB.")
        self.assertEqual(MappingTemplate.objects.count(), 1)

    def test_registered_operations_use_stable_json_payloads_and_effect_metadata(self):
        operations = public.operations()
        self.assertEqual(set(operations), {"pdf.read", "pdf.configure", "pdf.exportMapping", "pdf.applyMapping", "pdf.diagnostics", "pdf.roll",
                                            "pdf.templates.list", "pdf.templates.read", "pdf.templates.create", "pdf.templates.update", "pdf.templates.delete",
                                            "pdf.templates.import", "pdf.templates.export", "pdf.templates.apply"})
        self.assertEqual(operations["pdf.read"]["effect"], "read")
        self.assertEqual(operations["pdf.configure"]["effect"], "write")
        read = operations["pdf.read"]["handler"](self.campaign.pk, self.player.pk, {"actorId": str(self.actor.pk)}, None)
        self.assertEqual(read["source"], SOURCE)
        response = operations["pdf.configure"]["handler"](self.campaign.pk, self.gm.pk,
                      {"actorId": str(self.actor.pk), "source": SOURCE, "version": read["version"], "sheetVersion": read["sheetVersion"], "changes": {"bindings": {}}}, uuid4())
        self.assertEqual(response["sheetVersion"], read["sheetVersion"] + 1)
