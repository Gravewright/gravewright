"""Installed release identity and complete notes remain usable offline."""

import json
from pathlib import Path
import tempfile
import time
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from . import release_presentation
from .release_presentation import MAX_RELEASE_NOTES_BYTES, bounded_notes, installed_release
from .updates import CoreUpdateService


@override_settings(GRAVEWRIGHT_RELEASES_REPOSITORY="example/gravewright-django")
class ReleasePresentationTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.notes = self.root / "docs/releases/0.2.1.md"
        self.notes.parent.mkdir(parents=True)
        self.body = "# Gravewright 0.2.1 — Alpha\n\n" + "Complete notes.\n" * 400 + "\n## Português (Brasil)\nNotas completas.\n"
        self.notes.write_text(self.body, encoding="utf-8")
        (self.root / "pyproject.toml").write_text(
            '[project]\nversion="0.2.1"\nclassifiers=["Development Status :: 3 - Alpha"]\n',
            encoding="utf-8",
        )
        root = patch.object(release_presentation, "_PROJECT_ROOT", self.root)
        root.start()
        self.addCleanup(root.stop)
        self.cache = self.root / "release-cache.json"

    def service(self, fetcher=None, version="0.2.1"):
        return CoreUpdateService(
            fetcher=fetcher or Mock(), cache_path=self.cache,
            current_version=version, channel="stable",
        )

    def published(self, notes, name="Gravewright 0.2.1 — Published Alpha"):
        return {
            "tag_name": "v0.2.1", "name": name, "body": notes,
            "html_url": "https://github.com/example/gravewright-django/releases/tag/v0.2.1",
            "assets": [{
                "name": "Gravewright-0.2.1-django.zip",
                "browser_download_url": "https://github.com/example/gravewright-django/releases/download/v0.2.1/Gravewright-0.2.1-django.zip",
                "digest": "sha256:" + "a" * 64, "size": 1024,
            }],
        }

    def test_unchecked_status_immediately_has_full_bundled_name_and_notes_without_fetch(self):
        fetcher = Mock()
        result = self.service(fetcher).status()
        self.assertEqual(result["status"], "unchecked")
        self.assertEqual(result["currentVersionLabel"], "0.2.1")
        self.assertEqual(result["installedRelease"], {
            "version": "0.2.1", "name": "Gravewright 0.2.1 — Alpha",
            "notes": self.body,
            "url": "https://github.com/example/gravewright-django/releases/tag/v0.2.1",
            "source": "bundled",
        })
        fetcher.assert_not_called()
        self.assertFalse(self.cache.exists())

    def test_failed_online_check_keeps_complete_local_notes_without_storing_them(self):
        service = self.service(Mock(side_effect=OSError("offline")))
        result = service.check()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["installedRelease"]["notes"], self.body)
        self.assertEqual(service.status()["installedRelease"], result["installedRelease"])
        self.assertNotIn("installedRelease", json.loads(self.cache.read_text(encoding="utf-8")))

    def test_cached_installed_release_uses_official_name_and_recovers_old_truncated_notes(self):
        service = self.service(Mock(return_value=json.dumps([self.published("x" * 4000)]).encode()))
        result = service.check()
        self.assertEqual(result["installedRelease"]["name"], "Gravewright 0.2.1 — Published Alpha")
        self.assertEqual(result["installedRelease"]["notes"], self.body)
        self.assertEqual(result["installedRelease"]["source"], "bundled")
        self.assertEqual(service.status()["installedRelease"], result["installedRelease"])
        self.assertNotIn("installedRelease", json.loads(self.cache.read_text(encoding="utf-8")))

    def test_complete_published_notes_are_not_truncated_at_four_thousand_characters(self):
        self.notes.unlink()
        notes = "# Published release\n\n" + "Notes beyond the old limit.\n" * 1000 + "\n## Português (Brasil)\nFim."
        service = self.service(Mock(return_value=json.dumps([self.published(notes)]).encode()))
        result = service.check()
        self.assertEqual(result["releaseNotes"], notes)
        self.assertEqual(result["releases"][0]["notes"], notes)
        self.assertEqual(result["installedRelease"]["notes"], notes)
        self.assertEqual(result["installedRelease"]["source"], "published")
        self.assertEqual(service.status()["installedRelease"]["notes"], notes)

    def test_complete_published_notes_precede_bundled_notes(self):
        notes = "Published amendment.\n" * 400
        result = self.service(Mock(return_value=json.dumps([self.published(notes)]).encode())).check()
        self.assertEqual(result["installedRelease"]["notes"], notes)
        self.assertEqual(result["installedRelease"]["source"], "published")

    def test_old_or_foreign_repository_cache_does_not_supply_installed_name(self):
        service = self.service(Mock(return_value=json.dumps([self.published("Published notes")]).encode()))
        service.check()
        cached = json.loads(self.cache.read_text(encoding="utf-8"))
        for field, value in (("repository", "another/repository"), ("checkedAt", int(time.time()) - 2 * 86400)):
            changed = {**cached, field: value}
            self.cache.write_text(json.dumps(changed), encoding="utf-8")
            result = service.status()
            self.assertEqual(result["status"], "unchecked")
            self.assertEqual(result["installedRelease"]["name"], "Gravewright 0.2.1 — Alpha")

    def test_missing_notes_use_matching_project_stage_without_changing_version_labels(self):
        self.notes.unlink()
        result = self.service().status()["installedRelease"]
        self.assertEqual(result["name"], "Gravewright 0.2.1 — Alpha")
        self.assertEqual(result["notes"], "")
        self.assertEqual(result["source"], "metadata")
        self.assertEqual(self.service(version="9.0.0").status()["installedRelease"]["name"], "Gravewright 9.0.0")

    def test_unreadable_or_invalid_metadata_does_not_break_status(self):
        self.notes.unlink()
        (self.root / "pyproject.toml").write_text("invalid TOML", encoding="utf-8")
        self.assertEqual(self.service().status()["installedRelease"]["name"], "Gravewright 0.2.1")
        self.notes.write_text(self.body, encoding="utf-8")
        original = Path.open

        def unreadable(path, *args, **kwargs):
            if path == self.notes:
                raise PermissionError("unreadable notes")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", unreadable):
            self.assertEqual(self.service().status()["installedRelease"]["notes"], "")

    def test_invalid_version_and_repository_cannot_form_paths_or_links(self):
        with patch.object(release_presentation, "_bundled_text", return_value="") as read:
            result = installed_release("../../outside", "example/repo")
        self.assertEqual([call.args[0] for call in read.call_args_list], ["pyproject.toml"])
        self.assertEqual(result["url"], "")
        self.assertEqual(installed_release("0.2.1", "../outside")["url"], "")

    def test_notes_have_a_utf8_byte_limit_in_metadata_and_bundled_documents(self):
        notes = "á" * MAX_RELEASE_NOTES_BYTES
        limited = bounded_notes(notes)
        self.assertLessEqual(len(limited.encode("utf-8")), MAX_RELEASE_NOTES_BYTES)
        self.notes.write_text("# Release\n" + notes, encoding="utf-8")
        bundled = self.service().status()["installedRelease"]["notes"]
        self.assertTrue(bundled.startswith("# Release\n"))
        self.assertLessEqual(len(bundled.encode("utf-8")), MAX_RELEASE_NOTES_BYTES)
        self.notes.unlink()
        result = self.service(Mock(return_value=json.dumps([self.published(notes)]).encode())).check()
        self.assertEqual(result["releaseNotes"], limited)
        self.assertEqual(result["releases"][0]["notes"], limited)
        self.assertEqual(result["installedRelease"]["notes"], limited)

    def test_symlinked_release_notes_outside_the_project_are_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "external.md"
            external.write_text("# External notes\nDo not read.", encoding="utf-8")
            self.notes.unlink()
            try:
                self.notes.symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symbolic links is unavailable on this platform.")
            result = self.service().status()["installedRelease"]
            self.assertEqual(result["notes"], "")
            self.assertEqual(result["source"], "metadata")
