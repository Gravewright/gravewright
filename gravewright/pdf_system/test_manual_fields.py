"""Persistence and permission boundaries for GM-authored PDF overlays."""

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from gravewright.maps.services import MapError

from .schema import normalize


def definition(**changes):
    return {
        "id": str(uuid4()), "source": "template:generic", "page": 1,
        "type": "text", "name": "Character name", "x": 0.1, "y": 0.2,
        "width": 0.5, "height": 0.08, **changes,
    }


def value_key(field):
    return "manual_" + field["id"].replace("-", "")


class ManualFieldSchemaTests(SimpleTestCase):
    def test_existing_sheets_keep_their_shape_without_a_manual_layout(self):
        clean = normalize({"fields": {"manual_existing_pdf_field": "Written"}})
        self.assertNotIn("manualFields", clean["pdf"])
        self.assertEqual(clean["fields"]["manual_existing_pdf_field"], "Written")

    def test_all_field_types_round_trip_with_source_and_page_binding(self):
        sources = ("template:generic", "asset:" + str(uuid4()))
        fields = [definition(type=kind, source=sources[i % 2], page=i + 1)
                  for i, kind in enumerate(("text", "number", "checkbox", "multiline"))]
        values = dict(zip(map(value_key, fields), ("Hero", 12.5, True, "Long\nnotes")))
        raw = {"pdf": {"manualFields": fields}, "fields": values}
        before = deepcopy(raw)
        clean = normalize(raw)
        self.assertEqual(clean["pdf"]["manualFields"], fields)
        self.assertEqual(clean["fields"], values)
        self.assertEqual(raw, before)

    def test_gm_can_move_and_remove_fields_without_deleting_values(self):
        field = definition()
        data = normalize({"pdf": {"manualFields": [field]},
                          "fields": {value_key(field): "Retained"}})
        moved = deepcopy(data)
        moved["pdf"]["manualFields"][0].update(x=0.25, width=0.3, page=2)
        saved = normalize(moved, data)
        self.assertEqual(saved["pdf"]["manualFields"][0]["page"], 2)
        saved["pdf"]["manualFields"] = []
        self.assertEqual(normalize(saved, moved)["fields"][value_key(field)], "Retained")

    def test_omitted_layout_is_preserved_for_both_gm_and_player_partial_saves(self):
        field = definition()
        previous = normalize({"pdf": {"manualFields": [field]}})
        for gm in (True, False):
            with self.subTest(gm=gm):
                clean = normalize({"pdf": {"template": "another"}}, previous, gm)
                self.assertEqual(clean["pdf"]["manualFields"], [field])
                self.assertEqual(clean["pdf"]["manualFields"][0]["source"], "template:generic")
                self.assertIsNot(clean["pdf"]["manualFields"], previous["pdf"]["manualFields"])

    def test_player_can_fill_an_unchanged_layout_and_select_another_pdf(self):
        field = definition(type="checkbox")
        previous = normalize({"pdf": {"manualFields": [field]}})
        changed = deepcopy(previous)
        changed["pdf"]["asset"] = str(uuid4())
        changed["fields"][value_key(field)] = True
        clean = normalize(changed, previous, gm=False)
        self.assertTrue(clean["fields"][value_key(field)])
        self.assertEqual(clean["pdf"]["manualFields"], [field])

    def test_player_cannot_create_remove_or_change_any_definition(self):
        field = definition()
        previous = normalize({"pdf": {"manualFields": [field]}})
        mutations = {"id": str(uuid4()), "source": "template:another", "page": 2,
                     "type": "number", "name": "Changed", "x": 0.15, "y": 0.3,
                     "width": 0.4, "height": 0.1}
        layouts = [[], [field, definition()]]
        layouts.extend([{**field, key: value}] for key, value in mutations.items())
        for layout in layouts:
            with self.subTest(layout=layout), self.assertRaises(MapError) as caught:
                normalize({"pdf": {"manualFields": layout}}, previous, gm=False)
            self.assertEqual(caught.exception.code, "forbidden")
        with self.assertRaises(MapError):
            normalize({"pdf": {"manualFields": [field]}}, gm=False)

    def test_layout_count_and_exact_record_shape_are_bounded(self):
        self.assertEqual(len(normalize({"pdf": {"manualFields":
                                              [definition() for _ in range(256)]}})
                             ["pdf"]["manualFields"]), 256)
        for layout in (None, {}, "fields", True, [definition() for _ in range(257)],
                       [None], [{**definition(), "extra": "unexpected"}],
                       [{key: value for key, value in definition().items() if key != "x"}]):
            with self.subTest(layout_type=type(layout)), self.assertRaises(MapError):
                normalize({"pdf": {"manualFields": layout}})

    def test_identifiers_are_canonical_and_equivalent_duplicates_are_rejected(self):
        field = definition()
        upper = {**field, "id": field["id"].upper()}
        self.assertEqual(normalize({"pdf": {"manualFields": [upper]}})
                         ["pdf"]["manualFields"], [field])
        for layout in ([field, upper], [{**field, "id": "not-a-uuid"}],
                       [{**field, "id": None}]):
            with self.subTest(layout=layout), self.assertRaises(MapError):
                normalize({"pdf": {"manualFields": layout}})

    def test_sources_names_types_and_pages_reject_invalid_input(self):
        invalid = {
            "source": [None, "generic", "asset:bad", "asset:", "template:",
                       "template:../private", "template:" + "a" * 121],
            "page": [False, 0, -1, 1.5, "1", 100001],
            "type": [[], None, "button", "boolean"],
            "name": [None, "", "  \n", "a" * 121],
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(MapError):
                    normalize({"pdf": {"manualFields": [definition(**{key: value})]}})

    def test_geometry_is_finite_nonempty_and_contained_inside_the_page(self):
        for key, values in {"x": [-0.01, True, 1, "0.1", float("nan")],
                            "y": [-1, 1, float("inf")],
                            "width": [0, 0.0009, 1, float("-inf")],
                            "height": [-0.1, 0, 1, None]}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(MapError):
                    normalize({"pdf": {"manualFields": [definition(**{key: value})]}})
        boundary = definition(x=0, y=0.999, width=1, height=0.001)
        self.assertEqual(normalize({"pdf": {"manualFields": [boundary]}})
                         ["pdf"]["manualFields"], [boundary])

    def test_known_field_values_are_validated_by_the_authored_type(self):
        for kind, values in {"text": [False, 1, {}, None, "a" * 20001],
                             "multiline": [["line"], True],
                             "number": [True, "12", None, 1000001, float("nan")],
                             "checkbox": [0, 1, "true", None]}.items():
            field = definition(type=kind)
            for value in values:
                with self.subTest(kind=kind, value_type=type(value)), self.assertRaises(MapError):
                    normalize({"pdf": {"manualFields": [field]},
                               "fields": {value_key(field): value}})

    def test_archived_values_and_native_pdf_field_names_are_preserved(self):
        field = definition()
        values = {"manual_old_field": "Native PDF", value_key(field): "Archived"}
        self.assertEqual(normalize({"fields": values})["fields"], values)
        self.assertEqual(normalize({"pdf": {"manualFields": []}, "fields": values})
                         ["fields"], values)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ManualFieldPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from gravewright.accounts.models import User
        from gravewright.actors.models import Actor
        from gravewright.campaigns.models import Campaign, Membership, StreamerLink
        from gravewright.maps.models import Broadcast, Scene
        from gravewright.tokens.models import Token

        cls.gm = User.objects.create(email="pdf-gm@example.test", name="GM", role="owner")
        cls.player = User.objects.create(email="pdf-player@example.test", name="Player")
        cls.streamer = User.objects.create(email="pdf-streamer@example.test", name="Streamer")
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="PDF mapping")
        for user, role in ((cls.gm, "gm"), (cls.player, "player"), (cls.streamer, "streamer")):
            Membership.objects.create(campaign=cls.campaign, user=user, role=role)
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer,
                                    digest="pdf-test-stream", expires_at=timezone.now() + timedelta(hours=1))
        cls.field = definition()
        cls.actor = Actor.objects.create(
            campaign=cls.campaign, name="Mapped hero",
            data=normalize({"pdf": {"manualFields": [cls.field]}}),
            permissions={str(cls.player.pk): "owner", str(cls.streamer.pk): "owner"},
        )
        cls.scene = Scene.objects.create(campaign=cls.campaign, name="Map", width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)
        cls.token = Token.objects.create(scene=cls.scene, actor=cls.actor, linked=False,
                                         snapshot=deepcopy(cls.actor.data))

    def view(self, user, *, snapshot=False):
        from gravewright.actors.services import sheet
        return sheet(self.campaign.pk, user.pk, self.actor.pk,
                     self.token.pk if snapshot else None)

    def save(self, user, view, *, request_id=None):
        from gravewright.actors.services import command
        return command(self.campaign.pk, user.pk, "sheet.save",
                       {**view, "actorId": str(self.actor.pk)}, request_id or uuid4())

    def test_gm_layout_and_player_values_persist_for_actor_and_independent_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                view = self.view(self.gm, snapshot=snapshot)
                view["data"]["pdf"]["manualFields"][0]["name"] = "Mapped name"
                self.save(self.gm, view)
                player = self.view(self.player, snapshot=snapshot)
                player["data"]["fields"][value_key(self.field)] = "Player input"
                self.save(self.player, player)
                saved = self.view(self.gm, snapshot=snapshot)["data"]
                self.assertEqual(saved["pdf"]["manualFields"][0]["name"], "Mapped name")
                self.assertEqual(saved["fields"][value_key(self.field)], "Player input")

    def test_player_layout_rejections_are_atomic_for_actor_and_snapshot(self):
        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                view = self.view(self.player, snapshot=snapshot)
                view["data"]["pdf"]["manualFields"] = []
                view["data"]["fields"][value_key(self.field)] = "Must roll back"
                with self.assertRaises(MapError) as caught:
                    self.save(self.player, view)
                self.assertEqual(caught.exception.code, "forbidden")
                saved = self.view(self.gm, snapshot=snapshot)["data"]
                self.assertEqual(saved["pdf"]["manualFields"], [self.field])
                self.assertEqual(saved["fields"], {})

    def test_player_legacy_save_retains_layout_and_stale_save_cannot_replace_it(self):
        view = self.view(self.player)
        stale = deepcopy(view)
        del view["data"]["pdf"]["manualFields"]
        view["data"]["fields"][value_key(self.field)] = "Saved"
        request_id = uuid4()
        first = self.save(self.player, view, request_id=request_id)
        self.assertEqual(self.save(self.player, view, request_id=request_id), first)
        self.assertEqual(self.view(self.gm)["data"]["pdf"]["manualFields"], [self.field])
        with self.assertRaises(MapError) as caught:
            self.save(self.player, stale)
        self.assertEqual(caught.exception.code, "conflict")

    def test_streamer_cannot_fill_or_remap_even_with_actor_owner_permission(self):
        from gravewright.journals.services import JournalError

        for snapshot in (False, True):
            with self.subTest(snapshot=snapshot):
                view = self.view(self.streamer, snapshot=snapshot)
                self.assertFalse(view["canEdit"])
                view["data"]["fields"][value_key(self.field)] = "Denied"
                with self.assertRaises(JournalError):
                    self.save(self.streamer, view)
