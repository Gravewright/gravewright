"""Engine configuration supported by the Django implementation."""
import os
from ipaddress import ip_network
from config.environment import env_bool


def positive_int(name, default):
    value = int(os.environ.get(name, default))
    if value < 1:
        raise ValueError(f'{name} must be positive.')
    return value


def configure():
    values = {name: env_bool(name, True) for name in (
        'CAMPAIGN_JOIN_CODE_ENABLED', 'CAMPAIGN_CLONE_ENABLED',
        'CAMPAIGN_SNAPSHOTS_ENABLED', 'ADMINISTRATIVE_AUDIT_ENABLED',
        'TARGETED_HANDOUTS_ENABLED', 'CAMPAIGN_EXPORT_ENABLED',
        'COMMAND_PALETTE_ENABLED', 'LOBBY_READY_CHECK_ENABLED',
        'DYNAMIC_LIGHTING_ENABLED', 'FOG_REQUIRE_EXPECTED_VERSION',
    )}
    values['PRIVACY_ENABLED'] = env_bool('PRIVACY_ENABLED',False)
    values['APP_DEBUG'] = env_bool('APP_DEBUG', False)
    defaults = {
        'CAMPAIGN_SNAPSHOT_RETENTION': 20,
        'ADMINISTRATIVE_AUDIT_RETENTION_DAYS': 180,
        'JOIN_CODE_DEFAULT_EXPIRES_HOURS': 168,
        'JOIN_CODE_MIN_EXPIRES_HOURS': 1,
        'JOIN_CODE_MAX_EXPIRES_HOURS': 720,
        'JOIN_CODE_MAX_USES_LIMIT': 1000,
        'JOIN_CODE_REDEEM_MAX_ATTEMPTS': 10,
        'JOIN_CODE_REDEEM_WINDOW_SECONDS': 600,
        'DATABASE_POOL_TIMEOUT': 30,
        'WS_MAX_MESSAGE_BYTES': 65536,
        'WS_COMMANDS_PER_SECOND': 20,
        'WS_BURST_COMMANDS': 40,
        'SCENE_VIEWPORT_MAX_WIDTH_CHUNKS': 16,
        'SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS': 16,
        'SCENE_VIEWPORT_MAX_AREA_CHUNKS': 256,
        'FOG_MAX_OPS_PER_COMMAND': 64,
        'FOG_MAX_POLYGON_POINTS': 128,
        'FOG_MAX_COORDINATE_ABS': 100000,
        'TOKEN_CREATE_MANY_MAX': 50,
        'BOARD_MARKERS_MAX_PER_SCENE': 500,
        'BOARD_MEASUREMENTS_MAX_PER_USER': 50,
        'JOURNAL_IMAGE_MAX_BYTES': 10485760,
        'JOURNAL_PDF_MAX_BYTES': 26214400,
        'MAP_UPLOAD_MAX_BYTES': 53687091200,
        'MAP_IMAGE_MAX_WIDTH': 500000,
        'MAP_IMAGE_MAX_HEIGHT': 500000,
        'MAP_MAX_TILE_COUNT': 4096,
    }
    values.update({name: positive_int(name, default) for name, default in defaults.items()})
    if not values['JOIN_CODE_MIN_EXPIRES_HOURS'] <= values['JOIN_CODE_DEFAULT_EXPIRES_HOURS'] <= values['JOIN_CODE_MAX_EXPIRES_HOURS']:
        raise ValueError('Join code expiration must be between the configured minimum and maximum.')
    if values['SCENE_VIEWPORT_MAX_AREA_CHUNKS'] > values['SCENE_VIEWPORT_MAX_WIDTH_CHUNKS'] * values['SCENE_VIEWPORT_MAX_HEIGHT_CHUNKS']:
        raise ValueError('Viewport area cannot exceed width times height.')
    values['TRUSTED_PROXIES'] = tuple(v.strip() for v in os.environ.get('TRUSTED_PROXIES', '').split(',') if v.strip())
    for network in values['TRUSTED_PROXIES']:
        ip_network(network, strict=False)
    values['APP_NAME'] = os.environ.get('APP_NAME', 'Gravewright').strip() or 'Gravewright'
    values['DEFAULT_LOCALE'] = os.environ.get('DEFAULT_LOCALE', 'en').strip() or 'en'
    values['DATABASE_ECHO'] = env_bool('DATABASE_ECHO', False)
    return values
