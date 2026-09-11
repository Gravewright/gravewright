from django.apps import AppConfig


class JournalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "gravewright.journals"
    label = "gravewright_journals"

    def ready(self):
        from django.db.models.signals import post_delete
        from django.db import transaction
        from .models import Asset
        def remove_file(sender, instance, **kwargs):
            storage, name = instance.file.storage, instance.file.name
            if name:
                transaction.on_commit(lambda: storage.delete(name))
        post_delete.connect(remove_file, sender=Asset, weak=False, dispatch_uid='journal_asset_cleanup')
