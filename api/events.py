"""Public events interface; implementations remain in the owning services."""
from gravewright.table.events import Change, resource_changed

__all__ = ['Change', 'resource_changed']
