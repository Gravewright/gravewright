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
