"""Installed compendiums use pinned, verified packages and native permissions."""

import io
import json
import uuid
import zipfile
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.items.models import Item
from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.packages import ModuleFailure, host
from gravewright.table import domain
from gravewright.table.models import DocumentAccess


SYSTEM = "example.srd"
ITEM_TYPES = ("weapon", "armor", "equipment", "consumable", "spell", "feat", "feature", "race", "background", "class", "effect")


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class InstalledCompendiumTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.enterContext(override_settings(
            MEDIA_ROOT=self.directory / "media",
            GRAVEWRIGHT_MODULES_ROOT=self.directory / "modules",
            GRAVEWRIGHT_CONTENT_ROOT=self.directory / "legacy-content",
            GRAVEWRIGHT_MARKETPLACE_KEYS_FILE="",
        ))
        self.gm = User.objects.create_user(email="srd-gm@example.test", name="GM", password="password", role="owner")
        self.player = User.objects.create_user(email="srd-player@example.test", name="Player", password="password")
        self.streamer = User.objects.create_user(email="srd-streamer@example.test", name="Streamer", password="password")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Installed SRD", system=SYSTEM)
        for user, role in ((self.gm, "gm"), (self.player, "player"), (self.streamer, "streamer")):
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="a" * 64, expires_at=timezone.now() + timedelta(hours=1))
        self.manifest = {
            "id": SYSTEM, "version": "0.1.0", "name": "Example SRD", "description": "Test-only SRD collections",
            "author": "Gravewright tests", "license": "MIT", "entry": "main.js",
            "sdk": {"requires": ">=1.0.0 <2.0.0", "tested": "1.0.0"},
            "system": {"actorTypes": [{"id": "character", "label": "Character"}],
                       "itemTypes": [{"id": kind, "label": kind.title()} for kind in ITEM_TYPES]},
            "content": {"compendiums": ["compendiums/2014.json", "compendiums/2024.json"]},
        }
        self.package = self.install()
        host().configure(self.campaign.pk, {SYSTEM: "0.1.0"}, {}, "0")

    def entry_id(self, edition, kind):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"test-srd/{edition}/{kind}"))

    def collection(self, edition, revision="original"):
        return {"name": f"SRD · {edition}", "packs": [
            {"id": f"items-{edition}", "label": "Itens", "type": "item_pack", "entries": [
                {"id": self.entry_id(edition, kind), "name": f"{kind.title()} {edition}", "type": kind,
                 "systemId": SYSTEM, "data": {"rulesEdition": edition, "description": f"Descrição {revision} · {kind}", "nested": {"kept": True}}}
                for kind in ITEM_TYPES if kind != "spell"
            ]},
            {"id": f"spells-{edition}", "label": "Magias", "type": "spell_pack", "entries": [
                {"id": self.entry_id(edition, "spell"), "name": f"Luz {edition}", "type": "spell", "systemId": SYSTEM,
                 "data": {"rulesEdition": edition, "level": 0, "school": "evocation", "description": f"Descrição {revision} · spell"}}
            ]},
        ]}

    def install(self, version="0.1.0", revision="original", collections=None, content_path=None):
        manifest = deepcopy(self.manifest)
        manifest["version"] = version
        if content_path is not None:
            manifest["content"]["compendiums"] = [content_path]
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("main.js", "export default {start(){},stop(){}}")
            for edition in ("2014", "2024"):
                value = (collections or {}).get(edition, self.collection(edition, revision))
                archive.writestr(f"compendiums/{edition}.json", json.dumps(value, ensure_ascii=False))
        host().install_local(output.getvalue(), expected_type="system")
        return Package.objects.get(module_id=SYSTEM, version=version)

    def state(self, user=None):
        return domain.state(self.campaign.pk, (user or self.gm).pk, "compendiums")

    def command(self, action, payload, user=None, request_id=None):
        return domain.command(self.campaign.pk, (user or self.gm).pk, "compendiums", action, payload, request_id or uuid.uuid4())

    def pack(self, edition="2014", spells=False, user=None):
        suffix = " / Magias" if spells else " / Itens"
        return next(pack for pack in self.state(user)["packs"] if edition in pack["name"] and pack["name"].endswith(suffix))

    def package_root(self):
        return self.directory / "modules/packages" / SYSTEM / self.package.version / self.package.digest

    def test_only_active_pinned_release_supplies_collections(self):
        packs = self.state()["packs"]
        self.assertEqual(len(packs), 4)
        self.assertTrue(all(pack["id"].startswith("native:") and pack["locked"] for pack in packs))
        self.assertTrue(all(pack["systemId"] == SYSTEM for pack in packs))
        first = self.pack()
        self.install("0.2.0", revision="newer")
        payload = {"packId": first["id"], "id": self.entry_id("2014", "weapon")}
        self.assertIn("original", self.command("read", payload)["data"]["description"])
        selected = ModuleSet.objects.get(campaign=self.campaign)
        host().configure(self.campaign.pk, {SYSTEM: "0.2.0"}, {}, selected.revision)
        self.assertEqual(self.pack()["id"], first["id"], "Read grants must survive a release upgrade.")
        self.assertIn("newer", self.command("read", payload)["data"]["description"])
        ModuleSet.objects.filter(campaign=self.campaign).delete()
        self.assertEqual(self.state()["packs"], [])

    def test_other_system_and_revoked_package_are_hidden(self):
        self.campaign.system = "another.rules"
        self.campaign.save(update_fields=["system"])
        self.assertEqual(self.state()["packs"], [])
        self.campaign.system = SYSTEM
        self.campaign.save(update_fields=["system"])
        self.package.revoked = True
        self.package.save(update_fields=["revoked"])
        self.assertEqual(self.state()["packs"], [])

    def test_default_private_read_grants_and_explicit_denial(self):
        pack = self.pack()
        payload = {"packId": pack["id"], "id": self.entry_id("2014", "weapon")}
        self.assertEqual(self.state(self.player)["packs"], [])
        self.assertEqual(self.state(self.streamer)["packs"], [])
        with self.assertRaises(domain.MapError):
            self.command("read", payload, self.player)
        access = DocumentAccess.objects.create(campaign=self.campaign, kind="compendiums", resource_id=pack["id"], grants={"default": "read", "streamer": "none"})
        self.assertEqual(len(self.state(self.player)["packs"]), 1)
        self.assertEqual(self.state(self.streamer)["packs"], [])
        self.assertEqual(self.command("read", payload, self.player)["type"], "weapon")
        access.grants = {"default": "none", "player": "read", "streamer": "read"}
        access.save(update_fields=["grants"])
        self.assertEqual(len(self.state(self.player)["packs"]), 1)
        self.assertEqual(len(self.state(self.streamer)["packs"]), 1)
        access.grants = {"default": "read", "player": "none"}
        access.save(update_fields=["grants"])
        self.assertEqual(self.state(self.player)["packs"], [])

    def test_permission_command_allows_read_but_never_player_import(self):
        pack = self.pack()
        self.command("permissions", {"packId": pack["id"], "level": "read"})
        self.assertEqual(len(self.state(self.player)["packs"]), 1)
        payload = {"packId": pack["id"], "id": self.entry_id("2014", "weapon")}
        self.assertEqual(self.command("read", payload, self.player)["data"]["rulesEdition"], "2014")
        with self.assertRaises(domain.MapError):
            self.command("import", payload, self.player)
        with self.assertRaises(domain.MapError):
            self.command("permissions", {"packId": pack["id"], "level": "read"}, self.player)
        self.assertFalse(Item.objects.exists())

    def test_batch_read_preserves_individual_documents_order_and_permissions(self):
        pack = self.pack()
        ids = [self.entry_id('2014', kind) for kind in ('armor', 'weapon')]
        payload = {'packId': pack['id'], 'ids': ids}
        expected = [self.command('read', {'packId': pack['id'], 'id': value}) for value in ids]
        self.assertEqual(self.command('read', payload), {'entries': expected})
        with self.assertRaises(domain.MapError) as denied:
            self.command('read', payload, self.player)
        self.assertEqual(denied.exception.code, 'not_found')
        self.command('permissions', {'packId': pack['id'], 'level': 'read'})
        self.assertEqual(self.command('read', payload, self.player), {'entries': expected})
        access = DocumentAccess.objects.create(campaign=self.campaign, kind='compendiums', resource_id=pack['id'], grants={'default': 'read'})
        self.assertEqual(self.command('read', payload, self.streamer), {'entries': expected})
        access.grants = {'default': 'read', 'player': 'none'}
        access.save(update_fields=['grants'])
        with self.assertRaises(domain.MapError) as denied:
            self.command('read', payload, self.player)
        self.assertEqual(denied.exception.code, 'not_found')
        self.assertFalse(Item.objects.exists())

    def test_batch_read_rejects_invalid_duplicate_and_missing_ids_atomically(self):
        pack = self.pack()
        entry_id = self.entry_id('2014', 'weapon')
        for ids in (None, {}, 'weapon', [], [entry_id, entry_id], [True], [1], [''], ['../escape'], ['a' * 121], ['id-' + str(n) for n in range(101)]):
            with self.subTest(ids=ids), self.assertRaises(domain.MapError) as invalid:
                self.command('read', {'packId': pack['id'], 'ids': ids})
            self.assertEqual(invalid.exception.code, 'invalid_data')
        with self.assertRaises(domain.MapError) as invalid:
            self.command('read', {'packId': pack['id'], 'id': entry_id, 'ids': [entry_id]})
        self.assertEqual(invalid.exception.code, 'invalid_data')
        with self.assertRaises(domain.MapError) as missing:
            self.command('read', {'packId': pack['id'], 'ids': [entry_id, 'missing']})
        self.assertEqual(missing.exception.code, 'not_found')
        self.assertEqual(self.command('read', {'packId': pack['id'], 'ids': [entry_id]})['entries'][0]['type'], 'weapon')

    def test_batch_read_retains_installed_package_integrity_and_active_system_gates(self):
        pack = self.pack()
        payload = {'packId': pack['id'], 'ids': [self.entry_id('2014', 'weapon')]}
        self.campaign.system = 'another.rules'
        self.campaign.save(update_fields=['system'])
        with self.assertRaises(domain.MapError):
            self.command('read', payload)
        self.campaign.system = SYSTEM
        self.campaign.save(update_fields=['system'])
        self.package.revoked = True
        self.package.save(update_fields=['revoked'])
        with self.assertRaises(domain.MapError):
            self.command('read', payload)
        self.package.revoked = False
        self.package.save(update_fields=['revoked'])
        path = self.package_root() / 'compendiums/2014.json'
        path.write_text(json.dumps(self.collection('2014', 'tampered')), encoding='utf-8')
        with self.assertRaises(domain.MapError):
            self.command('read', payload)

    def test_raw_package_assets_cannot_bypass_table_scoped_read_grants(self):
        prefix = f'/api/module-packages/{SYSTEM}/{self.package.version}/{self.package.digest}/'
        self.assertEqual(self.state(self.player)['packs'], [])
        for user in (self.gm, self.player):
            self.client.force_login(user)
            for path in ('compendiums/2014.json', 'compendiums/2024.json', 'COMPENDIUMS/2014.JSON'):
                with self.subTest(user=user.email, path=path):
                    response = self.client.get(prefix + path)
                    self.assertEqual(response.status_code, 404)
            response = self.client.get(prefix + 'main.js')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'export default {start(){},stop(){}}')
        pack = self.pack()
        self.command('permissions', {'packId': pack['id'], 'level': 'read'})
        entry = self.command('read', {'packId': pack['id'], 'id': self.entry_id('2014', 'weapon')}, self.player)
        self.assertEqual(entry['type'], 'weapon')
        self.assertEqual(entry['data']['rulesEdition'], '2014')
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(prefix + 'compendiums/2014.json').status_code, 404)

    def test_all_item_types_and_both_editions_import_without_losing_data(self):
        for edition in ("2014", "2024"):
            for kind in ITEM_TYPES:
                with self.subTest(edition=edition, kind=kind):
                    pack = self.pack(edition, spells=kind == "spell")
                    payload = {"packId": pack["id"], "id": self.entry_id(edition, kind)}
                    source = self.command("read", payload)
                    result = self.command("import", payload)
                    self.assertEqual(result["kind"], "item")
                    item = Item.objects.get(pk=result["id"])
                    self.assertEqual(item.type, kind)
                    self.assertEqual(item.system_id, SYSTEM)
                    self.assertEqual(item.data, source["data"])
                    self.assertEqual(item.data["rulesEdition"], edition)
                    self.assertEqual(item.permissions, {})
        self.assertEqual(Item.objects.count(), len(ITEM_TYPES) * 2)

    def test_import_retries_are_idempotent_and_pack_is_immutable(self):
        pack = self.pack()
        payload = {"packId": pack["id"], "id": self.entry_id("2014", "weapon")}
        request_id = uuid.uuid4()
        result = self.command("import", payload, request_id=request_id)
        self.assertEqual(self.command("import", payload, request_id=request_id), result)
        self.assertEqual(Item.objects.count(), 1)
        for action in ("remove", "configure", "delete", "add"):
            with self.subTest(action=action), self.assertRaises(domain.MapError):
                self.command(action, {**payload, "name": "Changed", "version": 1})

    def test_tampered_or_missing_installed_collection_is_not_exposed(self):
        path = self.package_root() / "compendiums/2014.json"
        original = path.read_bytes()
        path.write_text(json.dumps(self.collection("2014", "tampered")), encoding="utf-8")
        self.assertFalse(any("2014" in pack["name"] for pack in self.state()["packs"]))
        path.write_bytes(original)
        path.unlink()
        self.assertFalse(any("2014" in pack["name"] for pack in self.state()["packs"]))

    def test_symlink_collection_cannot_escape_installed_root(self):
        path = self.package_root() / "compendiums/2014.json"
        outside = self.directory / "outside.json"
        outside.write_text(json.dumps(self.collection("2014", "outside")), encoding="utf-8")
        original = path.read_bytes()
        path.unlink()
        try:
            path.symlink_to(outside)
        except (OSError, NotImplementedError):
            path.write_bytes(original)
            self.skipTest("Symlink creation unavailable on this host.")
        self.assertFalse(any("2014" in pack["name"] for pack in self.state()["packs"]))

    def test_manifest_rejects_unsafe_collection_paths(self):
        for path in ("../outside.json", "/absolute.json", "C:/absolute.json", "compendiums\\data.json", "https://example.test/data.json", "compendiums/%2e%2e/data.json", "compendiums/./data.json"):
            with self.subTest(path=path):
                with self.assertRaises(ModuleFailure):
                    self.install("0.2.0", content_path=path)

    def test_install_rejects_malformed_collections_and_invalid_entries(self):
        wrong_shape = {"name": "Broken", "packs": "wrong-shape"}
        wrong_type = self.collection("2014")
        wrong_type["packs"][0]["entries"][0]["type"] = "undeclared"
        wrong_system = self.collection("2014")
        wrong_system["packs"][0]["entries"][0]["systemId"] = "another.rules"
        duplicate_id = self.collection("2014")
        duplicate_id["packs"][0]["entries"].append(deepcopy(duplicate_id["packs"][0]["entries"][0]))
        for value in (wrong_shape, wrong_type, wrong_system, duplicate_id):
            with self.subTest(value=value), self.assertRaises(ModuleFailure):
                self.install("0.2.0", collections={"2014": value})
        self.assertFalse(Package.objects.filter(module_id=SYSTEM, version="0.2.0").exists())
        self.assertEqual(len(self.state()["packs"]), 4)
