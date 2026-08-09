from __future__ import annotations

import logging
import random
import re

import pytest

from app.helpers.codes import JOIN_CODE_ALPHABET
from app.helpers.codes import generate_join_code
from app.helpers.codes import generate_removal_code
from app.helpers.codes import hash_join_code
from app.helpers.codes import hash_removal_code
from app.helpers.codes import join_code_hash_matches
from app.helpers.codes import normalize_join_code


JOIN_CODE_RE = re.compile(r"^[A-Z2-9]{4}(?:-[A-Z2-9]{4}){2}$")
TEST_SECRET = "join-code-unit-test-secret-that-is-not-production"


def test_generated_join_codes_have_v1_format_alphabet_and_basic_distribution():
    generated = {generate_join_code() for _ in range(5_000)}
    assert len(generated) == 5_000
    for code in generated:
        assert JOIN_CODE_RE.fullmatch(code)
        assert set(code.replace("-", "")) <= set(JOIN_CODE_ALPHABET)


def test_generation_uses_secrets_not_random(monkeypatch):
    def forbidden(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("random must not be used for join codes")

    monkeypatch.setattr(random, "choice", forbidden)
    assert normalize_join_code(generate_join_code())


@pytest.mark.parametrize(
    "variant",
    [
        "ABCD-EFGH-JKMP",
        "abcd efgh jkmp",
        "  AbCd- EfGh\tJkMp  ",
        "ABCDefghJKMP",
    ],
)
def test_normalization_equivalent_presentations(variant):
    assert normalize_join_code(variant) == "ABCDEFGHJKMP"


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "short",
        "ABCD-EFGH-JKM",
        "ABCD-EFGH-JKMP-X",
        "ABCD-EFGH-JKMI",  # ambiguous I
        "ABCD-EFGH-JKML",  # ambiguous L
        "ABCD-EFGH-JKMO",  # ambiguous O
        "ABCD-EFGH-JKMU",  # ambiguous U
        "ABCD-EFGH-JKM0",
        "ABCD-EFGH-JKM1",
        "ABCD_EFGH_JKMP",
        "ÁBCD-EFGH-JKMP",
    ],
)
def test_invalid_join_codes_are_rejected(invalid):
    with pytest.raises(ValueError):
        normalize_join_code(invalid)


def test_non_string_join_code_is_rejected():
    with pytest.raises(TypeError):
        normalize_join_code(None)  # type: ignore[arg-type]


def test_hash_is_normalized_deterministic_namespaced_and_64_hex_characters():
    first = hash_join_code("ABCD-EFGH-JKMP", secret=TEST_SECRET)
    equivalent = hash_join_code("abcd efgh jkmp", secret=TEST_SECRET)
    different = hash_join_code("ABCD-EFGH-JKMQ", secret=TEST_SECRET)
    other_secret = hash_join_code("ABCD-EFGH-JKMP", secret=f"{TEST_SECRET}-other")

    assert first == equivalent
    assert first != different
    assert first != other_secret
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert join_code_hash_matches("abcd-efgh-jkmp", first, secret=TEST_SECRET)
    assert not join_code_hash_matches("ABCD-EFGH-JKMQ", first, secret=TEST_SECRET)


def test_join_code_plaintext_is_not_logged(caplog):
    code = "ABCD-EFGH-JKMP"
    with caplog.at_level(logging.DEBUG):
        digest = hash_join_code(code, secret=TEST_SECRET)
        assert join_code_hash_matches(code, digest, secret=TEST_SECRET)
    assert code not in "\n".join(record.getMessage() for record in caplog.records)
    assert normalize_join_code(code) not in "\n".join(
        record.getMessage() for record in caplog.records
    )


def test_existing_removal_code_helpers_remain_available():
    code = generate_removal_code()
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", code)
    assert hash_removal_code(code) == hash_removal_code(code.lower())
