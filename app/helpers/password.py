from __future__ import annotations

import base64
import hashlib
import secrets


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)

    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_BYTES,
    )

    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _b64encode(salt),
            _b64encode(key),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected_key = password_hash.split("$", 5)

        if algorithm != "scrypt":
            return False

        key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=KEY_BYTES,
        )

        return secrets.compare_digest(key, _b64decode(expected_key))
    except Exception:
        return False