from django.apps import AppConfig


class JournalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "gravewright.journals"
    label = "gravewright_journals"

    def ready(self):
        from django.db.models.signals import post_delete
        from .models import Asset, Revision
        from .history import release_files, retained_asset_names
        def remove_file(sender, instance, **kwargs):
            storage, name = instance.file.storage, instance.file.name
            if name:
                release_files({name}, storage)
        def remove_retained_files(sender, instance, **kwargs):
            release_files(retained_asset_names(instance.retained))
        post_delete.connect(remove_file, sender=Asset, weak=False, dispatch_uid='journal_asset_cleanup')
        post_delete.connect(remove_retained_files, sender=Revision, weak=False, dispatch_uid='journal_revision_cleanup')
