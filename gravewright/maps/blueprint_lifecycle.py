"""Explicit scene-object destruction, separate from authored data cleanup."""

from .blueprint_actions import intelligent
from .blueprint_runtime import MAX_CHAIN_OPERATIONS, automation_paused, element_state, operate
from .blueprints import has_event_path
from .models import SceneObject
from .services import MapError, manage


MAX_DESTROY_HANDLERS = MAX_CHAIN_OPERATIONS


def destroy_objects(scene, who, rows, *, context=None, skip_unbound_teleport=False):
    """Run bounded hooks before removing a command's entire validated selection.

    The caller owns authorization, object revisions, its transaction and receipt.
    ORM cleanup for assets, source regeneration or campaign deletion deliberately
    does not use this function. Pending work belongs to its native owner and is
    removed by the owner's foreign-key cascade, including work its hook created.
    """
    manage(who)
    selected = {str(row.pk): row for row in rows}
    if any(row.scene_id != scene.pk for row in selected.values()):
        raise MapError("Choose an object from this scene.")
    ordered = sorted(selected.values(), key=lambda row: (row.created_at, str(row.pk)))
    handlers = [row for row in ordered if intelligent(row) and has_event_path(row.data.get("blueprint"), "destroy")]
    if not automation_paused(scene):
        if len(handlers) > MAX_DESTROY_HANDLERS:
            raise MapError("Delete at most 32 objects with On destroy handlers at a time.")
        for row in handlers:
            # Earlier handlers may change another selected owner's live state.
            row.refresh_from_db(fields=["data", "version"])
            try:
                operate(scene, who, row, element_state(row), interact=False, trigger_event="destroy",
                        context=context, skip_unbound_teleport=skip_unbound_teleport)
            except MapError as error:
                if hasattr(error, "automation_run"):
                    error.automation_run["elementId"] = str(row.pk)
                raise
    from .blueprint_delays import cancel_owned_delays
    cancelled_waits = cancel_owned_delays(scene, selected)
    from .torches import delete_group
    for row in ordered:
        if row.kind == "images" and isinstance(row.data.get("torch"), dict):
            delete_group(row)
    SceneObject.objects.filter(scene=scene, pk__in=selected).delete()
    return {"removedIds": list(selected), "cancelledWaits": cancelled_waits}
