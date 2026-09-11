from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import EntryAsset, Entry


@receiver(post_delete, sender=EntryAsset)
def remove_snapshot_file(sender, instance, **kwargs):
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name))

@receiver(post_delete, sender=Entry)
def remove_document_bundle(sender, instance, **kwargs):
    if instance.bundle:
        storage,name=instance.bundle.storage,instance.bundle.name
        transaction.on_commit(lambda:storage.delete(name))
