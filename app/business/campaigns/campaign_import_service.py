from __future__ import annotations

import base64
import binascii
import io
import json
import os
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.business.campaigns.campaign_export_service import CampaignExportService
from app.business.campaigns.portable_asset_archive import validate_asset_manifest
from app.infrastructure.storage.local_asset_storage import LocalAssetStorage
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.helpers.env import PROJECT_ROOT
from app.persistence.tables import (
    actor_folders,
    actors_core,
    campaign_members,
    campaign_packages,
    campaign_permission_overrides,
    campaigns,
    installed_packages,
    item_folders,
    items_core,
    journal_folders,
    journals,
    quest_board_entries,
    scene_groups,
    scene_layers,
    scenes,
    journal_assets, library_assets, pdf_annotations, tokens, scene_image_placements,
    scene_assets, scene_tiles, scene_chunks,
    card_deck_definitions, card_definitions, card_deck_instances, card_piles,
    card_instances, card_pile_entries, scene_card_placements,
    sounds, sound_playlists, soundscapes, scene_spatial_sounds,
)

MAX_CAMPAIGN_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_CAMPAIGN_JSON_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 100_010


@dataclass(frozen=True)
class CampaignImportResult:
    success: bool
    campaign_id: str | None = None
    summary: dict[str, int] = field(default_factory=dict)
    error_key: str | None = None


class CampaignImportService:
    """Validate and transactionally restore a portable campaign export."""

    def import_archive(
        self, *, archive: bytes, user_id: str, title: str = ""
    ) -> CampaignImportResult:
        self.recover_incomplete_imports()
        if not archive or len(archive) > MAX_CAMPAIGN_ARCHIVE_BYTES:
            return self._invalid()
        asset_entries=[]
        archive_version=1
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                infos=bundle.infolist()
                names=[info.filename for info in infos]
                if len(infos)>MAX_ARCHIVE_ENTRIES or len(names)!=len(set(names)) or any(info.flag_bits & 1 for info in infos):
                    return self._invalid()
                if any(name.startswith(("/","\\")) or ".." in name.replace("\\","/").split("/") for name in names):
                    return self._invalid()
                if sum(info.file_size for info in infos)>MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    return self._invalid()
                if any(info.filename.startswith("assets/") and info.file_size>25*1024*1024 for info in infos):
                    return self._invalid()
                info = bundle.getinfo("campaign.json")
                if info.file_size > MAX_CAMPAIGN_JSON_BYTES:
                    return self._invalid()
                if not CampaignExportService.validate(archive):
                    return self._invalid()
                payload = json.loads(bundle.read(info))
                archive_version=int(payload.get("version") or 0)
                if archive_version==2:
                    asset_manifest=json.loads(bundle.read("assets.json"))
                    locations=[name for name in names if name.startswith(("assets/", "rasters/"))]
                    blobs={str(location):bundle.read(str(location)) for location in locations}
                    asset_entries=validate_asset_manifest(asset_manifest,blobs)
                elif archive_version!=1:
                    return self._invalid()
        except (KeyError, TypeError, ValueError, zipfile.BadZipFile):
            return self._invalid()

        source_campaign = payload.get("campaign")
        content = payload.get("content")
        if not isinstance(source_campaign, dict) or not isinstance(content, dict):
            return self._invalid()
        imported_title = " ".join((title.strip() or str(source_campaign.get("title") or "")).split())
        if not 2 <= len(imported_title) <= 120:
            return CampaignImportResult(False, error_key="campaign.import.errors.invalid_title")

        now = int(time.time())
        campaign_id = uuid.uuid4().hex
        ordinary_entries=[entry for entry in asset_entries if not entry.get("portableKind")]
        journal_entries=[entry for entry in asset_entries if entry.get("portableKind")=="journal"]
        raster_entries=[entry for entry in asset_entries if entry.get("portableKind")=="raster"]
        asset_id_map={str(entry["id"]):uuid.uuid4().hex for entry in ordinary_entries}
        journal_asset_map={str(entry["id"]):uuid.uuid4().hex for entry in journal_entries}
        scene_map={str(row.get("id")):uuid.uuid4().hex for row in self._rows(content, scenes.name)}
        layer_map={str(row.get("id")):uuid.uuid4().hex for row in self._rows(content, scene_layers.name)}
        journal_map={str(row.get("id")):uuid.uuid4().hex for row in self._rows(content, journals.name)}
        journal_folder_map={str(row.get("id")):uuid.uuid4().hex for row in self._rows(content, journal_folders.name)}
        storage=LocalAssetStorage()
        journal_storage=LocalJournalAssetStorage()
        scene_storage=LocalSceneAssetStorage()
        chunk_storage=LocalChunkStorage()
        marker=self._write_recovery_marker(campaign_id=campaign_id,scene_ids=list(scene_map.values()),phase="IMPORTING")
        written=[]
        journal_written=[]
        raster_written=[]
        try:
            for entry in ordinary_entries:
                asset_id=asset_id_map[str(entry["id"])]
                extension=str(entry["validated"]["extension"])
                filename=(str(entry.get("filename") or "asset").rsplit(".",1)[0] or "asset")+extension
                path=storage.write_image(campaign_id=campaign_id,asset_id=asset_id,filename=filename,data=entry["data"])
                written.append((entry,asset_id,filename,path))
            for entry in journal_entries:
                asset_id=journal_asset_map[str(entry["id"])]
                extension=str(entry["validated"]["extension"])
                filename=(str(entry.get("filename") or "attachment").rsplit(".",1)[0] or "attachment")+extension
                path=journal_storage.write_image(campaign_id=campaign_id,asset_id=asset_id,filename=filename,data=entry["data"])
                journal_written.append((entry,asset_id,filename,path))
            for raster in raster_entries:
                new_scene=scene_map.get(str(raster.get("sceneId")))
                if not new_scene:
                    raise ValueError("unresolved raster scene")
                component_map={str(component["id"]):uuid.uuid4().hex for component in raster["components"]}
                stored_components=[]
                for component in raster["components"]:
                    component_id=component_map[str(component["id"])]
                    extension=str(component["validated"]["extension"])
                    if component["kind"]=="original_image":
                        path=scene_storage.write_original(scene_id=new_scene,filename=f"source{extension}",data=component["data"])
                    else:
                        tile=next((row for row in raster["tiles"] if row["componentId"]==component["id"]),None)
                        if tile is None or str(tile["layerId"]) not in layer_map:
                            raise ValueError("orphan raster component")
                        path=scene_storage.write_tile_bytes(scene_id=new_scene,layer_id=layer_map[str(tile["layerId"])],tx=int(tile["tx"]),ty=int(tile["ty"]),data=component["data"],extension=extension)
                    stored_components.append((component,component_id,path))
                for chunk in raster["chunks"]:
                    new_layer=layer_map.get(str(chunk["layerId"]))
                    if not new_layer:
                        raise ValueError("unresolved raster chunk layer")
                    digest=chunk_storage.write_chunk(scene_id=new_scene,layer_id=new_layer,cx=int(chunk["cx"]),cy=int(chunk["cy"]),data=chunk["data"])
                    if digest!=chunk["digest"]:
                        raise ValueError("raster chunk publish mismatch")
                raster_written.append((raster,new_scene,component_map,stored_components))
            self._write_recovery_marker(campaign_id=campaign_id,scene_ids=list(scene_map.values()),phase="PHYSICAL_COMPLETE")
        except (OSError,ValueError):
            storage.delete_campaign(campaign_id=campaign_id)
            journal_storage.delete_campaign(campaign_id=campaign_id)
            for new_scene in scene_map.values(): scene_storage.delete_scene(scene_id=new_scene)
            marker.unlink(missing_ok=True)
            return self._invalid()
        summary: dict[str, int] = {}
        try:
            with engine_begin() as connection:
                available_packages = set(
                    connection.execute(select(installed_packages.c.id)).scalars()
                )
                exported_packages = self._rows(content, campaign_packages.name)
                active_system_id = source_campaign.get("active_system_id")
                if active_system_id not in available_packages:
                    active_system_id = None
                connection.execute(insert(campaigns).values(
                    id=campaign_id,
                    owner_user_id=user_id,
                    title=imported_title,
                    description=str(source_campaign.get("description") or "")[:2000],
                    active_system_id=active_system_id,
                    initial_state_json=str(source_campaign.get("initial_state_json") or "{}"),
                    persistent_state_json=str(source_campaign.get("persistent_state_json") or "{}"),
                    state_version=int(source_campaign.get("state_version") or 1),
                    created_at=now,
                    updated_at=now,
                ))
                connection.execute(insert(campaign_members).values(
                    id=uuid.uuid4().hex,
                    campaign_id=campaign_id,
                    user_id=user_id,
                    role="gm",
                    created_at=now,
                    updated_at=now,
                ))

                for entry,asset_id,filename,storage_path in written:
                    checked=entry["validated"]
                    connection.execute(insert(library_assets).values(
                        id=asset_id,campaign_id=campaign_id,owner_user_id=user_id,folder_id=None,
                        filename=filename,content_type=checked["contentType"],byte_size=entry["bytes"],
                        width=checked.get("width"),height=checked.get("height"),storage_path=storage_path,
                        hash=entry["digest"],created_at=now,
                    ))
                summary["assets"]=len(written)

                summary["settings"] = self._simple_rows(
                    connection, content, campaign_permission_overrides, campaign_id, user_id, now
                )
                summary["packages"] = 0
                for raw in exported_packages:
                    if raw.get("package_id") not in available_packages:
                        continue
                    row = self._fit(campaign_packages, raw)
                    row.update(campaign_id=campaign_id, enabled_by_user_id=user_id, enabled_at=now)
                    connection.execute(insert(campaign_packages).values(**row))
                    summary["packages"] += 1

                summary["actors"],actor_map = self._tree(
                    connection, content, actor_folders, actors_core, campaign_id, user_id, now,
                    clear_fields=("portrait_asset_id", "token_asset_id") if archive_version==1 else (), asset_map=asset_id_map,
                )
                summary["items"],item_map = self._tree(
                    connection, content, item_folders, items_core, campaign_id, user_id, now,
                    clear_fields=("portrait_asset_id",) if archive_version==1 else (), asset_map=asset_id_map,
                )
                self._rewrite_journal_documents(content,journal_asset_map)
                journal_map, journal_count = self._journals(
                    connection, content, campaign_id, user_id, now, journal_map=journal_map,
                    folder_map=journal_folder_map,
                )
                summary["journals"] = journal_count
                summary["quest_board_entries"] = self._quest_links(
                    connection, content, journal_map, now
                )
                scene_map,layer_map,summary["scenes"] = self._scenes(
                    connection, content, campaign_id, user_id, now, scene_map=scene_map, layer_map=layer_map
                )
                if archive_version==2:
                    summary.update(self._portable_state(connection,content,campaign_id,user_id,now,asset_id_map,scene_map,actor_map,journal_map,journal_asset_map))
                    for entry,asset_id,filename,storage_path in journal_written:
                        connection.execute(insert(journal_assets).values(
                            id=asset_id,campaign_id=campaign_id,journal_id=journal_map.get(str(entry.get("journalId"))),
                            folder_id=journal_folder_map.get(str(entry.get("folderId"))),owner_user_id=user_id,purpose=entry["purpose"],filename=filename,
                            content_type=entry["validated"]["contentType"],byte_size=entry["bytes"],
                            width=entry["validated"].get("width"),height=entry["validated"].get("height"),
                            storage_path=storage_path,hash=entry["digest"],created_at=now,
                        ))
                    summary["journal_assets"]=len(journal_written)
                    summary["scene_rasters"]=self._publish_rasters(connection,raster_written,layer_map,now)
        except (KeyError, TypeError, ValueError, binascii.Error, SQLAlchemyError):
            storage.delete_campaign(campaign_id=campaign_id)
            journal_storage.delete_campaign(campaign_id=campaign_id)
            for new_scene in scene_map.values(): scene_storage.delete_scene(scene_id=new_scene)
            marker.unlink(missing_ok=True)
            return self._invalid()
        marker.unlink(missing_ok=True)
        return CampaignImportResult(True, campaign_id=campaign_id, summary=summary)

    @staticmethod
    def _recovery_root() -> Path:
        test_root=os.environ.get("GRAVEWRIGHT_TEST_TEMP_ROOT","").strip()
        return (Path(test_root) if test_root else PROJECT_ROOT / "storage") / "campaign-import-staging"

    @classmethod
    def _write_recovery_marker(cls, *, campaign_id: str, scene_ids: list[str], phase: str) -> Path:
        root=cls._recovery_root(); root.mkdir(parents=True,exist_ok=True)
        marker=root / f"{campaign_id}.json"; temporary=root / f".{campaign_id}.{uuid.uuid4().hex}.tmp"
        payload=json.dumps({"version":1,"campaignId":campaign_id,"sceneIds":scene_ids,"phase":phase},separators=(",",":"),sort_keys=True)
        try:
            with temporary.open("w",encoding="utf-8",newline="\n") as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,marker)
        finally:
            temporary.unlink(missing_ok=True)
        return marker

    @classmethod
    def recover_incomplete_imports(cls) -> None:
        root=cls._recovery_root()
        if not root.exists(): return
        for marker in root.glob("*.json"):
            try:
                value=json.loads(marker.read_text(encoding="utf-8"))
                campaign_id=str(value.get("campaignId") or "")
                scene_ids=value.get("sceneIds")
                if not campaign_id or not isinstance(scene_ids,list) or not all(isinstance(item,str) for item in scene_ids):
                    marker.unlink(missing_ok=True); continue
                with engine_connect() as connection:
                    published=connection.execute(select(campaigns.c.id).where(campaigns.c.id==campaign_id)).scalar_one_or_none()
                if published is None:
                    LocalAssetStorage().delete_campaign(campaign_id=campaign_id)
                    LocalJournalAssetStorage().delete_campaign(campaign_id=campaign_id)
                    for scene_id in scene_ids: LocalSceneAssetStorage().delete_scene(scene_id=scene_id)
                marker.unlink(missing_ok=True)
            except (OSError,TypeError,ValueError):
                # A malformed marker grants no deletion authority. Keep it for
                # operator inspection instead of deriving a filesystem target.
                continue

    @staticmethod
    def _invalid() -> CampaignImportResult:
        return CampaignImportResult(False, error_key="campaign.import.errors.invalid")

    @staticmethod
    def _rows(content: dict[str, Any], name: str) -> list[dict[str, Any]]:
        rows = content.get(name, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"invalid table {name}")
        return rows

    @classmethod
    def _fit(cls, table, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            key: cls._decode(value)
            for key, value in raw.items()
            if key in table.c
        }

    @classmethod
    def _decode(cls, value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {"$base64"}:
            return base64.b64decode(value["$base64"], validate=True)
        return value

    def _simple_rows(self, connection, content, table, campaign_id, user_id, now) -> int:
        count = 0
        for raw in self._rows(content, table.name):
            row = self._fit(table, raw)
            row.update(campaign_id=campaign_id, created_at=now, updated_at=now)
            if "id" in table.c:
                row["id"] = uuid.uuid4().hex
            if "created_by_user_id" in table.c:
                row["created_by_user_id"] = user_id
            connection.execute(insert(table).values(**row))
            count += 1
        return count

    def _tree(self, connection, content, folder_table, resource_table, campaign_id,
              user_id, now, clear_fields=(), asset_map=None) -> int:
        folders = self._rows(content, folder_table.name)
        folder_map = {str(row.get("id")): uuid.uuid4().hex for row in folders}
        for raw in folders:
            row = self._fit(folder_table, raw)
            row.update(id=folder_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["parent_id"] = folder_map.get(str(raw.get("parent_id")))
            connection.execute(insert(folder_table).values(**row))
        resource_map={str(row.get("id")):uuid.uuid4().hex for row in self._rows(content,resource_table.name)}
        count = 0
        for raw in self._rows(content, resource_table.name):
            row = self._fit(resource_table, raw)
            row.update(id=resource_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["folder_id"] = folder_map.get(str(raw.get("folder_id")))
            for field_name in clear_fields:
                row[field_name] = None
            for field_name in ("portrait_asset_id","token_asset_id"):
                if field_name in row and row.get(field_name):
                    row[field_name]=(asset_map or {}).get(str(row[field_name]))
                    if not row[field_name]: raise ValueError("unresolved asset reference")
            connection.execute(insert(resource_table).values(**row))
            count += 1
        return count,resource_map

    def _journals(self, connection, content, campaign_id, user_id, now, journal_map=None, folder_map=None):
        folders = self._rows(content, journal_folders.name)
        folder_map = folder_map or {str(row.get("id")): uuid.uuid4().hex for row in folders}
        for raw in folders:
            row = self._fit(journal_folders, raw)
            row.update(id=folder_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["parent_id"] = folder_map.get(str(raw.get("parent_id")))
            connection.execute(insert(journal_folders).values(**row))
        originals = self._rows(content, journals.name)
        journal_map = journal_map or {str(row.get("id")): uuid.uuid4().hex for row in originals}
        for raw in originals:
            row = self._fit(journals, raw)
            row.update(id=journal_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["folder_id"] = folder_map.get(str(raw.get("folder_id")))
            connection.execute(insert(journals).values(**row))
        return journal_map, len(originals)

    def _quest_links(self, connection, content, journal_map, now):
        count = 0
        for raw in self._rows(content, quest_board_entries.name):
            board_id = journal_map.get(str(raw.get("board_id")))
            quest_id = journal_map.get(str(raw.get("quest_id")))
            if not board_id or not quest_id:
                continue
            row = self._fit(quest_board_entries, raw)
            row.update(board_id=board_id, quest_id=quest_id, created_at=now)
            connection.execute(insert(quest_board_entries).values(**row))
            count += 1
        return count

    def _scenes(self, connection, content, campaign_id, user_id, now, scene_map=None, layer_map=None):
        groups = self._rows(content, scene_groups.name)
        group_map = {str(row.get("id")): uuid.uuid4().hex for row in groups}
        for raw in groups:
            row = self._fit(scene_groups, raw)
            row.update(id=group_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_at=now, updated_at=now)
            connection.execute(insert(scene_groups).values(**row))
        originals = self._rows(content, scenes.name)
        scene_map = scene_map or {str(row.get("id")): uuid.uuid4().hex for row in originals}
        layer_map = layer_map or {str(row.get("id")): uuid.uuid4().hex for row in self._rows(content, scene_layers.name)}
        for raw in originals:
            row = self._fit(scenes, raw)
            row.update(id=scene_map[str(raw.get("id"))], campaign_id=campaign_id,
                       group_id=group_map.get(str(raw.get("group_id"))), active=0,
                       status="draft", created_at=now, updated_at=now)
            if "created_by_user_id" in scenes.c:
                row["created_by_user_id"] = user_id
            connection.execute(insert(scenes).values(**row))
        count = len(originals)
        for raw in self._rows(content, scene_layers.name):
            scene_id = scene_map.get(str(raw.get("scene_id")))
            if not scene_id:
                continue
            row = self._fit(scene_layers, raw)
            row.update(id=layer_map[str(raw.get("id"))], scene_id=scene_id, created_at=now, updated_at=now)
            connection.execute(insert(scene_layers).values(**row))
        return scene_map,layer_map,count

    @staticmethod
    def _rewrite_journal_documents(content, asset_map):
        from app.business.campaigns.portable_asset_archive import PortableAssetGraph
        PortableAssetGraph._rewrite_journal_documents(content, asset_map)

    @staticmethod
    def _publish_rasters(connection, rasters, layer_map, now):
        count=0
        for raster,new_scene,component_map,stored_components in rasters:
            by_component={str(component["id"]):(component,asset_id,path) for component,asset_id,path in stored_components}
            for component,asset_id,path in stored_components:
                connection.execute(insert(scene_assets).values(
                    id=asset_id,scene_id=new_scene,kind=component["kind"],storage_path=path,
                    hash=component["digest"],byte_size=component["bytes"],width=component.get("width"),
                    height=component.get("height"),content_type=component["validated"]["contentType"],created_at=now,
                ))
            for tile in raster["tiles"]:
                new_layer=layer_map.get(str(tile["layerId"])); component=by_component.get(str(tile["componentId"]))
                if not new_layer or not component: raise ValueError("unresolved raster tile")
                connection.execute(insert(scene_tiles).values(
                    scene_id=new_scene,layer_id=new_layer,tile_ref=int(tile["tileRef"]),lod=int(tile["lod"]),
                    asset_id=component[1],tx=int(tile["tx"]),ty=int(tile["ty"]),width=int(tile["width"]),
                    height=int(tile["height"]),hash=tile["digest"],byte_size=int(tile["bytes"]),created_at=now,
                ))
            for chunk in raster["chunks"]:
                new_layer=layer_map.get(str(chunk["layerId"]))
                if not new_layer: raise ValueError("unresolved raster chunk")
                connection.execute(insert(scene_chunks).values(
                    id=uuid.uuid4().hex,scene_id=new_scene,layer_id=new_layer,cx=int(chunk["cx"]),cy=int(chunk["cy"]),
                    lod=int(chunk["lod"]),version=int(chunk["version"]),hash=chunk["digest"],byte_size=int(chunk["bytes"]),
                    encoding=chunk["encoding"],created_at=now,updated_at=now,
                ))
            count+=1
        return count

    def _portable_state(self, connection, content, campaign_id, user_id, now, asset_map, scene_map, actor_map, journal_map, journal_asset_map=None):
        required=lambda mapping,value: mapping.get(str(value)) if value is not None else None
        counts={}
        for raw in self._rows(content,"tokens"):
            row=self._fit(tokens,raw); old_url=str(row.get("token_asset_url") or "")
            if old_url.startswith("/game/assets/file/"):
                portable=old_url.rsplit("/",1)[-1]; mapped=required(asset_map,portable)
                if not mapped: raise ValueError("unresolved token asset")
                row["token_asset_url"]=f"/game/assets/file/{mapped}"
            row.update(id=uuid.uuid4().hex,scene_id=required(scene_map,raw.get("scene_id")),actor_id=required(actor_map,raw.get("actor_id")),created_at=now,updated_at=now)
            if not row["scene_id"]: raise ValueError("unresolved token scene")
            connection.execute(insert(tokens).values(**row))
        counts["tokens"]=len(self._rows(content,"tokens"))

        for raw in self._rows(content,"scene_image_placements"):
            row=self._fit(scene_image_placements,raw); mapped=required(asset_map,raw.get("asset_id")); scene=required(scene_map,raw.get("scene_id"))
            if not mapped or not scene: raise ValueError("unresolved scene image")
            row.update(id=uuid.uuid4().hex,campaign_id=campaign_id,scene_id=scene,asset_id=mapped,owner_user_id=user_id,created_at=now,updated_at=now)
            connection.execute(insert(scene_image_placements).values(**row))
        counts["scene_images"]=len(self._rows(content,"scene_image_placements"))

        sound_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"sounds")}
        for raw in self._rows(content,"sounds"):
            asset=required(asset_map,raw.get("asset_id"))
            if not asset: raise ValueError("unresolved Sound asset")
            row=self._fit(sounds,raw);row.update(id=sound_map[str(raw.get("id"))],campaign_id=campaign_id,asset_id=asset,created_at=now,updated_at=now)
            connection.execute(insert(sounds).values(**row))
        def rewrite_sound_ids(value):
            decoded=json.loads(value or "[]")
            def walk(node):
                if isinstance(node,dict):
                    for key,item in list(node.items()): node[key]=required(sound_map,item) if key=="soundId" else [required(sound_map,x) for x in item] if key=="soundIds" and isinstance(item,list) else walk(item)
                elif isinstance(node,list):
                    for index,item in enumerate(node): node[index]=walk(item)
                return node
            return json.dumps(walk(decoded),ensure_ascii=False,separators=(",",":"))
        soundscape_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"soundscapes")}
        for table,mapping,json_fields in ((sound_playlists,{str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"sound_playlists")},("entries_json",)),(soundscapes,soundscape_map,("layers_json","random_pools_json"))):
            for raw in self._rows(content,table.name):
                row=self._fit(table,raw);row.update(id=mapping[str(raw.get("id"))],campaign_id=campaign_id,created_at=now,updated_at=now)
                for json_field in json_fields: row[json_field]=rewrite_sound_ids(raw.get(json_field))
                connection.execute(insert(table).values(**row))
        for raw in self._rows(content,"scene_spatial_sounds"):
            scene=required(scene_map,raw.get("scene_id"));sound=required(sound_map,raw.get("sound_id"))
            if not scene or not sound: raise ValueError("unresolved Spatial Sound")
            row=self._fit(scene_spatial_sounds,raw);row.update(id=uuid.uuid4().hex,scene_id=scene,sound_id=sound,created_at=now,updated_at=now)
            connection.execute(insert(scene_spatial_sounds).values(**row))
        for raw in self._rows(content,"scenes"):
            old=raw.get("soundscape_id")
            if old: connection.execute(update(scenes).where(scenes.c.id==required(scene_map,raw.get("id"))).values(soundscape_id=required(soundscape_map,old)))
        counts["sounds"]=len(sound_map);counts["soundscapes"]=len(soundscape_map);counts["spatial_sounds"]=len(self._rows(content,"scene_spatial_sounds"))

        deck_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"card_deck_definitions")}
        for raw in self._rows(content,"card_deck_definitions"):
            row=self._fit(card_deck_definitions,raw); back=raw.get("default_back_asset_id")
            row.update(id=deck_map[str(raw.get("id"))],campaign_id=campaign_id,owner_user_id=user_id,default_back_asset_id=required(asset_map,back),editable=0,created_at=now,updated_at=now)
            if back and not row["default_back_asset_id"]: raise ValueError("unresolved deck artwork")
            connection.execute(insert(card_deck_definitions).values(**row))
        card_definition_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"card_definitions")}
        for raw in self._rows(content,"card_definitions"):
            row=self._fit(card_definitions,raw); front=required(asset_map,raw.get("front_asset_id")); back=required(asset_map,raw.get("back_asset_id"))
            if not front or not required(deck_map,raw.get("deck_definition_id")): raise ValueError("unresolved card definition")
            row.update(id=card_definition_map[str(raw.get("id"))],deck_definition_id=required(deck_map,raw.get("deck_definition_id")),front_asset_id=front,back_asset_id=back,created_at=now,updated_at=now)
            connection.execute(insert(card_definitions).values(**row))
        deck_instance_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"card_deck_instances")}
        for raw in self._rows(content,"card_deck_instances"):
            definition=required(deck_map,raw.get("deck_definition_id"))
            if not definition: raise ValueError("unresolved deck instance")
            row=self._fit(card_deck_instances,raw); row.update(id=deck_instance_map[str(raw.get("id"))],campaign_id=campaign_id,room_id=campaign_id,deck_definition_id=definition,owner_user_id=user_id if raw.get("portablePrincipal") else None,created_at=now,updated_at=now)
            connection.execute(insert(card_deck_instances).values(**row))
        pile_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"card_piles")}
        for raw in self._rows(content,"card_piles"):
            row=self._fit(card_piles,raw); row.update(id=pile_map[str(raw.get("id"))],campaign_id=campaign_id,deck_instance_id=required(deck_instance_map,raw.get("deck_instance_id")),owner_user_id=user_id if raw.get("portablePrincipal") else None,created_at=now,updated_at=now)
            connection.execute(insert(card_piles).values(**row))
        card_instance_map={str(raw.get("id")):uuid.uuid4().hex for raw in self._rows(content,"card_instances")}
        for raw in self._rows(content,"card_instances"):
            row=self._fit(card_instances,raw); row.update(id=card_instance_map[str(raw.get("id"))],campaign_id=campaign_id,deck_instance_id=required(deck_instance_map,raw.get("deck_instance_id")),card_definition_id=required(card_definition_map,raw.get("card_definition_id")),current_pile_id=required(pile_map,raw.get("current_pile_id")),current_scene_id=required(scene_map,raw.get("current_scene_id")),owner_user_id=user_id if raw.get("portablePrincipal") else None,created_at=now,updated_at=now)
            if not row["deck_instance_id"] or not row["card_definition_id"]: raise ValueError("unresolved card instance")
            connection.execute(insert(card_instances).values(**row))
        for raw in self._rows(content,"card_pile_entries"):
            pile=required(pile_map,raw.get("pile_id")); card=required(card_instance_map,raw.get("card_instance_id"))
            if not pile or not card: raise ValueError("unresolved pile entry")
            connection.execute(insert(card_pile_entries).values(pile_id=pile,card_instance_id=card,position=int(raw.get("position") or 0),inserted_at=now))
        for raw in self._rows(content,"scene_card_placements"):
            scene=required(scene_map,raw.get("scene_id")); card=required(card_instance_map,raw.get("card_instance_id"))
            if not scene or not card: raise ValueError("unresolved card placement")
            row=self._fit(scene_card_placements,raw); row.update(id=uuid.uuid4().hex,campaign_id=campaign_id,scene_id=scene,card_instance_id=card,owner_user_id=user_id if raw.get("portablePrincipal") else None,created_at=now,updated_at=now)
            connection.execute(insert(scene_card_placements).values(**row))
        counts["card_instances"]=len(card_instance_map)

        for raw in self._rows(content,"pdf_annotations"):
            document=required(asset_map,raw.get("document_id")) or required(journal_asset_map or {},raw.get("document_id"))
            if not document: raise ValueError("unresolved PDF")
            row=self._fit(pdf_annotations,raw); row.update(id=uuid.uuid4().hex,campaign_id=campaign_id,document_id=document,author_user_id=user_id,created_at=now,updated_at=now)
            connection.execute(insert(pdf_annotations).values(**row))
        counts["pdf_annotations"]=len(self._rows(content,"pdf_annotations"))
        return counts
