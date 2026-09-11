"""Public exception identities, preserved from the underlying services."""
from gravewright.accounts.services import AuthError
from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError
from gravewright.dice.engine import RollError

__all__ = ['AuthError', 'JournalError', 'MapError', 'RollError']
