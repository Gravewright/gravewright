"""Public combat interface; services own its command boundary."""
from gravewright.combat.services import public_state as state, public_command as command

__all__ = ["state", "command"]
