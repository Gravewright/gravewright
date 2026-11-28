"""Compendium modules supply verified packs with or without a required system."""

import io
import json
import uuid
import zipfile
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.items.models import Item
from gravewright.journals.models import Journal
from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.packages import ModuleFailure, host
from gravewright.table import domain
from . import catalog


SYSTEM = "example.rules"
BOOK = "example.book"
LORE = "example.lore"
SDK = {"requires": ">=1.0.0 <2.0.0", "tested": "1.0.0"}


def archive(manifest, files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("manifest.json", json.dumps(manifest))
        for name, value in files.items():
            package.writestr(name, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return output.getvalue()


def journal_pack(label="Chapters"):
    return {"id": "chapters", "label": label, "type": "journal_pack", "entries": [
        {"id": "prologue", "name": "Prologue", "content": "The road ends at a ruined gate."},
        {"id": "quest", "name": "Find the gate", "type": "quest", "data": {}},
    ]}


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class CompendiumModuleTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="gravewright-compendium-modules-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(override_settings(
            MEDIA_ROOT=self.root / "media", GRAVEWRIGHT_MODULES_ROOT=self.root / "modules",
            GRAVEWRIGHT_CONTENT_ROOT=self.root / "legacy-content", GRAVEWRIGHT_MARKETPLACE_KEYS_FILE="",
        ))
        catalog._collection_cache.clear()
        self.addCleanup(catalog._collection_cache.clear)
        self.gm = User.objects.create_user(email="book-gm@example.test", name="GM", password="password", role="owner")
        self.player = User.objects.create_user(email="book-player@example.test", name="Player", password="password")
        self.campaign = self.table("Book table", SYSTEM)
        self.install_system("1.0.0")
        self.install_system("2.0.0")
        self.configure({SYSTEM: "1.0.0"})

    def table(self, name, system):
        campaign = Campaign.objects.create(owner=self.gm, name=name, system=system)
        Membership.objects.create(campaign=campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=campaign, user=self.player, role="player")
        return campaign

    def install_system(self, version):
        manifest = {
            "id": SYSTEM, "version": version, "name": "Example rules", "description": "Test system",
            "author": "Tests", "license": "MIT", "entry": "main.js", "sdk": SDK,
            "system": {"actorTypes": [{"id": "creature", "label": "Creature"}],
                       "itemTypes": [{"id": "gear", "label": "Gear"}, {"id": "spell", "label": "Spell"}]},
            "content": {"compendiums": ["rules.json"]},
        }
        rules = {"name": "Rules", "packs": [{"id": "gear", "label": "Gear", "type": "item_pack", "entries": [
            {"id": "rope", "name": "Rope", "type": "gear", "systemId": SYSTEM, "data": {"weight": 1}}]}]}
        host().install_local(archive(manifest, {"main.js": "export default {start(){},register(){},stop(){}}",
                                                "rules.json": rules}), expected_type="system")

    def book_manifest(self, version="1.0.0", **content):
        return {
            "id": BOOK, "version": version, "name": "Purchased book", "description": "Private compendium",
            "author": "Owner", "license": "Private", "sdk": SDK,
            "content": {"compendiums": ["book.json"],
                        "requiresSystem": {"id": SYSTEM, "version": ">=1.0.0 <2.0.0"}, **content},
        }

    def book(self, creature_type="creature", marker="original"):
        return {"name": "Purchased book", "folder": ["Books", "Purchased"], "packs": [
            {"id": "bestiary", "label": "Bestiary", "type": "actor_pack", "entries": [
                {"id": "gate-warden", "name": "Gate warden", "type": creature_type, "systemId": SYSTEM,
                 "data": {"marker": marker, "hp": 22}}]},
            {"id": "spells", "label": "Spells", "type": "spell_pack", "entries": [
                {"id": "ward", "name": "Ward", "type": "spell", "systemId": SYSTEM, "data": {"level": 1}}]},
            journal_pack(),
        ]}

    def install_book(self, version="1.0.0", manifest=None, collection=None):
        host().install_local(archive(manifest or self.book_manifest(version), {"book.json": collection or self.book()}),
                             expected_type="module")
        return Package.objects.get(module_id=BOOK, version=version)

    def install_lore(self, collection=None, version="1.0.0"):
        manifest = {"id": LORE, "version": version, "name": "Lore", "description": "Setting notes",
                    "author": "Owner", "license": "Private", "sdk": SDK,
                    "content": {"compendiums": ["lore.json"]}}
        host().install_local(archive(manifest, {"lore.json": collection or {"name": "Lore", "packs": [journal_pack()]}}),
                             expected_type="module")
        return Package.objects.get(module_id=LORE, version=version)

    def configure(self, modules, campaign=None):
        campaign = campaign or self.campaign
        current = ModuleSet.objects.filter(campaign=campaign).first()
        return host().configure(campaign.pk, modules, {}, current.revision if current else "0")

    def packs(self, user=None, campaign=None):
        campaign = campaign or self.campaign
        return domain.state(campaign.pk, (user or self.gm).pk, "compendiums")["packs"]

    def pack(self, label, user=None, campaign=None):
        return next(pack for pack in self.packs(user, campaign) if pack["name"].endswith(" / " + label))

    def command(self, action, payload, user=None, campaign=None):
        campaign = campaign or self.campaign
        return domain.command(campaign.pk, (user or self.gm).pk, "compendiums", action, payload, uuid.uuid4())

    def test_module_without_system_supplies_journal_packs_to_any_table(self):
        package = self.install_lore()
        self.assertEqual(package.record["type"], "module")
        other = self.table("Other rules", "another.rules")
        state = self.configure({LORE: "1.0.0"}, other)
        self.assertEqual(state["modules"], [{"id": LORE, "version": "1.0.0",
                                             "baseUrl": f"/api/module-packages/{LORE}/1.0.0/{package.digest}/"}])
        with self.assertRaises(ModuleFailure) as stale:
            host().check(other.pk, LORE, state["moduleSetRevision"])
        self.assertEqual(stale.exception.code, "stale_context")

        pack = self.pack("Chapters", campaign=other)
        self.assertEqual([entry["kind"] for entry in pack["entries"]], ["journal", "journal"])
        self.assertNotIn(pack["id"], [row["id"] for row in self.packs(self.player, other)],
                         "Journal packs can hold spoilers and stay hidden from players by default.")
        imported = self.command("import", {"packId": pack["id"], "id": "prologue"}, campaign=other)
        journal = Journal.objects.get(pk=imported["id"])
        self.assertEqual((journal.title, journal.folder.name, journal.folder.parent.name), ("Prologue", "Chapters", "Lore"))
        self.assertIn("ruined gate", json.dumps(journal.data))
        quest = Journal.objects.get(pk=self.command("import", {"packId": pack["id"], "id": "quest"}, campaign=other)["id"])
        self.assertEqual(quest.type, "quest")

        self.configure({}, other)
        self.assertEqual(self.packs(campaign=other), [])

    def test_module_without_system_cannot_supply_actor_or_item_packs(self):
        collection = {"name": "Lore", "packs": [{"id": "gear", "label": "Gear", "type": "item_pack", "entries": [
            {"id": "rope", "name": "Rope", "type": "gear", "systemId": SYSTEM, "data": {}}]}]}
        with self.assertRaises(ModuleFailure) as rejected:
            self.install_lore(collection)
        self.assertIn("require a system", rejected.exception.message)
        self.assertFalse(Package.objects.filter(module_id=LORE).exists())

    def test_required_system_gates_activation_and_supplies_its_document_types(self):
        self.install_book()
        other = self.table("Other rules", "another.rules")
        with self.assertRaises(ModuleFailure) as wrong_system:
            self.configure({BOOK: "1.0.0"}, other)
        self.assertEqual(wrong_system.exception.code, "system_required")
        self.assertIn(f"requires a table using the system {SYSTEM}", wrong_system.exception.message)
        same_system = self.table("No active release", SYSTEM)
        with self.assertRaises(ModuleFailure) as inactive:
            self.configure({BOOK: "1.0.0"}, same_system)
        self.assertIn(">=1.0.0 <2.0.0 active in this table", inactive.exception.message)

        self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0"})
        bestiary = self.pack("Bestiary")
        self.assertEqual(bestiary["folder"], ["Books", "Purchased"])
        self.assertEqual(bestiary["entries"][0]["type"], "creature")
        actor = Actor.objects.get(pk=self.command("import", {"packId": bestiary["id"], "id": "gate-warden"})["id"])
        self.assertEqual((actor.type, actor.data["hp"]), ("creature", 22))
        item = Item.objects.get(pk=self.command("import", {"packId": self.pack("Spells")["id"], "id": "ward"})["id"])
        self.assertEqual((item.type, item.system_id), ("spell", SYSTEM))
        self.assertIn(self.pack("Spells")["id"], [row["id"] for row in self.packs(self.player)],
                      "Spell packs keep the native player-readable default.")
        self.assertTrue(self.pack("Gear"), "The system's own packs remain available.")

    def test_system_release_outside_the_range_hides_only_the_module_packs(self):
        self.install_book()
        self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0"})
        with self.assertLogs("gravewright.compendiums.catalog", "WARNING") as logs:
            self.configure({SYSTEM: "2.0.0", BOOK: "1.0.0"})
            names = [pack["name"] for pack in self.packs()]
        self.assertEqual(names, ["Rules / Gear"])
        self.assertIn(f"required system {SYSTEM} >=1.0.0 <2.0.0", logs.output[0])
        self.configure({SYSTEM: "2.0.0"})
        with self.assertRaises(ModuleFailure) as rejected:
            self.configure({SYSTEM: "2.0.0", BOOK: "1.0.0"})
        self.assertIn("requires the system", rejected.exception.message)

    def test_activation_checks_entries_against_the_active_system_types(self):
        self.install_book(collection=self.book(creature_type="vehicle"))
        with self.assertRaises(ModuleFailure) as rejected:
            self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0"})
        self.assertEqual(rejected.exception.code, "incompatible_content")
        self.assertIn("book.json: Unregistered compendium document type", rejected.exception.message)
        self.assertNotIn(BOOK, ModuleSet.objects.get(campaign=self.campaign).modules)

    def test_pack_identity_survives_module_updates_and_one_broken_module_hides_nothing_else(self):
        self.install_book()
        self.install_lore()
        self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0", LORE: "1.0.0"})
        bestiary = self.pack("Bestiary")["id"]
        self.assertNotEqual(bestiary, self.pack("Chapters")["id"])
        self.install_book("1.1.0", collection=self.book(marker="revised"))
        self.configure({SYSTEM: "1.0.0", BOOK: "1.1.0", LORE: "1.0.0"})
        self.assertEqual(self.pack("Bestiary")["id"], bestiary)
        read = self.command("read", {"packId": bestiary, "id": "gate-warden"})
        self.assertEqual(read["data"]["marker"], "revised")

        revised = Package.objects.get(module_id=BOOK, version="1.1.0")
        path = self.root / "modules/packages" / BOOK / "1.1.0" / revised.digest / "book.json"
        path.write_text(path.read_text(encoding="utf-8").replace("revised", "tampered"), encoding="utf-8")
        catalog._collection_cache.clear()
        with self.assertLogs("gravewright.compendiums.catalog", "WARNING"):
            names = sorted(pack["name"] for pack in self.packs())
        self.assertEqual(names, ["Lore / Chapters", "Rules / Gear"])
        with self.assertRaises(domain.MapError):
            self.command("read", {"packId": bestiary, "id": "gate-warden"})

    def test_manifest_boundaries_for_compendium_modules(self):
        def rejected(manifest, files=None):
            with self.assertRaises(ModuleFailure) as failure:
                host().install_local(archive(manifest, files or {"book.json": self.book()}), expected_type="module")
            return failure.exception

        manifest = self.book_manifest()
        manifest["content"]["requiresSystem"]["version"] = "^1.0.0"
        self.assertIn("Invalid required system", rejected(manifest).message)
        manifest = self.book_manifest()
        manifest["content"]["requiresSystem"]["id"] = BOOK
        self.assertIn("Invalid required system", rejected(manifest).message)
        manifest = self.book_manifest()
        manifest["locales"] = {"pt-BR": {"name": "Português", "path": "pt.json"}}
        self.assertEqual(rejected(manifest, {"book.json": self.book(), "pt.json": {}}).code, "invalid_data")
        manifest = deepcopy(self.book_manifest())
        manifest.update(entry="main.js", system={"actorTypes": [{"id": "creature", "label": "Creature"}]})
        with self.assertRaises(ModuleFailure):
            host().install_local(archive(manifest, {"book.json": self.book(), "main.js": ""}), expected_type="system")
        journal = self.book()
        journal["packs"][2]["entries"][0]["systemId"] = SYSTEM
        self.assertIn("belong to no system", rejected(self.book_manifest(), {"book.json": journal}).message)
        self.assertFalse(Package.objects.filter(module_id=BOOK).exists())

        # A module may also ship browser code beside its compendiums.
        manifest = self.book_manifest()
        manifest["entry"] = "main.js"
        host().install_local(archive(manifest, {"book.json": self.book(), "main.js": "export default {}"}),
                             expected_type="module")
        self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0"})
        self.assertEqual([row.get("entry") for row in host().state(self.campaign.pk)["modules"]], ["main.js", "main.js"])

    def test_collections_are_read_only_through_table_grants(self):
        package = self.install_book()
        self.configure({SYSTEM: "1.0.0", BOOK: "1.0.0"})
        self.client.force_login(self.gm)
        response = self.client.get(f"/api/module-packages/{BOOK}/1.0.0/{package.digest}/book.json")
        self.assertEqual(response.status_code, 404)
        bestiary = self.pack("Bestiary")["id"]
        with self.assertRaises(domain.MapError) as denied:
            self.command("read", {"packId": bestiary, "id": "gate-warden"}, user=self.player)
        self.assertEqual(denied.exception.code, "not_found")
        with self.assertRaises(domain.MapError):
            self.command("import", {"packId": self.pack("Spells")["id"], "id": "ward"}, user=self.player)
