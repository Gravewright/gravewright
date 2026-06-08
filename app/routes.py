from __future__ import annotations

from app.actions.auth import route_handlers as auth_route_handlers
from app.actions.game import route_handlers as game_route_handlers
from app.actions.inside import route_handlers as inside_route_handlers
from app.actions.static import route_handlers as static_route_handlers


route_handlers = [
    *auth_route_handlers,
    *inside_route_handlers,
    *game_route_handlers,
    *static_route_handlers,
]