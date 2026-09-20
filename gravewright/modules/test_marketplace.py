import base64
import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from gravewright.accounts.models import User

from .models import Package
from .packages import ModuleFailure, canonical, host


class MarketplaceTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.key = Ed25519PrivateKey.generate()
        self.keyfile = self.directory / "keys.json"
        self.keyfile.write_text(json.dumps({
            "publisher": base64.b64encode(self.key.public_key().public_bytes_raw()).decode()
        }))
        override = override_settings(
            MEDIA_ROOT=temporary.name,
            GRAVEWRIGHT_MARKETPLACE_URL="https://publisher.example/catalog.json",
            GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=str(self.keyfile),
        )
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user(
            email="owner@marketplace.test", name="Owner", role="owner"
        )
        self.client.force_login(self.user)

    def release(self, **changes):
        manifest = {
            "id": "publisher.test",
            "version": "1.0.0",
            "name": "Test package",
            "description": "A marketplace test package",
            "author": "Test publisher",
            "license": "MIT",
            "sdk": {"requires": ">=1.0.0 <2.0.0", "tested": "1.0.0"},
            "entry": "main.js",
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("main.js", "export default {start(){},stop(){}}")
        raw = output.getvalue()
        record = {
            "id": manifest["id"],
            "version": manifest["version"],
            "sdk": manifest["sdk"]["requires"],
            "download": "https://publisher.example/module.zip",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "keyId": "publisher",
            **changes,
        }
        record["signature"] = base64.b64encode(self.key.sign(canonical(record))).decode()
        return record, raw

    def assert_configuration_failure(self, code, field="keys"):
        with patch("gravewright.modules.views.download") as download:
            response = self.client.get("/api/marketplace/status")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["errors"], [{"field": field, "code": code}])
            self.assertFalse(response.json()["ready"])
            for response in [
                self.client.get("/api/marketplace"),
                self.client.post(
                    "/api/marketplace/install",
                    {"id": "publisher.test", "version": "1.0.0"},
                    content_type="application/json",
                ),
            ]:
                self.assertEqual(response.status_code, 503, response.content)
                self.assertEqual(response.json(), {"error": code})
            download.assert_not_called()

    def test_status_checks_local_configuration_without_constructing_host(self):
        with patch("gravewright.modules.views.host") as engine, patch(
            "gravewright.modules.views.download"
        ) as download:
            response = self.client.get("/api/marketplace/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "catalogConfigured": True,
            "trustedKeysConfigured": True,
            "ready": True,
            "errors": [],
            "sdk": "1.0.0",
        })
        engine.assert_not_called()
        download.assert_not_called()
        self.assertFalse((self.directory / "modules").exists())

    def test_missing_or_empty_keys_are_controlled_configuration_errors(self):
        with override_settings(GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=""):
            self.assert_configuration_failure("marketplace_keys_missing")
        self.keyfile.write_text("{}")
        self.assert_configuration_failure("marketplace_keys_empty")
        self.keyfile.unlink()
        self.assert_configuration_failure("marketplace_keys_unreadable")

    def test_malformed_keys_never_return_server_errors(self):
        for raw in [
            b"{broken", b"[]", b"null", b'{"publisher": 42}',
            b'{"publisher": "invalid base64!"}', b'{"publisher": "eA=="}',
            b'{"publisher": "\xff"}',
        ]:
            with self.subTest(raw=raw):
                self.keyfile.write_bytes(raw)
                self.assert_configuration_failure("marketplace_keys_invalid")
        with patch("gravewright.modules.packages.Path.read_text", side_effect=PermissionError):
            self.assert_configuration_failure("marketplace_keys_unreadable")

    def test_invalid_catalog_configuration_is_diagnosed_before_download(self):
        for url in [
            "", "http://publisher.example/catalog.json", "https://[invalid",
            "https://publisher.example:invalid/catalog.json",
            "https://user:password@publisher.example/catalog.json",
            "https://publisher.example/catalog.json#fragment",
        ]:
            with self.subTest(url=url), override_settings(GRAVEWRIGHT_MARKETPLACE_URL=url):
                self.assert_configuration_failure(
                    "marketplace_catalog_invalid" if url else "marketplace_catalog_missing",
                    "catalog",
                )

    def test_status_reports_both_missing_settings(self):
        with override_settings(GRAVEWRIGHT_MARKETPLACE_URL="", GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=""):
            status = self.client.get("/api/marketplace/status").json()
        self.assertFalse(status["catalogConfigured"])
        self.assertFalse(status["trustedKeysConfigured"])
        self.assertEqual(status["errors"], [
            {"field": "catalog", "code": "marketplace_catalog_missing"},
            {"field": "keys", "code": "marketplace_keys_missing"},
        ])

    def test_installed_packages_are_visible_without_marketplace_configuration(self):
        record, raw = self.release()
        manifest = host().install(record, raw)
        self.keyfile.write_text("broken")
        with override_settings(GRAVEWRIGHT_MARKETPLACE_URL=""), patch(
            "gravewright.modules.views.download"
        ) as download, patch("gravewright.modules.views.host") as engine:
            response = self.client.get("/api/module-packages")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [{**manifest, "revoked": False}])
        download.assert_not_called()
        engine.assert_not_called()

    def test_remote_failure_and_invalid_signatures_remain_controlled(self):
        record, _ = self.release()
        record["signature"] = base64.b64encode(b"x" * 64).decode()
        for payload, status, code in [
            (b"not JSON", 400, "invalid_data"),
            (json.dumps([record]).encode(), 403, "permission_denied"),
        ]:
            with self.subTest(code=code), patch("gravewright.modules.views.download", return_value=payload):
                response = self.client.get("/api/marketplace")
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), {"error": code})
        with patch("gravewright.modules.views.download", side_effect=ModuleFailure("unavailable")):
            response = self.client.get("/api/marketplace")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "unavailable"})
        self.assertFalse(Package.objects.exists())

    def test_install_refreshes_database_and_catalog_applies_signed_revocations(self):
        record, raw = self.release()
        with patch("gravewright.modules.views.download", side_effect=[json.dumps([record]).encode(), raw]):
            response = self.client.post(
                "/api/marketplace/install", {"id": record["id"], "version": record["version"]},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(self.client.get("/api/module-packages").json()[0]["revoked"])
        revoked, _ = self.release(status="revoked")
        incompatible, _ = self.release(version="2.0.0", sdk=">=2.0.0")
        active, _ = self.release(id="publisher.other")
        with patch("gravewright.modules.views.download", return_value=json.dumps([revoked, incompatible, active]).encode()):
            response = self.client.get("/api/marketplace")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), [active])
        self.assertTrue(self.client.get("/api/module-packages").json()[0]["revoked"])

    def test_signed_record_with_malformed_download_url_is_rejected(self):
        for url in [
            "https://[invalid/module.zip",
            "https://publisher.example:invalid/module.zip",
            "https://publisher.example:65536/module.zip",
        ]:
            record, _ = self.release(download=url)
            with self.subTest(url=url), patch(
                "gravewright.modules.views.download", return_value=json.dumps([record]).encode()
            ) as download:
                response = self.client.get("/api/marketplace")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json(), {"error": "invalid_data"})
                response = self.client.post(
                    "/api/marketplace/install", {"id": record["id"], "version": record["version"]},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json(), {"error": "invalid_data"})
                self.assertTrue(all(
                    call.args[0] == "https://publisher.example/catalog.json"
                    for call in download.call_args_list
                ))
        self.assertFalse(Package.objects.exists())

    def test_invalid_catalog_cannot_apply_partial_revocations(self):
        record, raw = self.release()
        host().install(record, raw)
        revoked, _ = self.release(status="revoked")
        invalid, _ = self.release(id="publisher.invalid")
        invalid["signature"] = "invalid"
        with patch("gravewright.modules.views.download", return_value=json.dumps([revoked, invalid]).encode()):
            response = self.client.get("/api/marketplace")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Package.objects.get().revoked)

    def test_marketplace_diagnostics_and_mutations_remain_owner_only(self):
        player = User.objects.create_user(email="player@marketplace.test", name="Player")
        self.client.force_login(player)
        for response in [
            self.client.get("/api/marketplace/status"),
            self.client.get("/api/marketplace"),
            self.client.post("/api/marketplace/install", {}, content_type="application/json"),
        ]:
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/module-packages").status_code, 200)

    def test_owner_installs_local_zip_into_configured_folder_without_marketplace(self):
        _, raw = self.release()
        destination = self.directory / "operator-modules"
        self.keyfile.write_text("broken")
        with override_settings(
            GRAVEWRIGHT_MODULES_ROOT=destination,
            GRAVEWRIGHT_MARKETPLACE_URL="",
        ), patch("gravewright.modules.views.download") as download:
            configuration = self.client.get("/api/module-packages/install-local")
            response = self.client.post("/api/module-packages/install-local", {
                "kind": "module",
                "file": SimpleUploadedFile("package.zip", raw, content_type="application/zip"),
            })
            installed = self.client.get("/api/module-packages").json()
            host().verify_installed(Package.objects.get())
        self.assertEqual(configuration.json()["directory"], str(destination))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["manifest"]["id"], "publisher.test")
        self.assertNotIn("record", installed[0])
        self.assertEqual(Package.objects.get().record["source"], "local")
        self.assertTrue((destination / "archives" / (Package.objects.get().digest + ".zip")).is_file())
        download.assert_not_called()

    def test_local_zip_must_match_library_and_remains_owner_only(self):
        _, raw = self.release()
        response = self.client.post("/api/module-packages/install-local", {
            "kind": "system",
            "file": SimpleUploadedFile("package.zip", raw, content_type="application/zip"),
        })
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Package.objects.exists())
        player = User.objects.create_user(email="local-player@example.test", name="Player")
        self.client.force_login(player)
        self.assertEqual(self.client.get("/api/module-packages/install-local").status_code, 403)

    def test_owner_installs_default_marketplace_from_settings_screen(self):
        raw = b'{\n  "gravewright-2026": "PXbpURq9J1jLkPnnwBVN/5B+zrb0p5MaWQAe/ltJ8LY="\n}\n'
        data = self.directory / "runner-data"
        data.mkdir()
        (data / ".env").write_text("DJANGO_SECRET_KEY=" + "x" * 64 + "\n")
        with override_settings(
            RUNNER_DATA=data,
            GRAVEWRIGHT_MARKETPLACE_URL="",
            GRAVEWRIGHT_MARKETPLACE_KEYS_FILE="",
        ), patch.dict(os.environ, {
            "GRAVEWRIGHT_MARKETPLACE_URL": "",
            "GRAVEWRIGHT_MARKETPLACE_KEYS_FILE": "",
        }), patch(
            "scripts.gravewright_runner._download_default_keys", return_value=raw,
        ):
            self.assertFalse(self.client.get("/api/marketplace/default").json()["configured"])
            response = self.client.post("/api/marketplace/default")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(response.json()["configured"])
            self.assertTrue(response.json()["default"])
            self.assertContains(self.client.get("/inside?section=settings"), "data-default-marketplace")
            self.assertTrue((data / "marketplace/trusted-keys.json").is_file())
            configured = (data / ".env").read_text()
            self.assertIn("GRAVEWRIGHT_MARKETPLACE_URL", configured)
            self.assertIn("GRAVEWRIGHT_MARKETPLACE_KEYS_FILE", configured)

        player = User.objects.create_user(email="settings-player@example.test", name="Player")
        self.client.force_login(player)
        self.assertEqual(self.client.get("/api/marketplace/default").status_code, 403)
        self.assertNotContains(self.client.get("/inside?section=settings"), "data-default-marketplace")

    def test_signed_package_type_must_be_supported_and_match_manifest(self):
        record, raw = self.release(type='module')
        self.assertEqual(host().install(record, raw)['id'], record['id'])
        for kind in ['system', 'unknown']:
            record, raw = self.release(type=kind)
            with self.subTest(kind=kind), self.assertRaises(ModuleFailure):
                host().install(record, raw)

    def test_tags_are_free_text_bounded_and_authenticated(self):
        record, _ = self.release(tags=['Tradução', 'Tools and controls'])
        host().verify(record)
        record['tags'].append('Changed')
        with self.assertRaises(ModuleFailure):
            host().verify(record)
        for tags in ['text', [1], [''], [' x'], ['x', 'X'], ['x'*65], [str(i) for i in range(25)]]:
            with self.subTest(tags=tags), self.assertRaises(ModuleFailure):
                host().verify(self.release(tags=tags)[0])
