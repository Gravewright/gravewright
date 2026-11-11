"""Invalidate cached socket authorizations when access can change.

A socket may reuse its last authorization for a short time (see
TableConsumer.authorized). Every change that can revoke access calls ``revoke``:
after commit it advances this process's epoch, which every socket in the process
checks synchronously, and sends ``room.access`` so sockets in other processes
revalidate at once. The epoch only advances after commit, so a socket cannot
revalidate against the old state and keep that answer.
"""

import logging
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)
_epoch = 0


def epoch():
    return _epoch


def user_group(user_id):
    return f"user.{UUID(str(user_id)).hex}"


def revoke(campaign_id=None, user_ids=()):
    """Make every socket of these campaigns and users revalidate after commit."""
    user_ids = [user_id for user_id in user_ids if user_id is not None]

    def publish():
        global _epoch
        _epoch += 1
        layer = get_channel_layer()
        if layer is None:
            return
        groups = [user_group(user_id) for user_id in user_ids]
        if campaign_id is not None:
            groups.append(f"table.{UUID(str(campaign_id)).hex}")
        for group in groups:
            try:
                async_to_sync(layer.group_send)(group, {"type": "room.access"})
            except Exception:  # noqa: BLE001 - the epoch already covers this process
                logger.exception("Could not notify other processes about an access change")
    transaction.on_commit(publish, robust=True)
