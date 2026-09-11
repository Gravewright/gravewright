"""Host accounts, authentication attempt windows and per-user preferences."""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Email-authenticated identity; the database permits at most one host owner."""
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        PARTICIPANT = "participant", "Participant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, validators=[MinLengthValidator(2)])
    email = models.EmailField(max_length=254, unique=True)
    role = models.CharField(max_length=11, choices=Role, default=Role.PARTICIPANT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_unique"),
            models.UniqueConstraint(
                fields=["role"], condition=models.Q(role="owner"),
                name="accounts_single_owner",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["owner", "participant"]),
                name="accounts_valid_role",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = type(self).objects.normalize_email(self.email)
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class AuthAttempt(models.Model):
    """Shared, database-backed attempt window; contains no raw IP addresses."""

    key = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField(default=0)


class UserPreference(models.Model):
    """Personal display preferences, independent of campaign permissions."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True,
                                related_name='preferences')
    ping_color = models.CharField(max_length=7, default='#f2c679')
