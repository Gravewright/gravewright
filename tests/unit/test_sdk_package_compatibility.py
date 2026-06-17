"""Phase 3 — compatibility and versioning.

Pin reliable SemVer-ish ordering (including alpha/beta/rc/final pre-releases),
the minimum/maximum/verified window semantics, and stable error codes.
"""

from __future__ import annotations

from app.engine.sdk.package_compatibility import (
    COMPAT_COMPATIBLE,
    COMPAT_INCOMPATIBLE,
    COMPAT_UNVERIFIED,
    compatibility_error,
    compute_compatibility_status,
    version_key,
)


def _status(minimum="", verified="", maximum="", engine="1.0.0"):
    return compute_compatibility_status(
        minimum=minimum, verified=verified, maximum=maximum, engine_version=engine
    )


def test_prerelease_ordering_alpha_beta_rc_final():
    assert version_key("1.0.0-alpha.1") < version_key("1.0.0-alpha.2")
    assert version_key("1.0.0-alpha.2") < version_key("1.0.0-beta.1")
    assert version_key("1.0.0-beta.1") < version_key("1.0.0-rc.1")
    assert version_key("1.0.0-rc.1") < version_key("1.0.0")
    # And the full chain is strictly increasing.
    chain = ["1.0.0-alpha.1", "1.0.0-alpha.2", "1.0.0-beta.1", "1.0.0-rc.1", "1.0.0"]
    keys = [version_key(v) for v in chain]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_minimum_blocks_old_sdk():
    assert _status(minimum="1.2.0", engine="1.1.0") == COMPAT_INCOMPATIBLE


def test_maximum_blocks_new_sdk():
    assert _status(maximum="1.0.0", engine="2.0.0") == COMPAT_INCOMPATIBLE


def test_verified_exact_match_is_compatible():
    assert _status(verified="1.0.0", engine="1.0.0") == COMPAT_COMPATIBLE
    assert (
        _status(verified="1.0.0-rc.1", engine="1.0.0-rc.1", maximum="1.x")
        == COMPAT_COMPATIBLE
    )


def test_in_range_but_not_verified_is_unverified():
    assert (
        _status(minimum="1.0.0", verified="1.2.0", maximum="1.x", engine="1.1.0")
        == COMPAT_UNVERIFIED
    )


def test_wildcard_major_range():
    # 1.x admits any 1.* release/pre-release but blocks 2.0.0.
    assert _status(maximum="1.x", engine="1.9.9") != COMPAT_INCOMPATIBLE
    assert _status(maximum="1.x", engine="1.0.0-alpha.1") != COMPAT_INCOMPATIBLE
    assert _status(maximum="1.x", engine="2.0.0") == COMPAT_INCOMPATIBLE


def test_incompatible_version_returns_stable_error_code():
    too_low = compatibility_error(
        minimum="1.2.0", verified="", maximum="", engine_version="1.1.0"
    )
    assert too_low is not None
    assert too_low.code == "sdk.compatibility.version_too_low"

    too_high = compatibility_error(
        minimum="", verified="", maximum="1.0.0", engine_version="2.0.0"
    )
    assert too_high is not None
    assert too_high.code == "sdk.compatibility.version_too_high"

    # Compatible / unverified windows produce no error.
    assert (
        compatibility_error(
            minimum="1.0.0", verified="1.0.0", maximum="1.x", engine_version="1.0.0"
        )
        is None
    )
