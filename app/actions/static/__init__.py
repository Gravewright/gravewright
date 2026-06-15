from __future__ import annotations

from app.actions.static.chrome_devtools import chrome_devtools_probe
from app.actions.static.favicon import favicon


route_handlers = [
    favicon,
    chrome_devtools_probe,
]
