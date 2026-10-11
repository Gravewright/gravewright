"""Installed ruleset document types flow through native and SDK commands."""

import uuid
from copy import deepcopy
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.compendiums.models import Entry, Pack
from gravewright.items import services as items
from gravewright.journals.services import member
from gravewright.maps.services import MapError
from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.operations import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table import domain

from . import services
from .models import Actor


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class SystemDocumentTypeTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        media = override_settings(MEDIA_ROOT=temp.name)
        media.enable()
        self.addCleanup(media.disable)
        self.gm = User.objects.create_user(
            email="system-types@example.test", name="GM", password="password", role="owner"
        )
        self.campaign = Campaign.objects.create(
            owner=self.gm, name="Custom system", system="example.rules"
        )
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        self.definition = {
            "actorTypes": [
                {"id": "hero", "label": "Hero"},
                {"id": "creature", "label": "Creature"},
            ],
            "itemTypes": [{"id": "gear", "label": "Gear"}],
        }
        self.package = Package.objects.create(
            module_id="example.rules",
            version="1.0.0",
            digest="a" * 64,
            record={},
            manifest={
                "id": "example.rules",
                "version": "1.0.0",
                "name": "Example rules",
                "description": "System for document type tests",
                "author": "Example",
                "license": "MIT",
                "sdk": {"requires": ">=1.0.0 <2.0.0", "tested": "1.0.0"},
                "entry": "main.js",
                "system": self.definition,
            },
        )

    def create_actor(self, **payload):
        result = services.command(
            self.campaign.pk, self.gm.pk, "actor.create", {"name": "Test actor", **payload}, uuid.uuid4()
        )
        return Actor.objects.get(pk=result["id"])

    def test_native_creation_and_directory_use_declared_actor_types(self):
        actor = self.create_actor(actorType="creature")
        self.assertEqual(actor.type, "creature")
        self.assertEqual(self.create_actor().type, "hero")
        result = services.state(self.campaign.pk, self.gm.pk)
        self.assertEqual(result["actorTypes"], self.definition["actorTypes"])
        view = next(row for row in result["actors"] if row["id"] == str(actor.pk))
        self.assertEqual(view["actorType"], "creature")
        self.assertEqual(view["systemId"], "example.rules")
        with self.assertRaises(MapError):
            self.create_actor(type="character")

    def test_custom_sheet_data_round_trip_has_no_pdf_defaults(self):
        data = {'abilities': {'might': 4}, 'inventory': [{'name': 'Sword'}]}
        actor = self.create_actor(data=data)
        self.assertEqual(actor.data, data)
        view = services.sheet(self.campaign.pk, self.gm.pk, actor.pk)
        services.command(self.campaign.pk, self.gm.pk, 'sheet.save', {
            **view, 'actorId': str(actor.pk), 'data': {'abilities': {'might': 7}},
        }, uuid.uuid4())
        actor.refresh_from_db()
        self.assertEqual(actor.data, {'abilities': {'might': 7}})
        with self.assertRaises(MapError):
            services.command(self.campaign.pk, self.gm.pk, 'sheet.save', {
                **view, 'actorId': str(actor.pk),
            }, uuid.uuid4())

    def test_custom_sdk_data_update_uses_system_shape(self):
        actor = self.create_actor(data={'health': 12})
        request = SimpleNamespace(user=self.gm)
        view = invoke(request, self.campaign.pk, None, 'actor.data.read', {'id': str(actor.pk)})
        invoke(request, self.campaign.pk, None, 'actor.data.update', {
            'id': str(actor.pk), 'data': {'health': 9, 'skills': ['sneak']},
            'expectedRevision': view['revision'],
        })
        actor.refresh_from_db()
        self.assertEqual(actor.data, {'health': 9, 'skills': ['sneak']})

    def test_custom_data_is_bounded_json_and_effects_stay_protected(self):
        from gravewright.campaigns.systems import normalize_actor
        for data in ({'value': float('nan')}, {'nested': [{'__proto__': {}}]}, {'large': 'x' * 500_001}):
            with self.assertRaises(MapError):
                normalize_actor('example.rules', data)
        with self.assertRaises(MapError):
            normalize_actor('example.rules', {'effects': [{'label': 'New'}]}, {}, False)
        self.assertEqual(normalize_actor('example.rules', {}, {'effects': [{'label': 'Old'}]}, False), {'effects': [{'label': 'Old'}]})

    def test_custom_sheet_writes_keep_document_ownership_checks(self):
        player = User.objects.create_user(email='sheet-player@example.test', name='Player', password='password', role='participant')
        Membership.objects.create(campaign=self.campaign, user=player, role='player')
        actor = self.create_actor(data={'health': 12})
        actor.permissions = {'default': 'read'}
        actor.save(update_fields=['permissions'])
        view = services.sheet(self.campaign.pk, player.pk, actor.pk)
        payload = {**view, 'actorId': str(actor.pk), 'data': {'health': 8}}
        with self.assertRaises(MapError):
            services.command(self.campaign.pk, player.pk, 'sheet.save', payload, uuid.uuid4())
        actor.permissions[str(player.pk)] = 'owner'
        actor.save(update_fields=['permissions'])
        services.command(self.campaign.pk, player.pk, 'sheet.save', payload, uuid.uuid4())
        actor.refresh_from_db()
        self.assertEqual(actor.data, {'health': 8})

    def test_custom_tokens_place_duplicate_move_and_save_without_pdf_shape(self):
        from gravewright.maps.models import Scene
        from gravewright.tokens.models import Token
        from gravewright.tokens import services as tokens
        actor = self.create_actor(data={'health': 12})
        scene = Scene.objects.create(campaign=self.campaign, name='Custom scene', width=800, height=600)
        result = tokens.command(self.campaign.pk, self.gm.pk, 'place', {
            'mapId': str(scene.pk), 'actorId': str(actor.pk), 'gridX': 0, 'gridY': 0,
        }, uuid.uuid4())
        linked = Token.objects.get(pk=result['createdIds'][0])
        self.assertEqual(result['tokens'][0]['cells'], 1)
        result = tokens.command(self.campaign.pk, self.gm.pk, 'duplicate', {
            'mapId': str(scene.pk), 'tokenIds': [str(linked.pk)],
        }, uuid.uuid4())
        copy = Token.objects.get(pk=result['createdIds'][0])
        self.assertEqual(copy.snapshot, {'health': 12})
        view = services.sheet(self.campaign.pk, self.gm.pk, actor.pk, copy.pk)
        services.command(self.campaign.pk, self.gm.pk, 'sheet.save', {
            **view, 'actorId': str(actor.pk), 'data': {'health': 8},
        }, uuid.uuid4())
        copy.refresh_from_db(); actor.refresh_from_db()
        self.assertEqual(copy.snapshot, {'health': 8})
        self.assertEqual(actor.data, {'health': 12})
        tokens.command(self.campaign.pk, self.gm.pk, 'move', {
            'mapId': str(scene.pk), 'id': str(copy.pk), 'version': copy.version, 'gridX': 2, 'gridY': 2,
        }, uuid.uuid4())

    def test_custom_table_has_no_pdf_assets_or_template(self):
        self.client.force_login(self.gm)
        response = self.client.get('/game/' + str(self.campaign.pk))
        self.assertEqual(response.status_code, 200)
        self.assertNotRegex(response.content.decode(), r'(?:src|href)="[^"]*gravewright_pdf_system/')
        self.assertNotContains(response, 'pdf-sheet__tabs')
        self.assertContains(response, 'actor-sheet-window')

    def test_sdk_create_read_and_list_preserve_type(self):
        request = SimpleNamespace(user=self.gm)
        created = invoke(request, self.campaign.pk, None, "actor.create", {"name": "SDK creature", "type": "creature"})
        read = invoke(request, self.campaign.pk, None, "actor.read", {"id": created["id"]})
        listed = invoke(request, self.campaign.pk, None, "actor.list", {})["items"]
        for view in (created, read, listed[0]):
            self.assertEqual(view["type"], "creature")
            self.assertEqual(view["systemId"], "example.rules")
        with self.assertRaises(ModuleFailure) as error:
            invoke(request, self.campaign.pk, None, "actor.create", {"name": "Invalid", "type": "character"})
        self.assertEqual(error.exception.code, "invalid_data")

    def test_items_use_declared_types_and_reject_other_types(self):
        result = domain.command(
            self.campaign.pk, self.gm.pk, "items", "create", {"name": "Sword", "type": "gear"}, uuid.uuid4()
        )
        self.assertEqual(result["item"]["type"], "gear")
        self.assertEqual(result["item"]["systemId"], "example.rules")
        self.assertEqual(items.state(member(self.campaign.pk, self.gm.pk))["types"], self.definition["itemTypes"])
        with self.assertRaises(MapError):
            domain.command(self.campaign.pk, self.gm.pk, "items", "create", {"name": "Invalid", "type": "spell"}, uuid.uuid4())

    def test_pinned_system_release_controls_actor_and_item_types(self):
        manifest = deepcopy(self.package.manifest)
        manifest.update(
            version="2.0.0",
            system={
                "actorTypes": [{"id": "adventurer", "label": "Adventurer"}],
                "itemTypes": [{"id": "spell", "label": "Spell"}],
            },
        )
        Package.objects.create(module_id=self.package.module_id, version="2.0.0", digest="b" * 64, manifest=manifest, record={})
        ModuleSet.objects.create(campaign=self.campaign, modules={"example.rules": "1.0.0"})
        request = SimpleNamespace(user=self.gm)
        created = invoke(request, self.campaign.pk, None, "actor.create", {"name": "Pinned creature", "type": "creature"})
        self.assertEqual(created["type"], "creature")
        with self.assertRaises(ModuleFailure) as error:
            invoke(request, self.campaign.pk, None, "actor.create", {"name": "Wrong release", "type": "adventurer"})
        self.assertEqual(error.exception.code, "invalid_data")
        self.assertEqual(services.state(self.campaign.pk, self.gm.pk)["actorTypes"], self.definition["actorTypes"])
        item = domain.command(self.campaign.pk, self.gm.pk, "items", "create", {"name": "Pinned sword", "type": "gear"}, uuid.uuid4())["item"]
        self.assertEqual(item["type"], "gear")
        self.assertEqual(items.state(member(self.campaign.pk, self.gm.pk))["types"], self.definition["itemTypes"])
        with self.assertRaises(MapError):
            domain.command(self.campaign.pk, self.gm.pk, "items", "create", {"name": "Wrong release", "type": "spell"}, uuid.uuid4())
        self.package.revoked = True
        self.package.save(update_fields=["revoked"])
        self.assertEqual(services.types("example.rules", campaign_id=self.campaign.pk), [])
        with self.assertRaises(MapError):
            self.create_actor(type="adventurer")

    def test_native_system_and_legacy_campaign_default_to_character(self):
        for system_id in ("gravewright-pdf-system", ""):
            self.campaign.system = system_id
            self.campaign.save(update_fields=["system"])
            actor = self.create_actor()
            self.assertEqual(actor.type, "character")
            view = services.sheet(self.campaign.pk, self.gm.pk, actor.pk)
            self.assertEqual(view["systemId"], "gravewright-pdf-system")
            self.assertEqual(items.types(system_id), [])

    def test_unavailable_system_keeps_existing_actor_readable(self):
        actor = self.create_actor(type="creature")
        self.package.revoked = True
        self.package.save(update_fields=["revoked"])
        view = services.sheet(self.campaign.pk, self.gm.pk, actor.pk)
        self.assertEqual(view["actorType"], "creature")
        self.assertEqual(view["systemId"], "example.rules")
        self.assertEqual(services.types("example.rules"), [])
        with self.assertRaises(MapError):
            self.create_actor(type="creature")

    def test_compendium_round_trip_and_legacy_copy_preserve_type(self):
        actor = self.create_actor(type="creature")
        pack = Pack.objects.create(campaign=self.campaign, name="Creatures", system_id=self.campaign.system)
        added = domain.command(
            self.campaign.pk, self.gm.pk, "compendiums", "add", {"packId": str(pack.pk), "kind": "actor", "resourceId": str(actor.pk)}, uuid.uuid4()
        )
        entry = Entry.objects.get(pk=added["id"])
        self.assertEqual(entry.data["type"], "creature")
        for bundled in (True, False):
            if not bundled:
                entry.bundle = ""
                entry.save(update_fields=["bundle"])
                self.package.revoked = True
                self.package.save(update_fields=["revoked"])
            copied = domain.command(
                self.campaign.pk, self.gm.pk, "compendiums", "import", {"packId": str(pack.pk), "id": str(entry.pk)}, uuid.uuid4()
            )
            self.assertEqual(Actor.objects.get(pk=copied["id"]).type, "creature")
