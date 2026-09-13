import io
import tempfile
import zipfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor, Asset
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.models import BoardEntry, Journal
from gravewright.maps.models import Broadcast, Scene, SceneObject, SceneState, Tile
from gravewright.pdf_system.schema import normalize
from gravewright.tokens.models import Token

from .archives import export_campaign, import_campaign


class ArchiveTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        setting = override_settings(MEDIA_ROOT=self.temp.name)
        setting.enable()
        self.addCleanup(setting.disable)
        self.user = User.objects.create_user(
            email="archive@example.test",
            name="Archive",
            password="a-long-test-password",
            role="owner",
        )
        self.campaign = Campaign.objects.create(owner=self.user, name="Original")
        Membership.objects.create(campaign=self.campaign, user=self.user, role="gm")
        self.scene = Scene.objects.create(
            campaign=self.campaign, name="Map", width=70, height=70
        )
        SceneState.objects.create(scene=self.scene, lighting={"mode": "manual"})
        SceneObject.objects.create(
            scene=self.scene, kind="walls", data={"x1": 0, "y1": 0, "x2": 70, "y2": 70}
        )
        Tile.objects.create(
            scene=self.scene,
            lod=0,
            x=0,
            y=0,
            file=ContentFile(b"image", name="test.webp"),
        )
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.actor = Actor.objects.create(
            campaign=self.campaign, name="Hero", data=normalize({})
        )
        Token.objects.create(scene=self.scene, actor=self.actor)
        asset = Asset.objects.create(
            campaign=self.campaign,
            actor=self.actor,
            kind="portrait",
            name="Hero",
            file=ContentFile(b"portrait", name="portrait.png"),
        )
        quest = Journal.objects.create(
            campaign=self.campaign,
            title="Quest",
            type="quest",
            data={"image": f"/game/actors/asset/{asset.pk}"},
        )
        board = Journal.objects.create(
            campaign=self.campaign, title="Board", type="quest-board"
        )
        BoardEntry.objects.create(board=board, quest=quest)

    def test_roundtrip_graph_files_and_reference_remapping(self):
        restored = import_campaign(
            export_campaign(self.campaign), self.user, "Imported"
        )
        scene = Scene.objects.get(campaign=restored)
        token = Token.objects.get(scene=scene)
        self.assertNotEqual(scene.pk, self.scene.pk)
        self.assertNotEqual(scene.block_id, self.scene.block_id)
        self.assertEqual(token.actor.campaign, restored)
        self.assertEqual(scene.environment.lighting, {"mode": "manual"})
        self.assertEqual(Tile.objects.get(scene=scene).file.read(), b"image")
        self.assertEqual(Broadcast.objects.get(campaign=restored).scene, scene)
        asset = Asset.objects.get(campaign=restored)
        self.assertIn(
            str(asset.pk),
            Journal.objects.get(campaign=restored, type="quest").data["image"],
        )
        self.assertEqual(
            BoardEntry.objects.get(board__campaign=restored).quest.campaign, restored
        )
        self.assertEqual(Campaign.objects.count(), 2)

    def test_corrupt_archive_rejected_without_creating_campaign(self):
        raw = export_campaign(self.campaign)
        with zipfile.ZipFile(io.BytesIO(raw)) as original:
            out = io.BytesIO()
            with zipfile.ZipFile(out, "w") as modified:
                for name in original.namelist():
                    modified.writestr(
                        name,
                        b"corrupt" if name == "campaign.json" else original.read(name),
                    )
        with self.assertRaises(AuthError):
            import_campaign(out.getvalue(), self.user)
        self.assertEqual(Campaign.objects.count(), 1)

    def test_restore_keeps_membership_and_campaign_identity(self):
        raw = export_campaign(self.campaign)
        self.actor.name = "Changed"
        self.actor.save()
        result = import_campaign(raw, self.user, target=self.campaign)
        self.assertEqual(result.pk, self.campaign.pk)
        self.assertEqual(Membership.objects.filter(campaign=result).count(), 1)
        self.assertEqual(Actor.objects.get(campaign=result).name, "Hero")

    def test_admin_endpoints_require_owner(self):
        player = User.objects.create_user(
            email="player@example.test", name="Player", password="a-long-test-password"
        )
        self.client.force_login(player)
        self.assertEqual(self.client.get("/api/admin/status").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/admin/updates/check", {}, content_type="application/json"
            ).status_code,
            403,
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/admin/status").status_code, 200)
        for section in ["administration", "addons", "marketplace"]:
            response = self.client.get("/inside", {"section": section})
            self.assertEqual(response.status_code, 200)

    def test_snapshot_preserves_document_ids_permissions_and_whispers(self):
        import uuid

        from gravewright.chat.models import Message, Recipient
        from gravewright.journals.models import Access

        player = User.objects.create_user(
            email="backup-player@example.test",
            name="Player",
            password="test-password-123",
        )
        Membership.objects.create(campaign=self.campaign, user=player)
        self.actor.permissions = {str(player.pk): "owner"}
        self.actor.save()
        journal = Journal.objects.filter(campaign=self.campaign).first()
        Access.objects.create(journal=journal, user=player, level="read")
        message = Message.objects.create(
            campaign=self.campaign,
            scene=self.scene,
            author=player,
            author_name="Player",
            text="Whisper",
            visibility="whisper",
            request_id=uuid.uuid4(),
        )
        Recipient.objects.create(message=message, user=self.user)
        raw = export_campaign(self.campaign, snapshot=True)
        import_campaign(raw, self.user, target=self.campaign)
        self.assertEqual(
            Actor.objects.get(pk=self.actor.pk).permissions, {str(player.pk): "owner"}
        )
        self.assertEqual(Access.objects.get(journal_id=journal.pk).user, player)
        self.assertEqual(Message.objects.get(pk=message.pk).author, player)
        self.assertEqual(Recipient.objects.get(message_id=message.pk).user, self.user)


@override_settings(GRAVEWRIGHT_RELEASES_REPOSITORY="example/gravewright-django")
class UpdateTests(TestCase):
    def test_installed_alpha_matches_its_release_and_stable_is_an_upgrade(self):
        import json
        from .updates import CoreUpdateService
        from .models import HostSettings
        alpha = self.release('0.1.0-alpha.0')
        service = CoreUpdateService(fetcher=lambda *_: json.dumps([alpha]).encode(), channel='dev', current_version='0.1.0-alpha.0')
        self.assertEqual(service.current_version, '0.1.0-alpha.0')
        result = service.check()
        self.assertEqual(result['status'], 'current')
        self.assertEqual(result['currentVersionLabel'], 'Alpha 0.1.0')
        self.assertEqual(result['availableVersionLabel'], 'Alpha 0.1.0')
        self.assertEqual(service.status()['currentVersionLabel'], 'Alpha 0.1.0')
        row = HostSettings.objects.get(pk=1)
        self.assertEqual(row.channel, 'stable')
        stable = self.release('0.1.0')
        result = CoreUpdateService(fetcher=lambda *_: json.dumps([stable]).encode(), current_version='0.1.0-alpha.0').check()
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['availableVersion'], '0.1.0')

    def test_preview_channel_offers_newer_stable_release(self):
        import json
        from .updates import CoreUpdateService
        releases = [self.release('0.1.0-alpha.0'), self.release('0.1.1')]
        service = CoreUpdateService(fetcher=lambda *_: json.dumps(releases).encode(),
                                    current_version='0.1.0-alpha.0', channel='dev')
        result = service.check()
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['availableVersion'], '0.1.1')
        self.assertEqual(result['resolvedChannel'], 'stable')

    @override_settings(GRAVEWRIGHT_RELEASES_REPOSITORY="")
    def test_unconfigured_source_never_fetches_legacy_releases(self):
        from unittest.mock import Mock
        from .updates import CoreUpdateService
        fetch = Mock()
        result = CoreUpdateService(fetcher=fetch).check()
        self.assertEqual(result['errorKey'], 'CORE_RELEASE_SOURCE_NOT_CONFIGURED')
        fetch.assert_not_called()

    def test_rejects_legacy_artifact_and_invalidates_cache_on_source_change(self):
        import json
        from .updates import CoreUpdateService
        release = self.release('1.0.0')
        release['assets'][0]['name'] = 'Gravewright-1.0.0-win64.zip'
        service = CoreUpdateService(fetcher=lambda *_: json.dumps([release]).encode(), current_version='0.1.0')
        self.assertEqual(service.check()['status'], 'failed')
        with self.settings(GRAVEWRIGHT_RELEASES_REPOSITORY='another/project'):
            self.assertEqual(CoreUpdateService(current_version='0.1.0').status()['status'], 'unchecked')

    def test_history_includes_old_releases_other_channels_and_all_pages(self):
        import json
        from .updates import CoreUpdateService
        urls = []
        first = [self.release(f'0.0.{i}') for i in range(100)]
        old = self.release('0.1.0-alpha.0')
        def fetch(url, limit):
            urls.append(url)
            return json.dumps(first if url.endswith('&page=1') else [old, self.release('9.0.0', draft=True)]).encode()
        result = CoreUpdateService(fetcher=fetch, current_version='0.1.1', channel='stable').check()
        self.assertEqual(len(urls), 2)
        self.assertEqual(len(result['releases']), 101)
        self.assertEqual(result['releases'][-1]['version'], '0.1.0-alpha.0')
        self.assertEqual(result['availableVersion'], '0.0.99')

    def release(self, version, *, digest=True, draft=False):
        return {
            "tag_name": "v" + version,
            "draft": draft,
            "name": version,
            "html_url": "https://github.com/example/gravewright-django/releases/tag/v"
            + version,
            "assets": [
                {
                    "name": f"Gravewright-{version}-django.zip",
                    "browser_download_url": f"https://github.com/example/gravewright-django/releases/download/v{version}/Gravewright-{version}-django.zip",
                    "digest": "sha256:" + "a" * 64 if digest else "",
                    "size": 1024,
                }
            ],
        }

    def test_release_channels_cache_and_missing_digest(self):
        import json

        from .updates import CoreUpdateService

        releases = [
            self.release("1.0.0"),
            self.release("1.1.0-rc.2"),
            self.release("2.0.0", digest=False),
            self.release("3.0.0", draft=True),
        ]
        fetch = lambda *_: json.dumps(releases).encode()
        stable = CoreUpdateService(
            fetcher=fetch, current_version="0.1.0", channel="stable"
        )
        result = stable.check()
        self.assertEqual(result["availableVersion"], "1.0.0")
        self.assertEqual(stable.status()["status"], "available")
        testing = CoreUpdateService(
            fetcher=fetch, current_version="0.1.0", channel="testing"
        )
        self.assertEqual(testing.check()["availableVersion"], "1.1.0-rc.2")
        broken = CoreUpdateService(
            fetcher=lambda *_: b"[]", current_version="0.1.0", channel="stable"
        )
        self.assertEqual(broken.check()["status"], "failed")


class EnvironmentRetentionTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        media = override_settings(MEDIA_ROOT=self.temp.name)
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(email='retention@example.test', name='Owner', password='long-password-value', role='owner')
        self.campaign = Campaign.objects.create(owner=self.user, name='Retention')
        Membership.objects.create(campaign=self.campaign, user=self.user, role='gm')
        self.client.force_login(self.user)

    @override_settings(CAMPAIGN_SNAPSHOT_RETENTION=1)
    def test_snapshot_retention_removes_old_file(self):
        from .models import Snapshot
        url = f'/api/containers/{self.campaign.pk}/snapshots'
        self.assertEqual(self.client.post(url, {'name':'First'}, content_type='application/json').status_code, 201)
        old = Snapshot.objects.get()
        storage, path = old.archive.storage, old.archive.name
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url, {'name':'Second'}, content_type='application/json').status_code, 201)
        self.assertEqual(list(Snapshot.objects.values_list('name', flat=True)), ['Second'])
        self.assertFalse(storage.exists(path))

    @override_settings(CAMPAIGN_SNAPSHOTS_ENABLED=False)
    def test_disabled_snapshots_rejected_by_api(self):
        response = self.client.post(f'/api/containers/{self.campaign.pk}/snapshots', {'name':'Disabled'}, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    @override_settings(ADMINISTRATIVE_AUDIT_RETENTION_DAYS=1)
    def test_audit_retention_and_disable(self):
        from datetime import timedelta
        from types import SimpleNamespace
        from django.utils import timezone
        from .models import AuditEvent
        from .views import audit
        old = AuditEvent.objects.create(user=self.user, action='old')
        AuditEvent.objects.filter(pk=old.pk).update(created_at=timezone.now()-timedelta(days=2))
        request = SimpleNamespace(user=self.user)
        audit(request, 'new')
        self.assertEqual(list(AuditEvent.objects.values_list('action', flat=True)), ['new'])
        with override_settings(ADMINISTRATIVE_AUDIT_ENABLED=False):
            audit(request, 'disabled')
        self.assertEqual(AuditEvent.objects.count(), 1)
