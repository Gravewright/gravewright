from __future__ import annotations

from app.actions.static.chrome_devtools import chrome_devtools_probe
from app.actions.static.favicon import favicon
from app.actions.static.system_assets import serve_system_asset
from app.actions.static.module_assets import serve_module_asset


route_handlers = [
    favicon,
    chrome_devtools_probe,
    serve_system_asset,
    serve_module_asset,
]