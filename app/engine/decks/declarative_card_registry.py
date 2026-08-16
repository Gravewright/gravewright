"""Validated, immutable card definitions declared by active SDK packages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_paths import safe_join

IDENTIFIER = re.compile(r"^[a-z][a-z0-9._-]{0,95}$")
MAX_DECKS = 64
MAX_CARDS = 500
MAX_DOCUMENT_BYTES = 256_000


class CardDefinitionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DeclaredDeck:
    package_id: str
    deck_id: str
    version: int
    label: str
    description: str
    metadata_schema: dict
    tags: tuple[str, ...]
    cards: tuple[dict, ...]

    @property
    def reference(self) -> str:
        return f"{self.package_id}:{self.deck_id}@{self.version}"

    def public(self) -> dict:
        return {
            "id": self.deck_id, "packageId": self.package_id, "version": self.version,
            "reference": self.reference, "label": self.label, "description": self.description,
            "metadataSchema": self.metadata_schema, "tags": list(self.tags),
            "cards": [dict(card) for card in self.cards],
        }


def _validate(package_id: str, raw: object) -> DeclaredDeck:
    if not isinstance(raw, dict):
        raise CardDefinitionError("sdk.cards.definition_invalid")
    deck_id, version = raw.get("id"), raw.get("version")
    cards, schema, tags = raw.get("cards"), raw.get("metadataSchema", {"type": "object"}), raw.get("tags", [])
    if not isinstance(deck_id, str) or not IDENTIFIER.fullmatch(deck_id):
        raise CardDefinitionError("sdk.cards.definition_id_invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise CardDefinitionError("sdk.cards.definition_version_invalid")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise CardDefinitionError("sdk.cards.metadata_schema_invalid")
    if not isinstance(tags, list) or len(tags) > 32 or any(not isinstance(tag, str) or not IDENTIFIER.fullmatch(tag) for tag in tags):
        raise CardDefinitionError("sdk.cards.tags_invalid")
    if not isinstance(cards, list) or not cards or len(cards) > MAX_CARDS:
        raise CardDefinitionError("sdk.cards.cards_invalid")
    clean = []
    seen = set()
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("id"), str) or not IDENTIFIER.fullmatch(card["id"]):
            raise CardDefinitionError("sdk.cards.card_invalid")
        if card["id"] in seen:
            raise CardDefinitionError("sdk.cards.card_duplicate")
        seen.add(card["id"])
        quantity = card.get("quantity", 1)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 999:
            raise CardDefinitionError("sdk.cards.card_invalid")
        metadata = card.get("metadata", {})
        card_tags = card.get("tags", [])
        if not isinstance(metadata, dict) or len(json.dumps(metadata, separators=(",", ":"))) > 16_384:
            raise CardDefinitionError("sdk.cards.metadata_invalid")
        if not isinstance(card_tags, list) or len(card_tags) > 32 or any(not isinstance(tag, str) for tag in card_tags):
            raise CardDefinitionError("sdk.cards.card_invalid")
        clean.append({"id": card["id"], "label": str(card.get("label") or card["id"])[:191],
                      "quantity": quantity, "tags": list(dict.fromkeys(card_tags)), "metadata": metadata,
                      "artwork": {"kind": "campaign-asset-slot"}})
    return DeclaredDeck(package_id, deck_id, version, str(raw.get("label") or deck_id)[:191],
                        str(raw.get("description") or "")[:2000], schema, tuple(dict.fromkeys(tags)), tuple(clean))


class DeclarativeCardRegistry:
    def list(self, package_id: str) -> list[DeclaredDeck]:
        loaded = package_registry.load_by_package_id(package_id)
        manifest = PackageInstallService().get_active_manifest(package_id)
        if loaded is None or manifest is None:
            raise CardDefinitionError("sdk.runtime.package_disabled")
        relative = manifest.rules.get("cardRegistry", "")
        path = safe_join(loaded.package_dir, relative) if relative else None
        if path is None or not path.is_file():
            return []
        try:
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                raise ValueError
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CardDefinitionError("sdk.cards.registry_invalid") from exc
        raw = document.get("decks") if isinstance(document, dict) else None
        if not isinstance(raw, list) or len(raw) > MAX_DECKS:
            raise CardDefinitionError("sdk.cards.registry_invalid")
        result, identities = [], set()
        for value in raw:
            definition = _validate(package_id, value)
            identity = (definition.deck_id, definition.version)
            if identity in identities:
                raise CardDefinitionError("sdk.cards.definition_duplicate")
            identities.add(identity); result.append(definition)
        return result

    def get(self, package_id: str, deck_id: str, version: int | None = None) -> DeclaredDeck:
        matches = [entry for entry in self.list(package_id) if entry.deck_id == deck_id]
        if version is not None:
            matches = [entry for entry in matches if entry.version == version]
        if not matches:
            raise CardDefinitionError("sdk.cards.definition_not_found")
        return max(matches, key=lambda entry: entry.version)


def validate_registry_file(package_id: str, raw: object) -> list[str]:
    decks = raw.get("decks") if isinstance(raw, dict) else None
    if not isinstance(decks, list) or len(decks) > MAX_DECKS:
        return ["sdk.cards.registry_invalid"]
    errors, seen = [], set()
    for value in decks:
        try:
            entry = _validate(package_id, value)
            identity = (entry.deck_id, entry.version)
            if identity in seen: errors.append("sdk.cards.definition_duplicate")
            seen.add(identity)
        except CardDefinitionError as exc:
            errors.append(exc.code)
    return list(dict.fromkeys(errors))
