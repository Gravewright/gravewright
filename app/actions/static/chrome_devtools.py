from __future__ import annotations

from litestar import get
from litestar.response import Response


@get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools_probe() -> Response[bytes]:
    """Silence Chrome DevTools' local app-specific probe.

    Chromium-based browsers may request this development-only URL when DevTools
    is open. Returning 204 keeps the server logs clean without serving data.
    """

    return Response(content=b"", media_type="application/json", status_code=204)
