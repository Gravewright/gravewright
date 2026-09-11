from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "gravewright.chat"
    label = "gravewright_chat"

    def ready(self):
        from . import card_attachments  # Register file cleanup.
