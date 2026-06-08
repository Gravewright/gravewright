from __future__ import annotations

from pathlib import Path

from litestar import get
from litestar.response import Response


FAVICON_PATH = Path(__file__).resolve().parents[3] / "static" / "icons" / "icon.svg"


@get("/favicon.ico")
async def favicon() -> Response[bytes]:
    return Response(
        content=FAVICON_PATH.read_bytes(),
        media_type="image/svg+xml",
    )
