from __future__ import annotations

from pathlib import Path

from litestar import Litestar
from litestar.config.allowed_hosts import AllowedHostsConfig
from litestar.config.compression import CompressionConfig
from litestar.config.csrf import CSRFConfig
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.logging import LoggingConfig
from litestar.middleware import DefineMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.openapi import OpenAPIConfig
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig

from app.actions.service_dependencies import SERVICE_DEPENDENCIES
from app.config import config
from app.helpers.auth import auth_exception_handler, provide_current_user, provide_session
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.persistence.session_store import SQLiteStore
from app.routes import route_handlers


BASE_DIR = Path(__file__).resolve().parent

                                                                                    
                                                             
_AUTH_EXCLUDE = ["^/static", "^/sdk/packages/[^/]+/asset/", "^/schema"]

                                                                                        
_session_config = ServerSideSessionConfig(
    key=config.session_cookie_name,
    max_age=config.session_max_age,
    secure=config.session_cookie_secure,
    httponly=config.session_cookie_httponly,
    samesite=config.session_cookie_samesite,
    domain=config.session_cookie_domain,
    exclude=["^/static", "^/sdk/packages/[^/]+/asset/", "^/schema"],
)


app = Litestar(
    route_handlers=[
        *route_handlers,
        create_static_files_router(
            path="/static",
            directories=[BASE_DIR / "static"],
            include_in_schema=False,
        ),
    ],
    stores={"sessions": SQLiteStore()},
    middleware=[
        _session_config.middleware,
        DefineMiddleware(AuthenticationMiddleware, exclude=_AUTH_EXCLUDE),
        DefineMiddleware(SecurityHeadersMiddleware),
    ],
    dependencies={
        "current_user": Provide(provide_current_user, sync_to_thread=False),
        "session": Provide(provide_session, sync_to_thread=False),
        **SERVICE_DEPENDENCIES,
    },
    exception_handlers={NotAuthorizedException: auth_exception_handler},
    csrf_config=CSRFConfig(
        secret=config.session_secret,
        cookie_secure=config.session_cookie_secure,
        cookie_samesite=config.session_cookie_samesite,
        exclude=["^/static", "^/sdk/packages/[^/]+/asset/", "^/schema"],
    ),
    template_config=TemplateConfig(
        directory=BASE_DIR / "templates",
        engine=JinjaTemplateEngine,
    ),
    compression_config=CompressionConfig(backend="gzip"),
    logging_config=LoggingConfig(
                                                                                  
                                                                                    
                                                                  
        log_exceptions="debug",
        configure_root_logger=True,
    ),
    openapi_config=OpenAPIConfig(
        title=config.app_name,
        version=config.gravewright_version,
    ),
    allowed_hosts=(
        AllowedHostsConfig(allowed_hosts=list(config.allowed_hosts))
        if config.allowed_hosts
        else None
    ),
    debug=config.app_debug,
)
