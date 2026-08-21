from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

from app.business.core_update_service import CoreUpdateService


def release(version: str, digest: str = "a" * 64) -> dict:
    return {
        "tag_name": f"v{version}", "name": version, "draft": False,
        "html_url": f"https://github.com/Gravewright/gravewright/releases/tag/v{version}",
        "assets": [{
            "name": f"Gravewright-{version}-win64.zip", "size": 10,
            "digest": f"sha256:{digest}",
            "browser_download_url": f"https://github.com/Gravewright/gravewright/releases/download/v{version}/Gravewright-{version}-win64.zip",
        }],
    }


def test_core_update_uses_current_channel_and_verified_release_asset(tmp_path):
    payload = json.dumps([release("3.0.0-alpha"), release("1.0.0-beta.2")]).encode()
    result = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "core.json",
                               current_version="1.0.0-beta.1").check()
    assert result["status"] == "available"
    assert result["availableVersion"] == "1.0.0-beta.2"
    assert result["artifact"]["sha256"] == "a" * 64


def test_core_update_fails_closed_without_digest(tmp_path):
    payload = json.dumps([release("1.0.0-beta.2", digest="")]).encode()
    result = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "core.json",
                               current_version="1.0.0-beta.1").check()
    assert result["status"] == "failed"
    assert result["errorKey"] == "CORE_RELEASE_CHANNEL_UNAVAILABLE"


def test_core_channel_policy_ignores_newer_other_channels(tmp_path):
    scenarios = [
        ("1.0.0", [release("1.0.1"), release("1.1.0-alpha.3")], "1.0.1"),
        ("1.1.0-beta.1", [release("1.0.2"), release("1.1.0-beta.2"), release("1.2.0-alpha.1")], "1.1.0-beta.2"),
        ("2.0.0-alpha.1", [release("2.0.0-alpha.2"), release("1.9.0-beta.9"), release("3.0.0")], "2.0.0-alpha.2"),
    ]
    for index, (current, releases, expected) in enumerate(scenarios):
        service = CoreUpdateService(fetcher=lambda *_args, value=releases: json.dumps(value).encode(),
                                    cache_path=tmp_path / f"core-{index}.json", current_version=current)
        assert service.check()["availableVersion"] == expected


def test_core_channels_use_debian_style_fallback_without_upward_leaks(tmp_path):
    releases = [release("1.0.1"), release("1.1.0-rc.1"), release("1.2.0-dev.1")]
    payload = json.dumps(releases).encode()
    stable = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "stable.json",
                               current_version="1.0.0", channel="stable").check()
    testing = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "testing.json",
                                current_version="1.0.0", channel="testing").check()
    dev = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "dev.json",
                            current_version="1.0.0", channel="dev").check()
    assert (stable["availableVersion"], stable["resolvedChannel"]) == ("1.0.1", "stable")
    assert (testing["availableVersion"], testing["resolvedChannel"]) == ("1.1.0-rc.1", "testing")
    assert (dev["availableVersion"], dev["resolvedChannel"]) == ("1.2.0-dev.1", "dev")


def test_returning_to_stable_never_offers_an_automatic_core_downgrade(tmp_path):
    payload = json.dumps([release("1.9.0")]).encode()
    result = CoreUpdateService(fetcher=lambda *_: payload, cache_path=tmp_path / "core.json",
                               current_version="2.0.0-dev.4", channel="stable").check()
    assert result["status"] == "ahead-of-channel"
    assert result["artifact"] is None
    assert result["requiresBackup"] is False


def test_catalog_controls_which_core_channels_are_published(tmp_path):
    registry = b'''version = 2
packages = []
[core]
id = "gravewright"
name = "Gravewright"
enabled = true
repository = "https://github.com/Gravewright/gravewright"
releases = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"
[core.channels.dev]
enabled = true
'''
    payload = json.dumps([release("2.0.0-dev.2")]).encode()
    service = CoreUpdateService(fetcher=lambda *_: payload, registry_fetcher=lambda *_: registry,
        registry_cache_path=tmp_path / "marketplace.toml",
        cache_path=tmp_path / "dev.json", current_version="2.0.0-dev.1", channel="dev")
    service.catalog_bound = True
    result = service.check()
    assert result["status"] == "available"
    assert result["resolvedChannel"] == "dev"

    stable = CoreUpdateService(fetcher=lambda *_: payload, registry_fetcher=lambda *_: registry,
        registry_cache_path=tmp_path / "marketplace.toml",
        cache_path=tmp_path / "stable.json", current_version="1.0.0", channel="stable")
    stable.catalog_bound = True
    assert stable.check()["errorKey"] == "CORE_RELEASE_CHANNEL_UNAVAILABLE"


def test_core_distinguishes_unavailable_registry_from_missing_core_entry(tmp_path):
    unavailable = CoreUpdateService(
        registry_fetcher=lambda *_: (_ for _ in ()).throw(OSError("offline")),
        registry_cache_path=tmp_path / "missing-marketplace.toml",
        cache_path=tmp_path / "unavailable.json",
        current_version="1.0.0",
    )
    unavailable.catalog_bound = True
    assert unavailable.check()["errorKey"] == "CORE_MARKETPLACE_REGISTRY_UNAVAILABLE"

    no_core = b"version = 2\npackages = []\n"
    missing_entry = CoreUpdateService(
        registry_fetcher=lambda *_: no_core,
        registry_cache_path=tmp_path / "marketplace.toml",
        cache_path=tmp_path / "missing-entry.json",
        current_version="1.0.0",
    )
    missing_entry.catalog_bound = True
    assert missing_entry.check()["errorKey"] == "CORE_MARKETPLACE_ENTRY_UNAVAILABLE"


def test_core_rejects_draft_wrong_asset_duplicate_asset_and_bad_digest(tmp_path):
    documents = []
    draft = release("1.0.1"); draft["draft"] = True; documents.append([draft])
    wrong = release("1.0.1"); wrong["assets"][0]["name"] = "other.zip"; documents.append([wrong])
    duplicate = release("1.0.1"); duplicate["assets"].append(dict(duplicate["assets"][0])); documents.append([duplicate])
    bad = release("1.0.1"); bad["assets"][0]["digest"] = "sha256:" + "z" * 64; documents.append([bad])
    for index, document in enumerate(documents):
        result = CoreUpdateService(fetcher=lambda *_args, value=document: json.dumps(value).encode(),
                                   cache_path=tmp_path / f"bad-{index}.json",
                                   current_version="1.0.0").check()
        assert result["status"] == "failed"


def test_core_cache_corruption_expiry_and_channel_change_are_unchecked(tmp_path):
    cache = tmp_path / "core.json"
    cache.write_text("broken", encoding="utf-8")
    assert CoreUpdateService(cache_path=cache, current_version="1.0.0").status()["status"] == "unchecked"
    cache.write_text(json.dumps({"status": "current", "currentVersion": "1.0.0", "channel": "stable",
                                 "checkedAt": int(time.time()) - 100_000}), encoding="utf-8")
    assert CoreUpdateService(cache_path=cache, current_version="1.0.0").status()["status"] == "unchecked"
    cache.write_text(json.dumps({"status": "current", "currentVersion": "1.0.0", "channel": "stable",
                                 "checkedAt": int(time.time())}), encoding="utf-8")
    assert CoreUpdateService(cache_path=cache, current_version="1.0.0-beta.1").status()["status"] == "unchecked"


def test_two_core_checks_write_one_valid_atomic_cache(tmp_path):
    cache = tmp_path / "core.json"
    payload = json.dumps([release("1.0.1")]).encode()
    def check():
        return CoreUpdateService(fetcher=lambda *_: payload, cache_path=cache,
                                 current_version="1.0.0").check()["status"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _value: check(), range(2))) == ["available", "available"]
    assert json.loads(cache.read_text(encoding="utf-8"))["availableVersion"] == "1.0.1"
    assert not list(tmp_path.glob("*.tmp-*"))
