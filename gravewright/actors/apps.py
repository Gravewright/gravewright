from django.apps import AppConfig
from django.db import transaction
from django.db.models.signals import post_delete


class ActorsConfig(AppConfig):
    name = "gravewright.actors"
    label = "gravewright_actors"

    def ready(self):
        from .models import Asset

        def remove_file(sender, instance, **kwargs):
            if instance.file:
                storage, name = instance.file.storage, instance.file.name
                transaction.on_commit(lambda: storage.delete(name))

        post_delete.connect(
            remove_file, sender=Asset, weak=False, dispatch_uid="actors.delete_asset"
        )
