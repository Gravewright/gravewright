"""Serve a system's declared UI assets (Sheet API system CSS/JS).

Only files whitelisted in the system manifest's ``system.assets`` block are
served, and only for enabled systems — see
:class:`app.engine.systems.system_asset_service.SystemAssetService`.
"""

from __future__ import annotations

from litestar import get
from litestar.params import FromPath
from litestar.response import File, Response

from app.engine.systems.system_asset_service import SystemAssetService


@get("/systems/{system_id:str}/asset/{asset_path:path}", sync_to_thread=False)
def serve_system_asset(
    system_id: FromPath[str],
    asset_path: FromPath[str],
    system_asset_service: SystemAssetService,
) -> File | Response[bytes]:
    resolved = system_asset_service.resolve(system_id, str(asset_path))
    if resolved is None:
        return Response(b"", status_code=404)
    path, content_type = resolved
    return File(
        path=path,
        media_type=content_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=300"},
    )
