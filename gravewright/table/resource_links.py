"""Typed campaign links, projected through each resource's native read boundary.

References contain identities only. A Resolver belongs to one request: it reloads
membership, memoizes native projections and never caches authorization globally.
Unavailable resources deliberately have the same result as missing resources.
"""

from copy import deepcopy
import re
from uuid import UUID

from django.apps import apps
from django.db.models import Q

from gravewright.journals.services import member
from gravewright.maps.services import MapError


def _spec(label, model, group, provider, **extra):
    return {"label": label, "model": model, "group": group, "provider": provider,
            "identifier": "uuid", **extra}


# Archive consumers use model-specific identity maps, never global UUID rewriting.
# Composite entries retain their parent identity and opaque installed entry IDs.
RESOURCE_KINDS = {
    "actor": _spec("Characters", "gravewright_actors.actor", "actors", "actors"),
    "actor-asset": _spec("Character assets", "gravewright_actors.asset", "actors", "actors"),
    "actor-folder": _spec("Character folders", "gravewright_actors.folder", "actors", "actors"),
    "item": _spec("Items", "gravewright_items.item", "items", "items"),
    "item-folder": _spec("Item folders", "gravewright_items.folder", "items", "items"),
    "journal": _spec("Journals", "gravewright_journals.journal", "journals", "journals"),
    "journal-page": _spec("Journal pages", "gravewright_journals.journal", "journals", "journals", fragment="pageId"),
    "journal-asset": _spec("Journal attachments", "gravewright_journals.asset", "journals", "journals"),
    "journal-folder": _spec("Journal folders", "gravewright_journals.folder", "journals", "journals"),
    "quest-board-entry": _spec("Quest board entries", "gravewright_journals.boardentry", "journals", "journals", identifier="integer"),
    "scene": _spec("Scenes", "gravewright_maps.scene", "scenes", "maps"),
    "scene-folder": _spec("Scene folders", "gravewright_maps.folder", "scenes", "maps"),
    "scene-object": _spec("Scene objects", "gravewright_maps.sceneobject", "scenes", "scene", sceneField="scene"),
    "scene-tile": _spec("Scene tiles", "gravewright_maps.tile", "scenes", "scene", identifier="integer", sceneField="scene"),
    "scene-drawing": _spec("Drawings", "gravewright_maps.scenestate", "scenes", "scene", identifier="scene-fragment", sceneField="scene"),
    "token": _spec("Tokens", "gravewright_tokens.token", "scenes", "scene", sceneField="scene", requires=["scenes", "actors"]),
    "encounter": _spec("Encounters", "gravewright_combat.encounter", "combat", "scene", sceneField="scene"),
    "map-asset": _spec("Map images", "gravewright_maps.mapasset", "scenes", "map-assets"),
    "asset-folder": _spec("File folders", "gravewright_maps.assetfolder", "scenes", "map-assets"),
    "clock": _spec("Clocks", "gravewright_table.progressclock", "clocks", "progress", sceneField="scene"),
    "clue": _spec("Clues", "gravewright_table.progressclue", "clues", "progress", sceneField="scene"),
    "track": _spec("Audio tracks", "gravewright_audio.track", "audio", "audio"),
    "playlist": _spec("Playlists", "gravewright_audio.playlist", "audio", "audio"),
    "deck": _spec("Decks", "gravewright_cards.deck", "cards", "cards"),
    "card": _spec("Cards", "gravewright_cards.card", "cards", "cards", sceneField="scene"),
    "deck-definition": _spec("Deck definitions", "gravewright_cards.deckdefinition", "cards", "cards"),
    "card-asset": _spec("Card images", "gravewright_cards.cardasset", "cards", "cards"),
    "compendium": _spec("Compendiums", "gravewright_compendiums.pack", "compendiums", "compendiums", identifier="pack"),
    "compendium-entry": _spec("Compendium entries", "gravewright_compendiums.entry", "compendiums", "compendiums", identifier="pack-entry", parentModel="gravewright_compendiums.pack"),
    "compendium-asset": _spec("Compendium attachments", "gravewright_compendiums.entryasset", "compendiums", "compendiums"),
    "pdf-mapping": _spec("PDF mapping templates", "gravewright_pdf_system.mappingtemplate", "actors", "templates"),
    "session-plan": _spec("Session plans", "gravewright_campaigns.sessionplan", "preparation", "preparation"),
    "campaign-event": _spec("Timeline events", "gravewright_campaigns.campaignevent", "preparation", "preparation"),
    "map-builder-project": _spec("Map Builder projects", "gravewright_maps.mapbuilderproject", "scenes", "templates"),
    "blueprint-template": _spec("Behavior templates", "gravewright_maps.blueprinttemplate", "blueprintTemplates", "templates"),
    "chat-message": _spec("Chat messages", "gravewright_chat.message", "chat", "chat", identifier="integer", sceneField="scene", snapshotOnly=True),
    "mindmap": _spec("Mind maps", "gravewright_table.mindmap", "mindmaps", "mindmaps"),
}
MAX_RESULTS = 200
_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}\Z")
_PAGE = re.compile(r"[^\x00-\x1f\x7f]{1,40}\Z")
_INTEGER = re.compile(r"[1-9][0-9]{0,18}\Z")
_OBJECT_LABELS = {"walls": "Walls", "lights": "Lights", "particles": "Particles",
                  "images": "Images", "shaders": "Shaders", "markers": "Markers",
                  "journalPins": "Journal pins", "spatialSounds": "Spatial sounds", "zones": "Zones"}


def _uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError
    return str(UUID(value))


def _pack(value):
    if value.startswith("native:"):
        return "native:" + _uuid(value[7:])
    return _uuid(value)


def validate_reference(ref):
    """Normalize only a bounded canonical reference; never accept display data."""
    try:
        if (not isinstance(ref, dict) or set(ref) - {"kind", "id", "pageId"}
                or not isinstance(ref.get("kind"), str) or ref["kind"] not in RESOURCE_KINDS
                or not isinstance(ref.get("id"), str) or not 1 <= len(ref["id"]) <= 256):
            raise ValueError
        kind, identifier = ref["kind"], ref["id"]
        codec = RESOURCE_KINDS[kind]["identifier"]
        if codec == "integer":
            if not _INTEGER.fullmatch(identifier) or int(identifier) > 2**63 - 1:
                raise ValueError
        elif codec == "pack":
            identifier = _pack(identifier)
        elif codec == "pack-entry":
            pack, entry = identifier.split("/", 1)
            if not _OPAQUE.fullmatch(entry):
                raise ValueError
            pack = _pack(pack)
            if not pack.startswith("native:"):
                entry = _uuid(entry)
            identifier = pack + "/" + entry
        elif codec == "scene-fragment":
            scene, fragment = identifier.split("/", 1)
            identifier = _uuid(scene) + "/" + _uuid(fragment)
        else:
            identifier = _uuid(identifier)
        result = {"kind": kind, "id": identifier}
        if kind == "journal-page":
            if (not isinstance(ref.get("pageId"), str) or not ref["pageId"].strip()
                    or ref["pageId"] in {".", ".."} or not _PAGE.fullmatch(ref["pageId"])):
                raise ValueError
            result["pageId"] = ref["pageId"]
        elif "pageId" in ref:
            raise ValueError
        return result
    except (ValueError, TypeError, AttributeError):
        raise MapError("Invalid resource reference.", "invalid_data") from None


def _key(ref):
    return ref["kind"], ref["id"], ref.get("pageId")


class Resolver:
    """One fresh membership and one projection per domain/scene per request.

    Do not retain this object between requests or mutations. Returned dictionaries
    are independent copies, and content bodies/URLs/grants never enter the index.
    """

    def __init__(self, who, *, scene_id=None):
        self.who = member(who.campaign_id, who.user_id)
        self._presentation = bool(getattr(who, '_presentation_journal_id', None))
        self._presentation_gm = self._presentation and self.who.role == 'gm'
        if self._presentation:
            # The ticket projection intentionally uses player permissions even
            # for GM recipients. Preserve only its single temporary read scope.
            identifier = str(who._presentation_journal_id)
            self.who.role = 'player'
            self.who._presentation_journal_id = identifier
            self.who._presentation_page_id = getattr(who, '_presentation_page_id', None)
            from .models import DocumentAccess
            grants = {row.resource_id: row.grants for row in DocumentAccess.objects.filter(
                campaign_id=self.who.campaign_id, kind='journals')}
            grants[identifier] = {'default': 'none', str(who.user_id): 'read'}
            self.who._ownership_cache = {'journals': grants}
            pages = getattr(who, '_ownership_cache', {}).get('pages', {})
            page_grants = {row.resource_id: row.grants for row in DocumentAccess.objects.filter(
                campaign_id=self.who.campaign_id, kind='pages')}
            page_grants.update({key: value for key, value in pages.items() if key.startswith(identifier + ':')})
            self.who._ownership_cache['pages'] = page_grants
        try:
            self.scene_id = _uuid(str(scene_id)) if scene_id is not None else None
        except ValueError:
            raise MapError("Invalid resource search.", "invalid_data") from None
        if self.scene_id is not None:
            from gravewright.maps.services import scene
            scene(self.scene_id, self.who)
        self._loaded, self._rows, self._memo = set(), {}, {}
        self._scene_rows = None

    def _add(self, kind, identifier, label, *, page_id=None, scene_id=None, description=None,
             fallback=None, description_key=None, owner_reference=None):
        ref = {"kind": kind, "id": str(identifier)}
        if page_id is not None:
            ref["pageId"] = page_id
        try:
            ref = validate_reference(ref)
        except MapError:
            return
        row = {**ref, "label": str(label or fallback or RESOURCE_KINDS[kind]["label"])[:240]}
        if not label:
            row["labelKey"] = fallback or RESOURCE_KINDS[kind]["label"]
        if scene_id:
            row["sceneId"] = str(scene_id)
        if description:
            row["description"] = str(description)[:240]
        if description_key:
            row["descriptionKey"] = description_key
        if owner_reference:
            row["ownerReference"] = validate_reference(owner_reference)
        self._rows[_key(ref)] = row

    def _load(self, provider):
        if provider in self._loaded:
            return
        self._loaded.add(provider)
        getattr(self, "_" + provider.replace("-", "_"))()

    def _maps(self):
        from gravewright.maps.services import state, scene
        projected = state(self.who.campaign_id, self.who.user_id)
        if self._presentation:
            from gravewright.maps.models import Broadcast
            broadcast = {str(value) for value in Broadcast.objects.filter(
                campaign_id=self.who.campaign_id).values_list('scene_id', flat=True)}
            allowed = []
            for row in projected['maps']:
                if row['id'] not in broadcast:
                    continue
                try:
                    scene(row['id'], self.who)
                except MapError:
                    continue
                allowed.append(row)
            projected['maps'], projected['folders'] = allowed, []
        self._scene_rows = {row["id"]: row for row in projected["maps"]}
        for row in projected["maps"]:
            self._add("scene", row["id"], row["name"])
        for row in projected["folders"]:
            self._add("scene-folder", row["id"], row.get("name", row.get("label")))

    def _scenes(self):
        self._load("maps")
        return [self.scene_id] if self.scene_id else list(self._scene_rows)

    def _actors(self):
        from gravewright.actors import services
        from gravewright.actors.models import Asset
        if self._presentation:
            from gravewright.actors.models import Actor, Folder
            allowed = [services.project(actor, self.who) for actor in Actor.objects.filter(
                campaign_id=self.who.campaign_id).prefetch_related('assets') if services.access(actor, self.who)]
            folders = {str(row.pk): row for row in Folder.objects.filter(campaign_id=self.who.campaign_id)}
            visible = {row['folderId'] for row in allowed if row.get('folderId')}
            while True:
                parents = {str(folders[value].parent_id) for value in visible if value in folders and folders[value].parent_id}
                if parents <= visible:
                    break
                visible |= parents
            projected = {'actors': allowed, 'folders': [{'id': value, 'name': folders[value].name}
                                                       for value in visible if value in folders]}
        else:
            projected = services.state(self.who.campaign_id, self.who.user_id)
        readable, referenced = set(), set()
        for row in projected["actors"]:
            if row["canOpen"]:
                readable.add(row["id"])
                self._add("actor", row["id"], row["name"])
                if self.who.role != "gm":
                    # System assets can be shared library records without an actor FK.
                    # Only the native authorized sheet can supply those references.
                    # A real GM's sheet reader would widen a presentation's
                    # player ceiling. Bound assets remain readable by actor FK;
                    # reusable assets require a genuine recipient sheet read.
                    pending = [] if self._presentation_gm else [
                        services.sheet(self.who.campaign_id, self.who.user_id, row["id"])["data"]]
                    while pending:
                        value = pending.pop()
                        if isinstance(value, dict):
                            pending.extend(value.values())
                        elif isinstance(value, list):
                            pending.extend(value)
                        elif isinstance(value, str):
                            try:
                                referenced.add(_uuid(value[6:] if value.startswith("asset:") else value))
                            except ValueError:
                                pass
        for row in projected["folders"]:
            self._add("actor-folder", row["id"], row["name"])
        assets = Asset.objects.filter(campaign_id=self.who.campaign_id)
        if self.who.role != "gm":
            assets = assets.filter(Q(actor_id__in=readable) | Q(actor__isnull=True, pk__in=referenced))
        for row in assets.only("id", "name", "actor_id"):
            owner = {"kind": "actor", "id": str(row.actor_id)} if str(row.actor_id) in readable else None
            self._add("actor-asset", row.pk, row.name, owner_reference=owner)

    def _items(self):
        from gravewright.items import services
        projected = services.state(self.who)
        for row in projected["items"]:
            if row["canOpen"]:
                self._add("item", row["id"], row["name"])
        for row in projected["folders"]:
            self._add("item-folder", row["id"], row["name"])

    def _journals(self):
        from gravewright.journals import services
        from gravewright.journals.models import Asset, BoardEntry
        projected = services.metadata_state(self.who)
        visible_assets, readable, entries, editable = set(), set(), {}, set()
        for row in projected["journals"]:
            if not row.get("can_open"):
                continue
            readable.add(row["id"])
            if row.get("can_edit"):
                editable.add(row["id"])
            self._add("journal", row["id"], row["title"])
            visible_assets.update(services.asset_ids(row))
            for page in row.get("sections", []):
                self._add("journal-page", row["id"], page["title"], page_id=page["id"], description=row["title"])
            for entry in row.get("board_entries", []):
                entries[(row["id"], entry["quest_id"])] = entry["card"].get("title", row["title"])
        for asset in Asset.objects.filter(journal__campaign_id=self.who.campaign_id).only("id", "name", "journal_id", "uploader_id"):
            if str(asset.pk) in visible_assets:
                self._add("journal-asset", asset.pk, asset.name,
                          owner_reference={"kind": "journal", "id": str(asset.journal_id)})
            elif asset.uploader_id == self.who.user_id and str(asset.journal_id) in editable:
                journal = services.get(asset.journal_id, self.who)
                if str(asset.pk) not in set(services.asset_ids(journal.data)):
                    self._add("journal-asset", asset.pk, asset.name,
                              owner_reference={"kind": "journal", "id": str(asset.journal_id)})
        for entry in BoardEntry.objects.filter(board_id__in=readable).only("id", "board_id", "quest_id"):
            label = entries.get((str(entry.board_id), str(entry.quest_id)))
            if label:
                self._add("quest-board-entry", entry.pk, label,
                          owner_reference={"kind": "journal", "id": str(entry.quest_id)})
        for row in projected["folders"]:
            self._add("journal-folder", row["id"], row["name"])

    def _load_scene(self, identifier):
        cache_key = "scene:" + identifier
        if cache_key in self._loaded:
            return
        self._loaded.add(cache_key)
        from gravewright.maps import services, objects
        from gravewright.maps.models import Tile
        from gravewright.tokens import services as tokens
        from gravewright.combat import services as combat
        target = services.scene(identifier, self.who)
        projected = objects.layer_state(target, self.who)
        for kind in ("walls", "lights", "particles", "images", "shaders", "markers", "journalPins", "spatialSounds", "zones"):
            for row in projected.get(kind, []):
                # Undiscovered barriers have geometry for clipping, not discoverable links.
                if (self.who.role != "gm" and kind == "walls"
                        and row.get("presentation") in {"secret", "invisible"} and not row.get("discovered")):
                    continue
                self._add("scene-object", row["id"], row.get("name") or row.get("label"),
                          scene_id=identifier, fallback=_OBJECT_LABELS[kind], description_key=_OBJECT_LABELS[kind])
        for row in projected.get("drawings", {}).get("rows", []):
            self._add("scene-drawing", identifier + "/" + str(row.get("id")),
                      row.get("name") or row.get("text"), scene_id=identifier)
        for tile in Tile.objects.filter(scene=target).only("id", "lod", "x", "y"):
            self._add("scene-tile", tile.pk, f"{target.name} · {tile.lod}/{tile.x}/{tile.y}", scene_id=identifier)
        for row in tokens.rows(target, self.who):
            self._add("token", row["id"], row["name"], scene_id=identifier)
        from gravewright.combat.models import Encounter
        encounter = Encounter.objects.filter(scene=target).first()
        if encounter is not None:
            combat.state(self.who, identifier)
            self._add("encounter", identifier, target.name, scene_id=identifier)

    def _scene(self):
        for identifier in self._scenes():
            self._load_scene(identifier)

    def _map_assets(self):
        from gravewright.maps.models import MapAsset, AssetFolder
        images = MapAsset.objects.filter(campaign_id=self.who.campaign_id)
        if self.who.role != "gm":
            from gravewright.maps.library_services import active_scene, visible_door_art
            from gravewright.maps.models import SceneObject
            try:
                active = active_scene(self.who)
            except MapError as error:
                if error.code != 'not_found':
                    raise
                # A revoked scene does not revoke campaign actors, items or
                # other independently readable resource-link directories.
                return
            allowed = {row.get("asset_id") for row in SceneObject.objects.filter(scene_id=active, kind="images").values_list("data", flat=True)
                       if row.get("layer") not in {"gm", "gm-image-layer"} and not row.get("empty")}
            allowed.update(visible_door_art(active))
            images = images.filter(pk__in=allowed, generated_for__isnull=True)
        folders = set()
        for row in images.only("id", "name", "folder_id"):
            self._add("map-asset", row.pk, row.name)
            if row.folder_id:
                folders.add(row.folder_id)
        rows = AssetFolder.objects.filter(campaign_id=self.who.campaign_id)
        if self.who.role != "gm":
            rows = rows.filter(pk__in=folders)
        for row in rows:
            self._add("asset-folder", row.pk, row.name)

    def _progress(self):
        from . import clocks, clues
        for identifier in [None, *self._scenes()]:
            for kind, service in (("clock", clocks), ("clue", clues)):
                for row in service.state(self.who, identifier)[kind + "s"]:
                    self._add(kind, row["id"], row["name"], scene_id=row["sceneId"])

    def _audio(self):
        from gravewright.audio import services
        for identifier in [None, *self._scenes()]:
            projected = services.state(self.who, identifier)
            for row in projected["tracks"]:
                self._add("track", row["id"], row["name"])
            for row in projected["playlists"]:
                self._add("playlist", row["id"], row["name"])

    def _cards(self):
        from gravewright.cards import services
        from gravewright.cards.models import Card, CardAsset, DeckDefinition
        for identifier in [None, *self._scenes()]:
            projected = services.state(self.who, identifier)
            for row in projected["decks"]:
                self._add("deck", row["id"], row["name"])
            for row in projected["hand"] + projected["cards"]:
                self._add("card", row["id"], row["name"], scene_id=row.get("sceneId"))
        if self.who.role == "gm":
            from gravewright.maps.services import manage
            manage(self.who)
            for card in Card.objects.filter(deck__campaign_id=self.who.campaign_id).select_related("deck"):
                row = services.card_data(card, self.who)
                self._add("card", row["id"], row["name"], scene_id=row.get("sceneId"))
            for row in DeckDefinition.objects.filter(campaign_id=self.who.campaign_id):
                self._add("deck-definition", row.pk, row.name)
            for row in CardAsset.objects.filter(campaign_id=self.who.campaign_id):
                self._add("card-asset", row.pk, row.purpose)

    def _compendiums(self):
        from gravewright.compendiums import services
        from gravewright.compendiums.models import EntryAsset
        projected = services.state(self.who)
        visible_entries = set()
        for pack in projected["packs"]:
            self._add("compendium", pack["id"], pack["name"])
            for entry in pack["entries"]:
                self._add("compendium-entry", pack["id"] + "/" + entry["id"], entry["name"], description=pack["name"])
                if not pack["id"].startswith("native:"):
                    visible_entries.add(entry["id"])
        for row in EntryAsset.objects.filter(entry_id__in=visible_entries, entry__pack__campaign_id=self.who.campaign_id).select_related('entry').only("id", "name", "entry__id", "entry__pack_id"):
            self._add("compendium-asset", row.pk, row.name, owner_reference={"kind": "compendium-entry",
                      "id": str(row.entry.pack_id) + '/' + str(row.entry_id)})

    def _preparation(self):
        if self.who.role != "gm":
            return
        from gravewright.campaigns import preparation
        projected = preparation.state(self.who.user, self.who.campaign_id)
        for row in projected["sessions"]:
            self._add("session-plan", row["id"], row["title"])
        for row in projected["events"]:
            self._add("campaign-event", row["id"], row["title"])

    def _templates(self):
        if self.who.role != "gm":
            return
        from gravewright.maps import builder_services, blueprint_templates
        from api import systems
        for row in builder_services.catalog(self.who.campaign_id, self.who.user_id)["projects"]:
            self._add("map-builder-project", row["id"], row["name"], scene_id=row.get("sceneId"))
        for row in blueprint_templates.catalog(self.who.campaign_id, self.who.user_id)["templates"]:
            self._add("blueprint-template", row["id"], row["name"])
        operations = systems.capabilities(self.who.campaign_id, self.who.user_id)['operations']
        if any(row['name'] == 'pdf.templates.list' and row['effect'] == 'read' for row in operations):
            for row in systems.call(self.who.campaign_id, self.who.user_id, 'pdf.templates.list', {})["items"]:
                self._add("pdf-mapping", row["id"], row["name"])

    def _chat(self):
        from gravewright.chat import services
        from gravewright.accounts.services import AuthError
        # Native history is intentionally bounded and filters recipients, even for GMs.
        for identifier in [None, *self._scenes()]:
            try:
                rows = services.history(self.who.campaign_id, self.who.user_id, identifier)
            except AuthError as error:
                if error.code != 'invalid_scene':
                    raise
                continue
            for row in rows:
                self._add("chat-message", row["id"], row["text"][:160], scene_id=row.get("sceneId"))

    def _chat_message(self, identifier):
        """An existing link survives advancing past the native history window."""
        from gravewright.chat.models import Message
        from gravewright.chat.services import public_message
        from gravewright.chat.context import readable
        row = Message.objects.filter(pk=identifier, campaign_id=self.who.campaign_id, deleted=False).filter(
            Q(visibility="public") | Q(recipients__user_id=self.who.user_id)).distinct().select_related("scene").first()
        if row is not None and self._presentation and row.scene_id:
            from gravewright.maps.services import scene
            try:
                scene(row.scene_id, self.who)
            except MapError:
                return
        if row is not None and readable(self.who.campaign_id, self.who.user_id, row.scene_id):
            projected = public_message(row)
            self._add("chat-message", projected["id"], projected["text"][:160], scene_id=projected.get("sceneId"))

    def _mindmaps(self):
        try:
            model = apps.get_model("gravewright_table", "MindMap")
        except LookupError:
            return
        from . import mindmaps
        for identifier in model.objects.filter(campaign_id=self.who.campaign_id).values_list("pk", flat=True):
            try:
                row = mindmaps.get(str(identifier), self.who)
            except MapError:
                continue
            self._add("mindmap", row.pk, getattr(row, "title", getattr(row, "name", "Mind maps")))

    def resolve(self, ref):
        ref = validate_reference(ref)
        key = _key(ref)
        if key not in self._memo:
            provider = RESOURCE_KINDS[ref["kind"]]["provider"]
            if provider == "scene":
                self._load("maps")
                if ref["kind"] == "scene-drawing":
                    identifier = ref["id"].split("/", 1)[0]
                else:
                    model = apps.get_model(RESOURCE_KINDS[ref["kind"]]["model"])
                    identifier = model.objects.filter(pk=ref["id"], scene__campaign_id=self.who.campaign_id).values_list("scene_id", flat=True).first()
                    identifier = str(identifier) if identifier else None
                if identifier in self._scene_rows:
                    self._load_scene(identifier)
            else:
                self._load(provider)
                if ref["kind"] == "chat-message" and key not in self._rows:
                    self._chat_message(ref["id"])
            self._memo[key] = self._rows.get(key)
        return deepcopy(self._memo[key])

    def resolve_many(self, refs):
        if not isinstance(refs, list) or len(refs) > 2048:
            raise MapError("Invalid resource references.", "invalid_data")
        return [self.resolve(ref) for ref in refs]

    def catalog(self, *, query="", kinds=None, limit=80):
        if (not isinstance(query, str) or len(query) > 120 or type(limit) is not int
                or not 1 <= limit <= MAX_RESULTS):
            raise MapError("Invalid resource search.", "invalid_data")
        selected = list(RESOURCE_KINDS) if kinds is None else kinds
        if (not isinstance(selected, (list, tuple)) or len(selected) > len(RESOURCE_KINDS)
                or any(not isinstance(kind, str) or kind not in RESOURCE_KINDS for kind in selected)
                or len(set(selected)) != len(selected)):
            raise MapError("Invalid resource search.", "invalid_data")
        for kind in selected:
            self._load(RESOURCE_KINDS[kind]["provider"])
        needle, allowed = query.strip().casefold(), set(selected)
        rows = [deepcopy(row) for row in self._rows.values() if row["kind"] in allowed
                and (not needle or needle in row["label"].casefold() or needle in row.get("description", "").casefold())]
        rows.sort(key=lambda row: (row["label"].casefold(), row["kind"], row["id"], row.get("pageId", "")))
        return {"kinds": [{"id": kind, "label": RESOURCE_KINDS[kind]["label"]} for kind in RESOURCE_KINDS],
                "resources": rows[:limit], "truncated": len(rows) > limit}


def resolve(who, ref):
    return Resolver(who).resolve(ref)


def catalog(who, *, query="", kinds=None, limit=80, scene_id=None):
    return Resolver(who, scene_id=scene_id).catalog(query=query, kinds=kinds, limit=limit)


def resolve_many(who, refs):
    return Resolver(who).resolve_many(refs)
