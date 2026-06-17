"""Serve a package's declared front-end assets.

Only files whitelisted by the manifest are served, and only for enabled
packages — see :class:`app.engine.sdk.package_asset_service.PackageAssetService`.
"""

from __future__ import annotations

from litestar import get
from litestar.params import FromPath
from litestar.response import File, Response

from app.engine.sdk.package_asset_service import PackageAssetService


@get("/sdk/packages/{package_id:str}/asset/{asset_path:path}", sync_to_thread=False)
def serve_package_asset(
    package_id: FromPath[str],
    asset_path: FromPath[str],
    package_asset_service: PackageAssetService,
) -> File | Response[bytes]:
    resolved = package_asset_service.resolve(str(package_id), str(asset_path))
    if resolved is None:
        return Response(b"", status_code=404)
    path, content_type = resolved
    return File(
        path=path,
        media_type=content_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=300"},
    )
