"""Serve a module's declared UI assets."""

from __future__ import annotations

from litestar import get
from litestar.params import FromPath
from litestar.response import File, Response

from app.engine.modules.module_asset_service import ModuleAssetService


@get("/modules/{module_id:str}/asset/{asset_path:path}", sync_to_thread=False)
def serve_module_asset(
    module_id: FromPath[str],
    asset_path: FromPath[str],
    module_asset_service: ModuleAssetService,
) -> File | Response[bytes]:
    resolved = module_asset_service.resolve(module_id, str(asset_path))
    if resolved is None:
        return Response(b"", status_code=404)
    path, content_type = resolved
    return File(
        path=path,
        media_type=content_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=300"},
    )
