"""Read-only campaign catalog shared by journal reference editors and SDKs."""

from gravewright.table import resource_links
from .services import member


def resources(campaign_id, user_id, *, query='', kinds=None, limit=80, scene_id=None):
    return resource_links.catalog(member(campaign_id, user_id), query=query, kinds=kinds,
                                  limit=limit, scene_id=scene_id)


def resolve(campaign_id, user_id, reference):
    return {'resource': resource_links.resolve(member(campaign_id, user_id), reference)}
