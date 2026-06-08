from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.config import config
from app.i18n.en import CATALOG as EN_CATALOG
from app.i18n.pt_br import CATALOG as PT_BR_CATALOG


CatalogValue = str | dict[str, Any]


CATALOGS: dict[str, Mapping[str, CatalogValue]] = {
    "en": EN_CATALOG,
    "pt-BR": PT_BR_CATALOG,
}


PLURAL_KEYS = {"zero", "one", "two", "few", "many", "other"}
GENDER_KEYS = {"male", "female", "neutral", "other"}


def get_configured_default_locale() -> str:
    path = Path(config.data_dir) / "inside" / "settings.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return config.default_locale

    app = data.get("app") if isinstance(data, dict) else None
    locale = app.get("default_locale") if isinstance(app, dict) else None
    return locale if isinstance(locale, str) and locale in CATALOGS else config.default_locale


class MissingFormatValue(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def get_supported_locale(locale: str | None) -> str:
    if not locale:
        return get_configured_default_locale()

    if locale in CATALOGS:
        return locale

    short_locale = locale.split("-", 1)[0]

    if short_locale in CATALOGS:
        return short_locale

    return get_configured_default_locale()


def get_locale_from_cookies(cookies: dict[str, str]) -> str:
    return get_supported_locale(cookies.get("gravewright_locale"))


def get_plural_category(locale: str, count: int | float) -> str:
    if locale == "en":
        return "one" if count == 1 else "other"

    if locale == "pt-BR":
        return "one" if count == 1 else "other"

    return "one" if count == 1 else "other"


def resolve_catalog_value(
    value: CatalogValue,
    *,
    locale: str,
    count: int | float | None,
    gender: str | None,
) -> str:
    current: CatalogValue = value

    while isinstance(current, dict):
        keys = set(current.keys())

        if count is not None and keys & PLURAL_KEYS:
            plural_category = get_plural_category(locale, count)
            current = current.get(plural_category, current.get("other", ""))
            continue

        if gender is not None and keys & GENDER_KEYS:
            current = current.get(gender, current.get("other", ""))
            continue

        current = current.get("other", "")

    return current


def translate(
    key: str,
    *,
    locale: str | None = None,
    count: int | float | None = None,
    gender: str | None = None,
    **params: Any,
) -> str:
    selected_locale = get_supported_locale(locale)
    catalog = CATALOGS.get(selected_locale, EN_CATALOG)

    value = catalog.get(key)

    if value is None:
        value = EN_CATALOG.get(key)

    if value is None:
        return key

    resolved = resolve_catalog_value(
        value,
        locale=selected_locale,
        count=count,
        gender=gender,
    )

    format_params = MissingFormatValue(params)

    if count is not None:
        format_params["count"] = count

    if gender is not None:
        format_params["gender"] = gender

    return resolved.format_map(format_params)


def translator_for_locale(locale: str):
    selected_locale = get_supported_locale(locale)

    def t(
        key: str,
        count: int | float | None = None,
        gender: str | None = None,
        **params: Any,
    ) -> str:
        return translate(
            key,
            locale=selected_locale,
            count=count,
            gender=gender,
            **params,
        )

    return t
