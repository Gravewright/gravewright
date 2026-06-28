from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.helpers.env import PROJECT_ROOT, env_bool, env_int, env_str


_DEFAULT_TUNNEL_ALLOWED_HOSTS = (
    "*.trycloudflare.com",
    "*.ngrok-free.app",
    "*.ngrok.io",
    "*.loca.lt",
    "*.serveo.net",
)


def _host_matches_pattern(host: str, pattern: str) -> bool:
    host = host.lower().strip().rstrip(".")
    pattern = pattern.lower().strip().rstrip(".")
    if not host or not pattern:
        return False
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return host.endswith(suffix) and host != pattern[2:]
    return host == pattern


def _resolve_tunnel_allowed_hosts(app_env: str) -> tuple[str, ...]:
    raw = env_str("TUNNEL_ALLOWED_HOSTS", "").strip()
    if raw:
        return tuple(host.strip() for host in raw.split(",") if host.strip())
    if app_env == "production":
        return ()
    return _DEFAULT_TUNNEL_ALLOWED_HOSTS


def _resolve_allowed_hosts(app_env: str) -> tuple[str, ...]:
    hosts = [*_csv("ALLOWED_HOSTS"), *_resolve_tunnel_allowed_hosts(app_env)]
    resolved: list[str] = []
    seen: set[str] = set()
    for host in hosts:
        normalized = host.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        resolved.append(normalized)
        seen.add(key)
    return tuple(resolved)


def _resolve_ws_allowed_origins(allowed_hosts: tuple[str, ...]) -> tuple[str, ...]:
    """Origins accepted on the realtime WebSocket handshake.

    Explicit ``WS_ALLOWED_ORIGINS`` wins; otherwise we derive ``http`` and
    ``https`` origins from ``ALLOWED_HOSTS``. An empty result means "not
    configured" and the guard falls back to allow-all (development).
    """
    explicit = tuple(
        o.strip().rstrip("/")
        for o in env_str("WS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    )
    if explicit:
        return explicit

    derived: list[str] = []
    for host in allowed_hosts:
        if "://" in host:
            derived.append(host.rstrip("/"))
            continue
        derived.append(f"https://{host}")
        derived.append(f"http://{host}")
    return tuple(derived)


def _resolve_database_url() -> str:
    """SQLAlchemy URL for the application database.

    Defaults to the bundled SQLite file (absolute path, so it is independent of
    the process working directory). Override with ``DATABASE_URL`` to point at
    PostgreSQL (the supported production backend).
    """
    raw = env_str("DATABASE_URL", "").strip()
    if raw:
        return raw
    sqlite_path = (PROJECT_ROOT / "storage" / "gravewright.sqlite3").resolve()
    return f"sqlite:///{sqlite_path}"


def _resolve_data_dir() -> str:
    """Root folder for installable SDK packages.

    Decoupled from the project so it can live anywhere: set ``GRAVEWRIGHT_DATA_DIR``
    to an absolute path (or one relative to the project root). Defaults to
    ``<project>/data``.
    """
    raw = env_str("GRAVEWRIGHT_DATA_DIR", "").strip()
    if not raw:
        return str((PROJECT_ROOT / "data").resolve())
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())


def _csv(key: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in env_str(key, "").split(",") if item.strip())


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.split(":", 1)[0].lower().startswith("sqlite")


def _is_mysql_url(database_url: str) -> bool:
    scheme = database_url.split(":", 1)[0].lower()
    return scheme.startswith("mysql") or scheme.startswith("mariadb")


def _public_base_url_host(public_base_url: str) -> tuple[str, str]:
    parsed = urlsplit(public_base_url)
    hostname = (parsed.hostname or "").lower()
    netloc = (parsed.netloc or "").lower()
    return hostname, netloc


def _allowed_host_matches(public_base_url: str, allowed_hosts: tuple[str, ...]) -> bool:
    hostname, netloc = _public_base_url_host(public_base_url)
    if not hostname:
        return False
    for allowed_host in allowed_hosts:
        normalized = allowed_host.lower().strip()
        if _host_matches_pattern(hostname, normalized):
            return True
        if _host_matches_pattern(netloc, normalized):
            return True
    return False


def _validate_positive_int(name: str, value: int) -> None:
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")


def _validate_config(cfg: "AppConfig") -> None:
    positive_values = {
        "SESSION_MAX_AGE": cfg.session_max_age,
        "AUTH_LOGIN_MAX_ATTEMPTS": cfg.auth_login_max_attempts,
        "AUTH_LOGIN_WINDOW_SECONDS": cfg.auth_login_window_seconds,
        "AUTH_LOGIN_BLOCK_SECONDS": cfg.auth_login_block_seconds,
        "AUTH_REGISTER_MAX_ATTEMPTS": cfg.auth_register_max_attempts,
        "AUTH_REGISTER_WINDOW_SECONDS": cfg.auth_register_window_seconds,
        "AUTH_PASSWORD_RESET_MAX_ATTEMPTS": cfg.auth_password_reset_max_attempts,
        "AUTH_PASSWORD_RESET_WINDOW_SECONDS": cfg.auth_password_reset_window_seconds,
        "AUTH_PASSWORD_RESET_TOKEN_TTL_SECONDS": cfg.auth_password_reset_token_ttl_seconds,
        "WS_MAX_MESSAGE_BYTES": cfg.ws_max_message_bytes,
        "WS_COMMANDS_PER_SECOND": cfg.ws_commands_per_second,
        "WS_BURST_COMMANDS": cfg.ws_burst_commands,
        "SCENE_VIEWPORT_MAX_WIDTH_CHUNKS": cfg.scene_viewport_max_width_chunks,
        "SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS": cfg.scene_viewport_max_height_chunks,
        "SCENE_VIEWPORT_MAX_AREA_CHUNKS": cfg.scene_viewport_max_area_chunks,
        "SCENE_VIEWPORT_MAX_KNOWN_CHUNKS": cfg.scene_viewport_max_known_chunks,
        "SCENE_VIEWPORT_MAX_LAYERS": cfg.scene_viewport_max_layers,
        "FOG_MAX_OPS_PER_COMMAND": cfg.fog_max_ops_per_command,
        "FOG_MAX_POLYGON_POINTS": cfg.fog_max_polygon_points,
        "FOG_MAX_COORDINATE_ABS": cfg.fog_max_coordinate_abs,
        "TOKEN_CREATE_MANY_MAX": cfg.token_create_many_max,
        "BOARD_MARKERS_MAX_PER_SCENE": cfg.board_markers_max_per_scene,
        "BOARD_MEASUREMENTS_MAX_PER_USER": cfg.board_measurements_max_per_user,
        "MAP_UPLOAD_MAX_BYTES": cfg.map_upload_max_bytes,
        "MAP_IMAGE_MAX_WIDTH": cfg.map_image_max_width,
        "MAP_IMAGE_MAX_HEIGHT": cfg.map_image_max_height,
        "MAP_TILE_SIZE": cfg.map_tile_size,
        "MAP_MAX_TILE_COUNT": cfg.map_max_tile_count,
    }
    for name, value in positive_values.items():
        _validate_positive_int(name, value)

    if cfg.scene_viewport_max_area_chunks > (
        cfg.scene_viewport_max_width_chunks * cfg.scene_viewport_max_height_chunks
    ):
        raise RuntimeError(
            "SCENE_VIEWPORT_MAX_AREA_CHUNKS cannot exceed width*height viewport limits"
        )

    if cfg.session_cookie_samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("SESSION_COOKIE_SAMESITE must be one of: lax, strict, none")
    if cfg.session_cookie_samesite == "none" and not cfg.session_cookie_secure:
        raise RuntimeError("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true")

    if cfg.app_env == "production":
        if cfg.web_workers != 1:
            raise RuntimeError(
                "WEB_WORKERS must be 1 in production. V1 realtime fan-out, diagnostics "
                "and metrics are in-process state that does not cross worker boundaries; "
                "running multiple workers silently breaks the multiplayer table. "
                "Scale vertically instead."
            )
        if cfg.session_secret in {"dev-only-change-me", "change-me-in-production"}:
            raise RuntimeError("SESSION_SECRET must be changed before running in production")
        if len(cfg.session_secret) < 32:
            raise RuntimeError("SESSION_SECRET must be at least 32 characters in production")
        if cfg.app_debug:
            raise RuntimeError("APP_DEBUG must be false in production")
        if not cfg.public_base_url:
            raise RuntimeError("PUBLIC_BASE_URL must be set in production")
        if not cfg.public_base_url.startswith("https://"):
            raise RuntimeError("PUBLIC_BASE_URL must use https:// in production")
        if not cfg.allowed_hosts:
            raise RuntimeError("ALLOWED_HOSTS must be set in production")
        if any(host.strip() == "*" for host in cfg.allowed_hosts):
            raise RuntimeError("ALLOWED_HOSTS must not contain '*' in production")
        if not _allowed_host_matches(cfg.public_base_url, cfg.allowed_hosts):
            raise RuntimeError("PUBLIC_BASE_URL host must be present in ALLOWED_HOSTS in production")
        if not cfg.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")
        if not cfg.session_cookie_httponly:
            raise RuntimeError("SESSION_COOKIE_HTTPONLY must be true in production")
        if cfg.database_echo:
            raise RuntimeError("DATABASE_ECHO must be false in production")
        if _is_sqlite_url(cfg.database_url) and not cfg.allow_sqlite_in_production:
            raise RuntimeError(
                "Refusing to run in production on SQLite. Use PostgreSQL, or set "
                "ALLOW_SQLITE_IN_PRODUCTION=true to override."
            )
        if _is_mysql_url(cfg.database_url):
            raise RuntimeError(
                "MySQL/MariaDB is not a supported production backend in V1. "
                "Use PostgreSQL (postgresql+psycopg://...)."
            )


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    app_env: str
    app_debug: bool
    web_workers: int

    public_base_url: str
    allowed_hosts: tuple[str, ...]
    trusted_proxies: tuple[str, ...]
    ws_allowed_origins: tuple[str, ...]

    gravewright_version: str

    data_dir: str

    database_url: str
    allow_sqlite_in_production: bool
    database_pool_size: int
    database_max_overflow: int
    database_pool_timeout: int
    database_pool_recycle_seconds: int
    database_pool_pre_ping: bool
    database_echo: bool
    sqlite_pool_size: int
    sqlite_max_overflow: int
    realtime_blocking_workers: int

    default_locale: str

    session_cookie_name: str
    session_secret: str
    session_max_age: int
    session_cookie_secure: bool
    session_cookie_httponly: bool
    session_cookie_samesite: str
    session_cookie_domain: str | None

    privacy_enabled: bool

    auth_login_max_attempts: int
    auth_login_window_seconds: int
    auth_login_block_seconds: int

    auth_register_max_attempts: int
    auth_register_window_seconds: int

    auth_password_reset_max_attempts: int
    auth_password_reset_window_seconds: int
    auth_password_reset_token_ttl_seconds: int

                                 
    ws_max_message_bytes: int
    ws_commands_per_second: int
    ws_burst_commands: int

                                                                        
    scene_viewport_max_width_chunks: int
    scene_viewport_max_height_chunks: int
    scene_viewport_max_area_chunks: int
    scene_viewport_max_known_chunks: int
    scene_viewport_max_layers: int

                 
    fog_max_ops_per_command: int
    fog_max_polygon_points: int
    fog_max_coordinate_abs: int
    fog_require_expected_version: bool

                     
    token_create_many_max: int
    board_markers_max_per_scene: int
    board_measurements_max_per_user: int

                          
    map_upload_max_bytes: int
    map_image_max_width: int
    map_image_max_height: int
    map_tile_size: int
    map_max_tile_count: int
    map_re_tile_use_staging: bool


_app_env = env_str("APP_ENV", "development")
_allowed_hosts = _resolve_allowed_hosts(_app_env)
_session_domain = env_str("SESSION_COOKIE_DOMAIN", "").strip()

config = AppConfig(
    app_name=env_str("APP_NAME", "Gravewright"),
    app_env=_app_env,
    app_debug=env_bool("APP_DEBUG", True),
    web_workers=env_int("WEB_WORKERS", 1),
    public_base_url=env_str("PUBLIC_BASE_URL", "").strip().rstrip("/"),
    allowed_hosts=_allowed_hosts,
    trusted_proxies=_csv("TRUSTED_PROXIES"),
    ws_allowed_origins=_resolve_ws_allowed_origins(_allowed_hosts),
    gravewright_version=env_str("GRAVEWRIGHT_VERSION", "2.1.0-alpha"),
    data_dir=_resolve_data_dir(),
    database_url=_resolve_database_url(),
    allow_sqlite_in_production=env_bool("ALLOW_SQLITE_IN_PRODUCTION", False),
    database_pool_size=env_int("DATABASE_POOL_SIZE", 5),
    database_max_overflow=env_int("DATABASE_MAX_OVERFLOW", 10),
    database_pool_timeout=env_int("DATABASE_POOL_TIMEOUT", 30),
    sqlite_pool_size=env_int("SQLITE_POOL_SIZE", 24),
    sqlite_max_overflow=env_int("SQLITE_MAX_OVERFLOW", 24),
    realtime_blocking_workers=env_int("REALTIME_BLOCKING_WORKERS", 48),
    database_pool_recycle_seconds=env_int("DATABASE_POOL_RECYCLE_SECONDS", 1800),
    database_pool_pre_ping=env_bool("DATABASE_POOL_PRE_PING", True),
    database_echo=env_bool("DATABASE_ECHO", False),
    default_locale=env_str("DEFAULT_LOCALE", "en"),
    session_cookie_name=env_str("SESSION_COOKIE_NAME", "gravewright_session"),
    session_secret=env_str("SESSION_SECRET", "dev-only-change-me"),
    session_max_age=env_int("SESSION_MAX_AGE", 60 * 60 * 24),
    session_cookie_secure=env_bool("SESSION_COOKIE_SECURE", _app_env == "production"),
    session_cookie_httponly=env_bool("SESSION_COOKIE_HTTPONLY", True),
    session_cookie_samesite=env_str("SESSION_COOKIE_SAMESITE", "lax").strip().lower() or "lax",
    session_cookie_domain=_session_domain or None,
    privacy_enabled=env_bool("PRIVACY_ENABLED", False),
    auth_login_max_attempts=env_int("AUTH_LOGIN_MAX_ATTEMPTS", 8),
    auth_login_window_seconds=env_int("AUTH_LOGIN_WINDOW_SECONDS", 15 * 60),
    auth_login_block_seconds=env_int("AUTH_LOGIN_BLOCK_SECONDS", 15 * 60),
    auth_register_max_attempts=env_int("AUTH_REGISTER_MAX_ATTEMPTS", 8),
    auth_register_window_seconds=env_int("AUTH_REGISTER_WINDOW_SECONDS", 30 * 60),
    auth_password_reset_max_attempts=env_int("AUTH_PASSWORD_RESET_MAX_ATTEMPTS", 6),
    auth_password_reset_window_seconds=env_int("AUTH_PASSWORD_RESET_WINDOW_SECONDS", 30 * 60),
    auth_password_reset_token_ttl_seconds=env_int("AUTH_PASSWORD_RESET_TOKEN_TTL_SECONDS", 60 * 60),
    ws_max_message_bytes=env_int("WS_MAX_MESSAGE_BYTES", 64 * 1024),
    ws_commands_per_second=env_int("WS_COMMANDS_PER_SECOND", 20),
    ws_burst_commands=env_int("WS_BURST_COMMANDS", 40),
    scene_viewport_max_width_chunks=env_int("SCENE_VIEWPORT_MAX_WIDTH_CHUNKS", 16),
    scene_viewport_max_height_chunks=env_int("SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS", 16),
    scene_viewport_max_area_chunks=env_int("SCENE_VIEWPORT_MAX_AREA_CHUNKS", 256),
    scene_viewport_max_known_chunks=env_int("SCENE_VIEWPORT_MAX_KNOWN_CHUNKS", 512),
    scene_viewport_max_layers=env_int("SCENE_VIEWPORT_MAX_LAYERS", 4),
    fog_max_ops_per_command=env_int("FOG_MAX_OPS_PER_COMMAND", 64),
    fog_max_polygon_points=env_int("FOG_MAX_POLYGON_POINTS", 128),
    fog_max_coordinate_abs=env_int("FOG_MAX_COORDINATE_ABS", 100_000),
    fog_require_expected_version=env_bool("FOG_REQUIRE_EXPECTED_VERSION", True),
    token_create_many_max=env_int("TOKEN_CREATE_MANY_MAX", 50),
    board_markers_max_per_scene=env_int("BOARD_MARKERS_MAX_PER_SCENE", 500),
    board_measurements_max_per_user=env_int("BOARD_MEASUREMENTS_MAX_PER_USER", 50),
    map_upload_max_bytes=env_int("MAP_UPLOAD_MAX_BYTES", 25 * 1024 * 1024),
    map_image_max_width=env_int("MAP_IMAGE_MAX_WIDTH", 8192),
    map_image_max_height=env_int("MAP_IMAGE_MAX_HEIGHT", 8192),
    map_tile_size=env_int("MAP_TILE_SIZE", 256),
    map_max_tile_count=env_int("MAP_MAX_TILE_COUNT", 4096),
    map_re_tile_use_staging=env_bool("MAP_RE_TILE_USE_STAGING", True),
)

_validate_config(config)
