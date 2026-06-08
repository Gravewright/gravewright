from __future__ import annotations

import re


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def validate_name(name: str) -> bool:
    return 2 <= len(name) <= 80


def validate_password(password: str) -> bool:
    return len(password) >= 8