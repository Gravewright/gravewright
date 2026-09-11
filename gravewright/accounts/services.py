"""Account setup, authentication throttles and database-backed session rotation.

Host owner status is distinct from a campaign's GM membership. HTTP views validate
forms before invoking these functions; AuthError carries transport error metadata."""

from contextlib import contextmanager
from datetime import timedelta
from math import ceil
from threading import BoundedSemaphore

from gravewright.accounts.client_ip import client_ip
from django.conf import settings
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AuthAttempt, User


class AuthError(Exception):
    def __init__(self, code, status=400, retry_after=None):
        self.code, self.status, self.retry_after = code, status, retry_after
        super().__init__(code)


_hash_slots = BoundedSemaphore(4)


@contextmanager
def password_capacity():
    """Bound concurrent expensive password hashing within this server process."""
    if not _hash_slots.acquire(blocking=False):
        raise AuthError("server_busy", 503)
    try:
        yield
    finally:
        _hash_slots.release()


def configured():
    return User.objects.filter(role=User.Role.OWNER).exists()


def public_account(user):
    return {"name": user.name, "email": user.email, "role": user.role}


def reserve_attempt(request):
    """Consume a shared login/setup attempt using a keyed hash of the client IP."""
    now = timezone.now()
    key = salted_hmac("gravewright.auth.attempt", client_ip(request),
                      algorithm="sha256").hexdigest()
    with transaction.atomic():
        AuthAttempt.objects.filter(expires_at__lte=now).delete()
        if not AuthAttempt.objects.filter(pk=key).exists() and AuthAttempt.objects.count() >= 5000:
            raise AuthError("too_many_attempts", 429, settings.GRAVEWRIGHT_AUTH_WINDOW_SECONDS)
        attempt, _ = AuthAttempt.objects.select_for_update().get_or_create(
            key=key, defaults={"expires_at": now + timedelta(seconds=settings.GRAVEWRIGHT_AUTH_WINDOW_SECONDS)}
        )
        if attempt.count >= settings.GRAVEWRIGHT_AUTH_MAX_ATTEMPTS:
            raise AuthError("too_many_attempts", 429,
                            max(1, ceil((attempt.expires_at - now).total_seconds())))
        attempt.count += 1
        attempt.save(update_fields=["count"])


def start_session(request, user):
    """Discard the old session key and persist a newly authenticated session."""
    # Rotate even when signing in to the same account, invalidating the old key.
    request.session.flush()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.set_expiry(timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE))
    request.session.save()


def register(request, data, *, owner=False):
    """Create a validated account and session, enforcing the one-owner bootstrap."""
    if owner and configured():
        raise AuthError("owner_already_configured", 409)
    if not owner and not configured():
        raise AuthError("setup_required", 409)
    user = User(name=data["name"], email=data["email"],
                role=User.Role.OWNER if owner else User.Role.PARTICIPANT)
    with password_capacity():
        user.set_password(data["password"])
    try:
        with transaction.atomic():
            if owner and configured():
                raise AuthError("owner_already_configured", 409)
            user.save(force_insert=True)
            start_session(request, user)
    except IntegrityError:
        if owner and configured():
            raise AuthError("owner_already_configured", 409) from None
        if User.objects.filter(email__iexact=data["email"]).exists():
            raise AuthError("email_already_registered", 409) from None
        raise
    return user


def sign_in(request, data):
    with password_capacity():
        user = authenticate(request, email=data["email"], password=data["password"])
    if user is None:
        raise AuthError("invalid_credentials", 401)
    with transaction.atomic():
        start_session(request, user)
    return user


def update_account(request, data, *, change_password=False):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if change_password:
            with password_capacity():
                if not user.check_password(data["currentPassword"]):
                    raise AuthError("invalid_credentials", 401)
                user.set_password(data["newPassword"])
        user.name = data["name"]
        user.save(update_fields=["name", "password"] if change_password else ["name"])
        if change_password:
            # Other sessions fail Django's session-auth-hash check on next use.
            update_session_auth_hash(request, user)
            request.session.save()
        request.user = user
    return user
