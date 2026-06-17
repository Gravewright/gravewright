from __future__ import annotations

from app.actions.sdk.campaign_packages import (
    activate_campaign_package,
    deactivate_campaign_package,
    list_campaign_packages,
    set_campaign_ruleset,
)
from app.actions.sdk.package_assets import serve_package_asset
from app.actions.sdk.package_content import (
    get_package_content_pack,
    import_package_content_entry,
    list_package_content_packs,
)
from app.actions.sdk.package_settings import update_package_setting
from app.actions.sdk.package_storage import (
    storage_sqlite_execute,
    storage_sqlite_query,
    storage_sqlite_status,
)
from app.actions.sdk.packages import (
    disable_package,
    enable_package,
    get_package,
    install_package,
    list_packages,
    remove_package,
    upload_package,
)

route_handlers = [
    list_packages,
    get_package,
    install_package,
    upload_package,
    enable_package,
    disable_package,
    remove_package,
    serve_package_asset,
    update_package_setting,
    list_campaign_packages,
    activate_campaign_package,
    deactivate_campaign_package,
    set_campaign_ruleset,
    list_package_content_packs,
    get_package_content_pack,
    import_package_content_entry,
    storage_sqlite_query,
    storage_sqlite_execute,
    storage_sqlite_status,
]
