"""Persistent releases, per-table activation, JSON namespaces and mount leases.

Archives/assets live under MEDIA_ROOT; these rows track their authenticated
identity and active contexts rather than storing executable package code.
"""

from django.conf import settings
from django.db import models


class Package(models.Model):
    """An immutable module ID/version paired with its digest and signed record."""
    module_id = models.CharField(max_length=120)
    version = models.CharField(max_length=60)
    digest = models.CharField(max_length=64)
    manifest = models.JSONField()
    record = models.JSONField()
    revoked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module_id", "version"], name="module_unique_release"
            )
        ]


class ModuleSet(models.Model):
    """Exact releases and preferred UI replacements selected for one campaign."""
    campaign = models.OneToOneField(
        "gravewright_campaigns.Campaign", primary_key=True, on_delete=models.CASCADE
    )
    revision = models.CharField(max_length=32, default="0")
    modules = models.JSONField(default=dict)
    replacements = models.JSONField(default=dict)


class ModuleValue(models.Model):
    """A revisioned JSON value; an empty user_key identifies shared table storage."""
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    module_id = models.CharField(max_length=120)
    user_key = models.CharField(max_length=36, blank=True)
    key = models.CharField(max_length=240)
    value = models.JSONField()
    revision = models.CharField(max_length=32)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "module_id", "user_key", "key"],
                name="module_unique_value",
            )
        ]


class ContextLease(models.Model):
    """Expiring server-side authority to use one active module mount and scene."""
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module_id = models.CharField(max_length=120)
    mount = models.CharField(max_length=128)
    revision = models.CharField(max_length=32)
    scene = models.ForeignKey(
        "gravewright_maps.Scene", null=True, on_delete=models.CASCADE
    )
    closed = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user", "module_id", "mount"],
                name="module_unique_lease",
            )
        ]
