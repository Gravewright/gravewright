from __future__ import annotations

from litestar import Request, post
from litestar.response import Redirect


@post("/logout")
async def logout(request: Request) -> Redirect:
    request.clear_session()
    return Redirect(path="/login")
