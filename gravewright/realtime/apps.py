from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    name = "gravewright.realtime"
    label = "gravewright_realtime"

    def ready(self):
        # Changes that can revoke socket access invalidate cached authorizations.
        from . import signals  # noqa: F401
