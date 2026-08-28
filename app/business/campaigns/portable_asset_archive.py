"""Portable campaign-owned asset graph and archive payload validation."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.engine.assets.asset_ingestion_service import AssetIngestionService
from app.helpers.env import PROJECT_ROOT
from app.persistence.tables import (
    card_deck_definitions, card_deck_instances, card_definitions,
    card_instances, card_pile_entries, card_piles, journal_assets, library_assets,
    pdf_annotations, scene_assets, scene_card_placements, scene_chunks,
    scene_image_placements, scene_layers, scenes, scene_tiles, tokens,
    sounds, sound_playlists, soundscapes, scene_spatial_sounds,
)
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage

ASSET_MANIFEST_VERSION = 2
LEGACY_ASSET_MANIFEST_VERSION = 1
MAX_ASSETS = 100_000
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
TOKEN_ASSET_URL = re.compile(r"^/(?:game/assets/file|game/journal/asset)/([A-Za-z0-9_-]+)$")

REFERENCE_FIELDS: dict[str, tuple[str, ...]] = {
    "actors_core": ("portrait_asset_id", "token_asset_id"),
    "items_core": ("portrait_asset_id",),
    "card_deck_definitions": ("default_back_asset_id",),
    "card_definitions": ("front_asset_id", "back_asset_id"),
    "scene_image_placements": ("asset_id",),
    "pdf_annotations": ("document_id",),
    "sounds": ("asset_id",),
}

PORTABLE_TABLES = (
    card_deck_definitions, card_definitions, card_deck_instances, card_piles,
    card_instances, card_pile_entries, scene_card_placements,
    sounds, sound_playlists, soundscapes,
)


class PortableAssetError(ValueError):
    pass


def _validate_payload(validator: AssetIngestionService, *, data: bytes, media_type_hint: str):
    """Accept legacy audio rows whose browser-provided MIME mislabeled the container."""
    checked = validator.validate_portable_payload(data=data, media_type_hint=media_type_hint)
    if not checked.success and media_type_hint.startswith("audio/"):
        detected = validator.validate_portable_payload(data=data)
        if detected.success and str(detected.payload.get("contentType") or "").startswith("audio/"):
            return detected
    return checked


def _registered_path(storage_path: str) -> Path:
    path = Path(storage_path)
    resolved = path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    allowed = (PROJECT_ROOT / "storage").resolve()
    test_root = __import__("os").environ.get("GRAVEWRIGHT_TEST_TEMP_ROOT", "").strip()
    roots = [allowed] + ([Path(test_root).resolve()] if test_root else [])
    if not any(root == resolved or root in resolved.parents for root in roots):
        raise PortableAssetError("asset path outside managed storage")
    return resolved


class PortableAssetGraph:
    def collect(self, connection, *, campaign_id: str, content: dict[str, list[dict]]) -> tuple[dict, dict[str, bytes]]:
        """Add typed dependent state and replace runtime asset IDs with archive IDs."""
        scene_ids = [str(row["id"]) for row in content.get("scenes", [])]
        if scene_ids:
            content["tokens"] = [dict(row) for row in connection.execute(select(tokens).where(tokens.c.scene_id.in_(scene_ids))).mappings()]
            content["scene_image_placements"] = [dict(row) for row in connection.execute(select(scene_image_placements).where(scene_image_placements.c.campaign_id == campaign_id)).mappings()]
            content["scene_spatial_sounds"] = [dict(row) for row in connection.execute(select(scene_spatial_sounds).where(scene_spatial_sounds.c.scene_id.in_(scene_ids))).mappings()]
        for table in PORTABLE_TABLES:
            if table is card_definitions:
                deck_ids = [str(row["id"]) for row in content.get("card_deck_definitions", [])]
                rows = [] if not deck_ids else connection.execute(select(table).where(table.c.deck_definition_id.in_(deck_ids))).mappings()
            elif table is card_pile_entries:
                pile_ids = [str(row["id"]) for row in content.get("card_piles", [])]
                rows = [] if not pile_ids else connection.execute(select(table).where(table.c.pile_id.in_(pile_ids))).mappings()
            elif "campaign_id" in table.c:
                rows = connection.execute(select(table).where(table.c.campaign_id == campaign_id)).mappings()
            else:
                rows = []
            content[table.name] = [dict(row) for row in rows]
        content["pdf_annotations"] = [dict(row) for row in connection.execute(select(pdf_annotations).where(pdf_annotations.c.campaign_id == campaign_id)).mappings()]
        for table_name in ("card_deck_instances","card_piles","card_instances","scene_card_placements"):
            for row in content.get(table_name,[]):
                row["portablePrincipal"] = bool(row.get("owner_user_id"))

        journal_runtime_ids = set(connection.execute(
            select(journal_assets.c.id).where(journal_assets.c.campaign_id == campaign_id)
        ).scalars())
        referenced: set[str] = set()
        for table_name, fields in REFERENCE_FIELDS.items():
            for row in content.get(table_name, []):
                for field in fields:
                    value = row.get(field)
                    if value and not (table_name == "pdf_annotations" and str(value) in journal_runtime_ids):
                        referenced.add(str(value))
        for row in content.get("tokens", []):
            match = TOKEN_ASSET_URL.fullmatch(str(row.get("token_asset_url") or ""))
            if match: referenced.add(match.group(1))
        if len(referenced) > MAX_ASSETS:
            raise PortableAssetError("too many assets")
        rows = [] if not referenced else [dict(row) for row in connection.execute(select(library_assets).where(library_assets.c.id.in_(referenced), library_assets.c.campaign_id == campaign_id)).mappings()]
        by_id = {str(row["id"]): row for row in rows}
        if set(by_id) != referenced:
            raise PortableAssetError("asset graph is not closed")

        id_map = {runtime_id: f"asset-{index:06d}" for index, runtime_id in enumerate(sorted(referenced), 1)}
        entries, blobs, total = [], {}, 0
        validator = AssetIngestionService()
        for runtime_id in sorted(referenced):
            row = by_id[runtime_id]; data = _registered_path(str(row["storage_path"])).read_bytes()
            total += len(data)
            if total > MAX_TOTAL_BYTES or len(data) != int(row["byte_size"]):
                raise PortableAssetError("asset size mismatch")
            validated = _validate_payload(validator, data=data, media_type_hint=str(row["content_type"] or ""))
            digest = hashlib.sha256(data).hexdigest()
            if not validated.success or digest != str(row["hash"]):
                raise PortableAssetError("asset validation failed")
            export_id = id_map[runtime_id]; location = f"assets/{export_id}.payload"
            entries.append({"id":export_id,"digest":digest,"bytes":len(data),"mediaTypeHint":validated.payload["contentType"],
                            "filename":Path(str(row["filename"])).name[:191],"ownership":"campaign","payload":location})
            blobs[location] = data
        self._rewrite(content, id_map)
        journals, journal_blobs = self._collect_journals(connection, campaign_id, content)
        rasters, raster_blobs = self._collect_rasters(connection, scene_ids)
        for location, data in (*journal_blobs.items(), *raster_blobs.items()):
            if location in blobs:
                raise PortableAssetError("duplicate physical payload")
            blobs[location] = data
        if sum(len(data) for data in blobs.values()) > MAX_TOTAL_BYTES:
            raise PortableAssetError("portable physical graph is too large")
        return {
            "version": ASSET_MANIFEST_VERSION,
            "assets": entries,
            "journalAttachments": journals,
            "rasters": rasters,
        }, blobs

    def _collect_journals(self, connection, campaign_id: str, content: dict) -> tuple[list[dict], dict[str, bytes]]:
        rows = [dict(row) for row in connection.execute(
            select(journal_assets).where(journal_assets.c.campaign_id == campaign_id)
        ).mappings()]
        id_map = {str(row["id"]): f"journal-{index:06d}" for index, row in enumerate(sorted(rows, key=lambda r: str(r["id"])), 1)}
        entries: list[dict] = []
        blobs: dict[str, bytes] = {}
        validator = AssetIngestionService()
        for row in rows:
            runtime_id = str(row["id"])
            export_id = id_map[runtime_id]
            data = _registered_path(str(row["storage_path"])).read_bytes()
            checked = _validate_payload(validator, data=data, media_type_hint=str(row["content_type"] or ""))
            digest = hashlib.sha256(data).hexdigest()
            if not checked.success or digest != str(row["hash"]) or len(data) != int(row["byte_size"]):
                raise PortableAssetError("journal attachment validation failed")
            location = f"assets/{export_id}.payload"
            entries.append({
                "id": export_id, "digest": digest, "bytes": len(data),
                "mediaTypeHint": checked.payload["contentType"],
                "filename": Path(str(row["filename"])).name[:191], "ownership": "campaign",
                "payload": location, "journalId": row.get("journal_id"),
                "folderId": row.get("folder_id"), "purpose": str(row.get("purpose") or "journal_image")[:80],
            })
            blobs[location] = data
        self._rewrite_journal_documents(content, id_map)
        for row in content.get("pdf_annotations", []):
            if str(row.get("document_id")) in id_map:
                row["document_id"] = id_map[str(row["document_id"])]
        return entries, blobs

    @staticmethod
    def _rewrite_journal_documents(content: dict, id_map: dict[str, str]) -> None:
        def visit(value: object) -> None:
            if isinstance(value, dict):
                if value.get("kind") == "pdf":
                    old = str(value.get("assetId") or value.get("asset_id") or "")
                    if old in id_map:
                        value.pop("asset_id", None)
                        value["assetId"] = id_map[old]
                        value["src"] = f"/game/journal/asset/{id_map[old]}"
                if value.get("type") == "gwImage" and isinstance(value.get("attrs"), dict):
                    attrs = value["attrs"]
                    old = str(attrs.get("assetId") or attrs.get("asset_id") or "")
                    if old in id_map:
                        attrs.pop("asset_id", None)
                        attrs["assetId"] = id_map[old]
                        attrs["src"] = f"/game/journal/asset/{id_map[old]}"
                if value.get("type") == "link" and isinstance(value.get("attrs"), dict):
                    href = str(value["attrs"].get("href") or "")
                    match = TOKEN_ASSET_URL.fullmatch(href)
                    if match and match.group(1) in id_map:
                        value["attrs"]["href"] = f"/game/journal/asset/{id_map[match.group(1)]}"
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        for row in content.get("journals", []):
            raw = row.get("data_json")
            if not isinstance(raw, str):
                continue
            try:
                document = __import__("json").loads(raw)
            except ValueError:
                continue
            visit(document)
            row["data_json"] = __import__("json").dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def _collect_rasters(self, connection, scene_ids: list[str]) -> tuple[list[dict], dict[str, bytes]]:
        if not scene_ids:
            return [], {}
        scene_rows = {str(row["id"]): dict(row) for row in connection.execute(select(scenes).where(scenes.c.id.in_(scene_ids))).mappings()}
        layer_rows = [dict(row) for row in connection.execute(select(scene_layers).where(scene_layers.c.scene_id.in_(scene_ids))).mappings()]
        layers_by_scene: dict[str, list[dict]] = {}
        for row in layer_rows:
            layers_by_scene.setdefault(str(row["scene_id"]), []).append(row)
        asset_rows = [dict(row) for row in connection.execute(select(scene_assets).where(scene_assets.c.scene_id.in_(scene_ids))).mappings()]
        assets_by_scene: dict[str, list[dict]] = {}
        for row in asset_rows:
            assets_by_scene.setdefault(str(row["scene_id"]), []).append(row)
        tile_rows = [dict(row) for row in connection.execute(select(scene_tiles).where(scene_tiles.c.scene_id.in_(scene_ids))).mappings()]
        chunk_rows = [dict(row) for row in connection.execute(select(scene_chunks).where(scene_chunks.c.scene_id.in_(scene_ids))).mappings()]
        chunks = LocalChunkStorage()
        validator = AssetIngestionService()
        blobs: dict[str, bytes] = {}
        rasters: list[dict] = []
        for scene_id in sorted(scene_ids):
            raster_id = f"raster-{len(rasters)+1:06d}"
            physical = assets_by_scene.get(scene_id, [])
            related_tiles = [row for row in tile_rows if str(row["scene_id"]) == scene_id]
            related_chunks = [row for row in chunk_rows if str(row["scene_id"]) == scene_id]
            if not physical and not related_tiles and not related_chunks:
                continue
            asset_map = {str(row["id"]): f"component-{index:06d}" for index, row in enumerate(sorted(physical, key=lambda r: str(r["id"])), 1)}
            components = []
            for row in sorted(physical, key=lambda r: str(r["id"])):
                component_id = asset_map[str(row["id"])]
                data = _registered_path(str(row["storage_path"])).read_bytes()
                checked = _validate_payload(validator, data=data, media_type_hint=str(row.get("content_type") or ""))
                digest = hashlib.sha256(data).hexdigest()
                if not checked.success or digest != str(row["hash"]) or len(data) != int(row["byte_size"]):
                    raise PortableAssetError("raster component validation failed")
                location = f"rasters/{raster_id}/{component_id}.payload"
                components.append({"id": component_id, "kind": str(row["kind"]), "digest": digest,
                                   "bytes": len(data), "mediaTypeHint": checked.payload["contentType"],
                                   "width": row.get("width"), "height": row.get("height"), "payload": location})
                blobs[location] = data
            portable_chunks = []
            for index, row in enumerate(sorted(related_chunks, key=lambda r: (str(r["layer_id"]), int(r["lod"]), int(r["cy"]), int(r["cx"]))), 1):
                data = chunks.read_chunk(scene_id=scene_id, layer_id=str(row["layer_id"]), cx=int(row["cx"]), cy=int(row["cy"]))
                if data is None or len(data) != int(row["byte_size"]) or hashlib.sha256(data).hexdigest() != str(row["hash"]):
                    raise PortableAssetError("raster chunk validation failed")
                location = f"rasters/{raster_id}/chunk-{index:06d}.payload"
                portable_chunks.append({"layerId": row["layer_id"], "cx": row["cx"], "cy": row["cy"], "lod": row["lod"],
                                        "version": row["version"], "encoding": row["encoding"], "digest": row["hash"],
                                        "bytes": row["byte_size"], "payload": location})
                blobs[location] = data
            portable_tiles = [{"layerId": row["layer_id"], "tileRef": row["tile_ref"], "lod": row["lod"],
                               "componentId": asset_map.get(str(row["asset_id"])), "tx": row["tx"], "ty": row["ty"],
                               "width": row["width"], "height": row["height"], "digest": row["hash"],
                               "bytes": row["byte_size"]} for row in related_tiles]
            if any(not row["componentId"] for row in portable_tiles):
                raise PortableAssetError("raster tile graph is not closed")
            scene = scene_rows[scene_id]
            rasters.append({"id": raster_id, "sceneId": scene_id,
                            "payloadStrategy": "BUNDLED_DERIVATIVES", "processingVersion": int(scene.get("raster_policy_version") or 0),
                            "rasterMetadata": {"width": scene["width"], "height": scene["height"], "tileSize": scene["tile_size"], "chunkSpan": scene["chunk_size"]},
                            "components": components, "tiles": portable_tiles, "chunks": portable_chunks})
        return rasters, blobs

    @staticmethod
    def _rewrite(content: dict[str, list[dict]], id_map: dict[str, str]) -> None:
        for table_name, fields in REFERENCE_FIELDS.items():
            for row in content.get(table_name, []):
                for field in fields:
                    if row.get(field): row[field] = id_map[str(row[field])]
        for row in content.get("tokens", []):
            match = TOKEN_ASSET_URL.fullmatch(str(row.get("token_asset_url") or ""))
            if match: row["token_asset_url"] = f"/game/assets/file/{id_map[match.group(1)]}"


def validate_asset_manifest(manifest: object, blobs: dict[str, bytes]) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict) or manifest.get("version") not in {LEGACY_ASSET_MANIFEST_VERSION, ASSET_MANIFEST_VERSION}:
        raise PortableAssetError("unsupported asset manifest version")
    entries = manifest.get("assets")
    if not isinstance(entries, list) or len(entries) > MAX_ASSETS:
        raise PortableAssetError("invalid asset manifest")
    seen, total, valid = set(), 0, []
    validator = AssetIngestionService()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id","digest","bytes","mediaTypeHint","filename","ownership","payload"}:
            raise PortableAssetError("invalid asset entry")
        export_id, location = entry.get("id"), entry.get("payload")
        if not isinstance(export_id, str) or not re.fullmatch(r"asset-[0-9]{6}", export_id) or export_id in seen:
            raise PortableAssetError("invalid asset identity")
        if location != f"assets/{export_id}.payload" or location not in blobs or entry.get("ownership") != "campaign":
            raise PortableAssetError("missing asset payload")
        data = blobs[location]; total += len(data)
        if total > MAX_TOTAL_BYTES or entry.get("bytes") != len(data) or hashlib.sha256(data).hexdigest() != entry.get("digest"):
            raise PortableAssetError("asset integrity mismatch")
        checked = validator.validate_portable_payload(data=data, media_type_hint=str(entry.get("mediaTypeHint") or ""))
        if not checked.success: raise PortableAssetError("asset content invalid")
        seen.add(export_id); valid.append({**entry,"validated":checked.payload,"data":data})
    if manifest.get("version") == LEGACY_ASSET_MANIFEST_VERSION:
        if set(blobs) != {str(entry["payload"]) for entry in entries}:
            raise PortableAssetError("unexpected asset payload")
        return valid
    journals = _validate_special_entries(manifest.get("journalAttachments"), blobs, "journal")
    rasters = _validate_rasters(manifest.get("rasters"), blobs)
    expected = {str(entry["payload"]) for entry in entries}
    expected.update(str(entry["payload"]) for entry in journals)
    for raster in rasters:
        expected.update(str(item["payload"]) for item in raster["components"])
        expected.update(str(item["payload"]) for item in raster["chunks"])
    if set(blobs) != expected:
        raise PortableAssetError("unexpected asset payload")
    return valid + [{"portableKind": "journal", **entry} for entry in journals] + [{"portableKind": "raster", **entry} for entry in rasters]


def _validate_special_entries(value: object, blobs: dict[str, bytes], prefix: str) -> list[dict]:
    if not isinstance(value, list) or len(value) > MAX_ASSETS:
        raise PortableAssetError("invalid journal attachment manifest")
    seen, result = set(), []
    validator = AssetIngestionService()
    required = {"id","digest","bytes","mediaTypeHint","filename","ownership","payload","journalId","folderId","purpose"}
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != required:
            raise PortableAssetError("invalid journal attachment entry")
        identity = str(entry.get("id") or "")
        location = str(entry.get("payload") or "")
        if not re.fullmatch(rf"{prefix}-[0-9]{{6}}", identity) or identity in seen or location != f"assets/{identity}.payload" or location not in blobs:
            raise PortableAssetError("invalid journal attachment identity")
        data = blobs[location]
        checked = validator.validate_portable_payload(data=data, media_type_hint=str(entry.get("mediaTypeHint") or ""))
        if entry.get("ownership") != "campaign" or not checked.success or len(data) != entry.get("bytes") or hashlib.sha256(data).hexdigest() != entry.get("digest"):
            raise PortableAssetError("journal attachment integrity mismatch")
        seen.add(identity)
        result.append({**entry, "validated": checked.payload, "data": data})
    return result


def _validate_rasters(value: object, blobs: dict[str, bytes]) -> list[dict]:
    if not isinstance(value, list) or len(value) > 10_000:
        raise PortableAssetError("invalid raster manifest")
    validator = AssetIngestionService()
    seen, result = set(), []
    for raster in value:
        if not isinstance(raster, dict) or set(raster) != {"id","sceneId","payloadStrategy","processingVersion","rasterMetadata","components","tiles","chunks"}:
            raise PortableAssetError("invalid raster entry")
        identity = str(raster.get("id") or "")
        if not re.fullmatch(r"raster-[0-9]{6}", identity) or identity in seen or raster.get("payloadStrategy") != "BUNDLED_DERIVATIVES":
            raise PortableAssetError("invalid raster identity")
        components = raster.get("components"); tiles = raster.get("tiles"); chunks = raster.get("chunks")
        if not all(isinstance(x, list) for x in (components, tiles, chunks)) or len(components)+len(chunks) > MAX_ASSETS:
            raise PortableAssetError("invalid raster graph")
        component_ids = set()
        checked_components=[]
        for component in components:
            required={"id","kind","digest","bytes","mediaTypeHint","width","height","payload"}
            if not isinstance(component,dict) or set(component)!=required or component["id"] in component_ids:
                raise PortableAssetError("invalid raster component")
            location=str(component["payload"]); data=blobs.get(location)
            checked=validator.validate_portable_payload(data=data or b"",media_type_hint=str(component["mediaTypeHint"]))
            if data is None or not checked.success or len(data)!=component["bytes"] or hashlib.sha256(data).hexdigest()!=component["digest"]:
                raise PortableAssetError("raster component integrity mismatch")
            component_ids.add(component["id"]); checked_components.append({**component,"validated":checked.payload,"data":data})
        tile_keys=set()
        component_by_id={component["id"]:component for component in checked_components}
        for tile in tiles:
            required={"layerId","tileRef","lod","componentId","tx","ty","width","height","digest","bytes"}
            key=(tile.get("layerId"),tile.get("lod"),tile.get("tx"),tile.get("ty")) if isinstance(tile,dict) else None
            if not isinstance(tile,dict) or set(tile)!=required or tile.get("componentId") not in component_ids or key in tile_keys:
                raise PortableAssetError("invalid raster tile")
            component=component_by_id[tile["componentId"]]
            if component.get("kind")!="raster_tile" or tile["digest"]!=component["digest"] or tile["bytes"]!=component["bytes"]:
                raise PortableAssetError("raster tile component mismatch")
            tile_keys.add(key)
        checked_chunks=[]; chunk_keys=set()
        for chunk in chunks:
            required={"layerId","cx","cy","lod","version","encoding","digest","bytes","payload"}
            key=(chunk.get("layerId"),chunk.get("lod"),chunk.get("cx"),chunk.get("cy")) if isinstance(chunk,dict) else None
            if not isinstance(chunk,dict) or set(chunk)!=required or key in chunk_keys:
                raise PortableAssetError("invalid raster chunk")
            data=blobs.get(str(chunk["payload"]))
            if data is None or len(data)!=chunk["bytes"] or hashlib.sha256(data).hexdigest()!=chunk["digest"]:
                raise PortableAssetError("raster chunk integrity mismatch")
            chunk_keys.add(key); checked_chunks.append({**chunk,"data":data})
        if len(tile_keys) != len(tiles) or len(chunk_keys) != len(chunks):
            raise PortableAssetError("incomplete raster graph")
        metadata=raster.get("rasterMetadata")
        if not isinstance(metadata,dict) or set(metadata)!={"width","height","tileSize","chunkSpan"}:
            raise PortableAssetError("invalid raster metadata")
        try:
            columns=math.ceil(int(metadata["width"])/int(metadata["tileSize"])); rows=math.ceil(int(metadata["height"])/int(metadata["tileSize"]))
            chunk_columns=math.ceil(columns/int(metadata["chunkSpan"])); chunk_rows=math.ceil(rows/int(metadata["chunkSpan"]))
        except (TypeError,ValueError,ZeroDivisionError):
            raise PortableAssetError("invalid raster dimensions")
        expected_tiles={(layer,0,x,y) for layer in {tile["layerId"] for tile in tiles} for y in range(rows) for x in range(columns)}
        expected_chunks={(layer,0,x,y) for layer in {chunk["layerId"] for chunk in chunks} for y in range(chunk_rows) for x in range(chunk_columns)}
        if {(layer,lod,tx,ty) for layer,lod,tx,ty in tile_keys} != expected_tiles or {(layer,lod,cx,cy) for layer,lod,cx,cy in chunk_keys} != expected_chunks:
            raise PortableAssetError("raster pyramid is incomplete")
        if sum(1 for component in components if component.get("kind")=="original_image") != 1:
            raise PortableAssetError("raster authoritative source is missing")
        seen.add(identity); result.append({**raster,"components":checked_components,"chunks":checked_chunks})
    return result
