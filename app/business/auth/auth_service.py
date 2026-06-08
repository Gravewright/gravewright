from __future__ import annotations

import time
from dataclasses import dataclass
from app.persistence.rows import Row

from app.config import config
from app.contracts.email import EmailSenderContract
from app.helpers.password import hash_password, verify_password
from app.helpers.tokens import create_url_token, hash_url_token
from app.helpers.validators import (
    normalize_email,
    normalize_name,
    validate_email,
    validate_name,
    validate_password,
)
from app.persistence.repositories.auth_attempt_repository import AuthAttemptRepository
from app.persistence.repositories.password_reset_repository import PasswordResetRepository
from app.persistence.repositories.user_repository import UserRepository
from app.persistence.session_store import SQLiteStore


@dataclass(frozen=True)
class AuthResult:
    success: bool
    user: Row | None = None
    error_key: str | None = None


class AuthService:
    def __init__(
        self,
        *,
        email_sender: EmailSenderContract | None = None,
    ) -> None:
        self.email_sender = email_sender
        self.users = UserRepository()
        self.password_resets = PasswordResetRepository()
        self.attempts = AuthAttemptRepository()

    def is_first_user(self) -> bool:
        return self.users.count() == 0

    def is_valid_reset_token(self, token: str) -> bool:
        if not token:
            return False
        return self.password_resets.get_valid_by_hash(hash_url_token(token)) is not None

    def _is_blocked(
        self,
        *,
        action: str,
        attempt_key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> bool:
        since = int(time.time()) - window_seconds

        failures = self.attempts.count_failures_since(
            action=action,
            attempt_key=attempt_key,
            since=since,
        )

        return failures >= max_attempts

    def register(
        self,
        *,
        name: str,
        email: str,
        password: str,
        client_ip: str,
    ) -> AuthResult:
        action = "register"
        attempt_key = client_ip

        if self._is_blocked(
            action=action,
            attempt_key=attempt_key,
            max_attempts=config.auth_register_max_attempts,
            window_seconds=config.auth_register_window_seconds,
        ):
            return AuthResult(
                success=False,
                error_key="auth.errors.too_many_attempts",
            )

        normalized_name = normalize_name(name)
        normalized_email = normalize_email(email)

        if not validate_name(normalized_name):
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_name")

        if not validate_email(normalized_email):
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_email")

        if not validate_password(password):
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_password")

        try:
            user = self.users.create_with_auto_role(
                name=normalized_name,
                email=normalized_email,
                password_hash=hash_password(password),
            )
        except Exception:
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.register_failed")

        self.attempts.clear(action=action, attempt_key=attempt_key)

        return AuthResult(success=True, user=user)

    def login(
        self,
        *,
        email: str,
        password: str,
        client_ip: str,
    ) -> AuthResult:
        normalized_email = normalize_email(email)
        action = "login"
        attempt_key = f"{client_ip}:{normalized_email}"

        if self._is_blocked(
            action=action,
            attempt_key=attempt_key,
            max_attempts=config.auth_login_max_attempts,
            window_seconds=config.auth_login_window_seconds,
        ):
            return AuthResult(
                success=False,
                error_key="auth.errors.too_many_attempts",
            )

        user = self.users.get_by_email(normalized_email)

        if user is None:
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_login")

        if not verify_password(password, user["password_hash"]):
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_login")

        self.attempts.clear(action=action, attempt_key=attempt_key)

        return AuthResult(success=True, user=user)

    async def forgot_password(
        self,
        *,
        email: str,
        client_ip: str,
        reset_base_url: str,
    ) -> None:
        if self.email_sender is None:
            raise RuntimeError("AuthService requires email_sender to send password reset emails")

        normalized_email = normalize_email(email)
        action = "forgot_password"
        attempt_key = f"{client_ip}:{normalized_email}"

        if self._is_blocked(
            action=action,
            attempt_key=attempt_key,
            max_attempts=config.auth_password_reset_max_attempts,
            window_seconds=config.auth_password_reset_window_seconds,
        ):
            return

        self.attempts.record(action=action, attempt_key=attempt_key, success=False)

        user = self.users.get_by_email(normalized_email)

        if user is None:
            return

        raw_token = create_url_token()
        token_hash = hash_url_token(raw_token)

        expires_at = int(time.time()) + config.auth_password_reset_token_ttl_seconds

        self.password_resets.create(
            user_id=user["id"],
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_url = f"{reset_base_url}/reset-password?token={raw_token}"

        await self.email_sender.send_password_reset_email(
            to_email=user["email"],
            reset_url=reset_url,
        )

    def reset_password(
        self,
        *,
        token: str,
        password: str,
        client_ip: str,
    ) -> AuthResult:
        action = "reset_password"
        attempt_key = client_ip

        if self._is_blocked(
            action=action,
            attempt_key=attempt_key,
            max_attempts=config.auth_password_reset_max_attempts,
            window_seconds=config.auth_password_reset_window_seconds,
        ):
            return AuthResult(
                success=False,
                error_key="auth.errors.too_many_attempts",
            )

        if not validate_password(password):
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_password")

        reset = self.password_resets.get_valid_by_hash(hash_url_token(token))

        if reset is None:
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_reset_link")

        user = self.users.get_by_id(reset["user_id"])

        if user is None:
            self.attempts.record(action=action, attempt_key=attempt_key, success=False)
            return AuthResult(success=False, error_key="auth.errors.invalid_reset_link")

        self.users.update_password(
            user_id=user["id"],
            password_hash=hash_password(password),
        )

        self.password_resets.mark_used(reset["id"])
        SQLiteStore.delete_user_sessions(user["id"])
        self.attempts.clear(action=action, attempt_key=attempt_key)

        return AuthResult(success=True, user=user)