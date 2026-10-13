"""Owner release alerts reuse discovery, caching and installation constraints."""

import json
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from unittest.mock import Mock, patch

from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, override_settings

from gravewright.accounts.models import User

from .models import HostSettings
from .updates import AUTOMATIC_CHECK_LEASE_SECONDS, CACHE_TTL_SECONDS, CoreUpdateService


@override_settings(
    GRAVEWRIGHT_RELEASES_REPOSITORY="example/gravewright-django",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class UpdateNotificationTests(TestCase):
    def release(self, version):
        return {
            "tag_name": "v" + version,
            "html_url": "https://github.com/example/gravewright-django/releases/tag/v" + version,
            "body": "Release notes are not part of the notification response.",
            "assets": [{
                "name": f"Gravewright-{version}-django.zip",
                "browser_download_url": f"https://github.com/example/gravewright-django/releases/download/v{version}/Gravewright-{version}-django.zip",
                "digest": "sha256:" + "a" * 64,
                "size": 1024,
            }],
        }

    def service(self, versions=("1.0.0",), **kwargs):
        fetch = Mock(return_value=json.dumps([self.release(version) for version in versions]).encode())
        service = CoreUpdateService(fetcher=fetch, current_version="0.2.1", **kwargs)
        return service, fetch

    def test_discovers_once_and_only_returns_small_notification_payload(self):
        service, fetch = self.service()
        first = service.notification()
        self.assertEqual(first["status"], "available")
        self.assertTrue(first["available"])
        self.assertEqual(first["currentVersion"], "0.2.1")
        self.assertEqual(first["availableVersionLabel"], "1.0.0")
        self.assertEqual(first["url"], "/inside?section=administration&tab=updates")
        self.assertEqual(set(first), {
            "status", "available", "currentVersion", "currentVersionLabel",
            "availableVersion", "availableVersionLabel", "channel", "checkedAt", "url",
        })
        self.assertEqual(service.notification(), first)
        fetch.assert_called_once()
        self.assertNotIn("_automaticCheck", HostSettings.objects.get(pk=1).update_status)

    def test_current_installation_has_no_alert(self):
        service, _ = self.service(("0.2.1",))
        result = service.notification()
        self.assertEqual(result["status"], "current")
        self.assertFalse(result["available"])
        self.assertIsNone(result["availableVersion"])

    def test_alert_respects_selected_channel_and_ignores_unsigned_artifacts(self):
        service, _ = self.service(("0.2.1", "0.3.0-rc.1"), channel="stable")
        self.assertFalse(service.notification()["available"])
        preview, _ = self.service(("0.2.1", "0.3.0-rc.1"), channel="testing")
        self.assertEqual(preview.notification()["availableVersion"], "0.3.0-rc.1")
        unsigned, fetch = self.service(("2.0.0",), channel="dev")
        release = self.release("2.0.0")
        release["assets"][0]["digest"] = ""
        fetch.return_value = json.dumps([release]).encode()
        self.assertFalse(unsigned.notification()["available"])

    def test_failures_are_cached_without_exposing_error_or_rechecking(self):
        service, fetch = self.service()
        fetch.side_effect = OSError("Private upstream details")
        result = service.notification()
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["available"])
        self.assertNotIn("errorKey", result)
        self.assertEqual(service.notification(), result)
        fetch.assert_called_once()

    def test_expired_cached_result_is_refreshed(self):
        service, fetch = self.service(("0.2.1",))
        service.check()
        row = HostSettings.objects.get(pk=1)
        row.update_status["checkedAt"] = int(time.time()) - CACHE_TTL_SECONDS - 1
        row.save(update_fields=["update_status"])
        fetch.return_value = json.dumps([self.release("1.0.0")]).encode()
        self.assertTrue(service.notification()["available"])
        self.assertEqual(fetch.call_count, 2)

    def test_other_request_observes_lease_without_duplicate_discovery(self):
        service, fetch = self.service()
        other, other_fetch = self.service()

        def discover(*_):
            concurrent = other.notification()
            self.assertEqual(concurrent["status"], "checking")
            self.assertFalse(concurrent["available"])
            other_fetch.assert_not_called()
            return json.dumps([self.release("1.0.0")]).encode()

        fetch.side_effect = discover
        self.assertTrue(service.notification()["available"])
        fetch.assert_called_once()
        self.assertTrue(other.notification()["available"])
        other_fetch.assert_not_called()

    def test_expired_lease_recovers_and_preserves_old_metadata_while_checking(self):
        service, fetch = self.service()
        result, claim = service._claim_automatic_check({"retained": "previous metadata"})
        claim["_automaticCheck"]["startedAt"] -= AUTOMATIC_CHECK_LEASE_SECONDS + 1
        HostSettings.objects.create(pk=1, update_status=claim)

        def discover(*_):
            row = HostSettings.objects.get(pk=1)
            self.assertEqual(row.update_status["retained"], "previous metadata")
            self.assertEqual(CoreUpdateService(current_version="0.2.1").status()["status"], "unchecked")
            return json.dumps([self.release("1.0.0")]).encode()

        fetch.side_effect = discover
        self.assertTrue(service.notification()["available"])
        self.assertNotIn("_automaticCheck", HostSettings.objects.get(pk=1).update_status)

    def test_manual_refresh_supersedes_in_flight_automatic_check(self):
        service, fetch = self.service()
        manual, _ = self.service(("2.0.0",))

        def discover(*_):
            self.assertEqual(manual.check()["availableVersion"], "2.0.0")
            return json.dumps([self.release("1.0.0")]).encode()

        fetch.side_effect = discover
        self.assertEqual(service.notification()["availableVersion"], "2.0.0")
        self.assertEqual(HostSettings.objects.get(pk=1).update_status["availableVersion"], "2.0.0")

    def test_channel_change_supersedes_in_flight_check(self):
        service, fetch = self.service()

        def discover(*_):
            HostSettings.objects.filter(pk=1).update(channel="testing", update_status={})
            return json.dumps([self.release("1.0.0")]).encode()

        fetch.side_effect = discover
        self.assertEqual(service.notification()["status"], "unchecked")
        self.assertEqual(HostSettings.objects.get(pk=1).update_status, {})

    def test_automatic_check_rereads_host_channel_before_claiming(self):
        fetch = Mock(return_value=json.dumps([self.release("9.0.0-rc.1")]).encode())
        service = CoreUpdateService(fetcher=fetch)
        HostSettings.objects.filter(pk=1).update(channel="testing", update_status={})
        result = service.notification()
        self.assertEqual(result["channel"], "testing")
        self.assertEqual(result["availableVersion"], "9.0.0-rc.1")

    def test_new_channel_result_wins_while_old_channel_request_is_in_flight(self):
        fetch = Mock()
        service = CoreUpdateService(fetcher=fetch)

        def discover(*_):
            HostSettings.objects.filter(pk=1).update(channel="testing", update_status={})
            newer = CoreUpdateService(fetcher=lambda *_: json.dumps([self.release("9.0.0-rc.1")]).encode())
            self.assertEqual(newer.notification()["availableVersion"], "9.0.0-rc.1")
            return json.dumps([self.release("1.0.0")]).encode()

        fetch.side_effect = discover
        result = service.notification()
        self.assertEqual(result["channel"], "testing")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["availableVersion"], "9.0.0-rc.1")
        self.assertEqual(HostSettings.objects.get(pk=1).update_status["channel"], "testing")

    def test_file_cache_reuses_discovery_and_supports_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "releases.json"
            service, fetch = self.service(cache_path=cache)
            other, other_fetch = self.service(cache_path=cache)

            def discover(*_):
                self.assertEqual(other.notification()["status"], "checking")
                return json.dumps([self.release("1.0.0")]).encode()

            fetch.side_effect = discover
            self.assertTrue(service.notification()["available"])
            self.assertTrue(other.notification()["available"])
            fetch.assert_called_once()
            other_fetch.assert_not_called()

    def test_endpoint_requires_owner_and_post_and_preserves_csrf(self):
        url = "/api/admin/updates/notification"
        self.assertEqual(self.client.post(url).status_code, 401)
        player = User.objects.create_user(email="player@notifications.test", name="Player", password="long-test-password")
        self.client.force_login(player)
        with patch("gravewright.administration.views.CoreUpdateService") as service:
            self.assertEqual(self.client.post(url).status_code, 403)
            service.assert_not_called()
        owner = User.objects.create_user(email="owner@notifications.test", name="Owner", password="long-test-password", role="owner")
        self.client.force_login(owner)
        self.assertEqual(self.client.get(url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(owner)
        self.assertEqual(strict.post(url).status_code, 403)
        with patch("gravewright.administration.views.CoreUpdateService") as service:
            service.return_value.notification.return_value = {"available": False, "status": "current"}
            response = self.client.post(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertFalse(response.json()["available"])
            service.return_value.notification.assert_called_once_with()


@override_settings(GRAVEWRIGHT_RELEASES_REPOSITORY="example/gravewright-django")
class ConcurrentUpdateNotificationTests(TransactionTestCase):
    def test_simultaneous_stale_reads_only_claim_one_network_check(self):
        HostSettings.objects.create(pk=1)
        both_read = threading.Barrier(2)
        finish = threading.Event()
        original_claim = CoreUpdateService._claim_automatic_check

        def simultaneous_claim(service, cached):
            if not cached:
                both_read.wait(timeout=5)
            return original_claim(service, cached)

        def discover(*_):
            if not finish.wait(timeout=5):
                raise RuntimeError("Concurrent request did not complete")
            return b"[]"

        fetches = [Mock(side_effect=discover), Mock(side_effect=discover)]

        def check(fetch):
            try:
                return CoreUpdateService(fetcher=fetch, current_version="0.2.1").notification()
            finally:
                connections.close_all()

        with patch.object(CoreUpdateService, "_claim_automatic_check", simultaneous_claim):
            with ThreadPoolExecutor(max_workers=2) as executor:
                pending = [executor.submit(check, fetch) for fetch in fetches]
                try:
                    completed, _ = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
                    self.assertEqual(len(completed), 1)
                    self.assertEqual(next(iter(completed)).result()["status"], "checking")
                finally:
                    finish.set()
                self.assertEqual(sorted(future.result(timeout=5)["status"] for future in pending), ["checking", "failed"])
        self.assertEqual(sum(fetch.call_count for fetch in fetches), 1)

    def test_independent_database_connections_share_the_automatic_check_lease(self):
        started = threading.Event()
        finish = threading.Event()

        def discover(*_):
            started.set()
            if not finish.wait(timeout=5):
                raise RuntimeError("Concurrent request did not complete")
            return b"[]"

        first_fetch = Mock(side_effect=discover)
        other_fetch = Mock()

        def check_first():
            try:
                return CoreUpdateService(fetcher=first_fetch, current_version="0.2.1").notification()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(check_first)
            try:
                self.assertTrue(started.wait(timeout=5))
                other = CoreUpdateService(fetcher=other_fetch, current_version="0.2.1").notification()
                self.assertEqual(other["status"], "checking")
                other_fetch.assert_not_called()
            finally:
                finish.set()
            self.assertEqual(pending.result(timeout=5)["status"], "failed")
        first_fetch.assert_called_once()
        self.assertNotIn("_automaticCheck", HostSettings.objects.get(pk=1).update_status)
