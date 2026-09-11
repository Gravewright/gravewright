"""Public chat interface; implementations remain in the owning services."""
from gravewright.chat.services import history, send, remove

__all__ = ['history', 'send', 'remove']
