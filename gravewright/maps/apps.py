from django.apps import AppConfig


class MapsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gravewright.maps"
    label = "gravewright_maps"

    def ready(self):
        from django.db import transaction
        from django.db.models.signals import post_delete
        from .models import Tile, MapAsset

        def remove_tile(sender, instance, **kwargs):
            storage, name = instance.file.storage, instance.file.name
            transaction.on_commit(lambda: storage.delete(name))

        post_delete.connect(
            remove_tile, sender=Tile, weak=False, dispatch_uid="maps.delete_tile_file"
        )

        post_delete.connect(
            remove_tile,
            sender=MapAsset,
            weak=False,
            dispatch_uid="maps.delete_asset_file",
        )
