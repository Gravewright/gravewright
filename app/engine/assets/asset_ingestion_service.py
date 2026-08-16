"""Server-authoritative, campaign-owned SDK asset ingestion."""
from __future__ import annotations
import base64,binascii,time
from dataclasses import dataclass,field
from io import BytesIO
from PIL import Image,UnidentifiedImageError
from app.business.audit import AuditService
from app.engine.assets.asset_library_service import AssetLibraryService,MAX_ASSET_BYTES
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.security.asset_permissions import can_manage_assets

MAX_PIXELS=16_000_000
MAX_DECODED_BYTES=64*1024*1024
CAMPAIGN_QUOTA_BYTES=100*1024*1024
MAX_IMPORTS_PER_MINUTE=20
SIGNATURES={"image/png":lambda b:b.startswith(b"\x89PNG\r\n\x1a\n"),"image/jpeg":lambda b:b.startswith(b"\xff\xd8\xff"),"image/webp":lambda b:len(b)>=12 and b[:4]==b"RIFF" and b[8:12]==b"WEBP"}
EXTENSIONS={"image/png":".png","image/jpeg":".jpg","image/webp":".webp"}
PDF_MIME="application/pdf"
@dataclass(frozen=True)
class IngestionResult:
    success:bool; payload:dict=field(default_factory=dict);error_key:str|None=None
class AssetIngestionService:
    def __init__(self):self.library=AssetLibraryService();self.assets=AssetRepository();self.campaigns=CampaignRepository();self.audit=AuditService()
    def ingest(self,*,campaign_id,user_id,package_id,source):
        role=self.campaigns.get_member_role(campaign_id=campaign_id,user_id=user_id)
        if not can_manage_assets(actor_role=role):return self._failure(campaign_id,user_id,package_id,"PERMISSION_DENIED")
        if not isinstance(source,dict) or source.get("kind")!="browser-file":return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        name=str(source.get("name") or "")[:191];mime=str(source.get("mime") or "")
        encoded=source.get("base64")
        if mime not in SIGNATURES or not isinstance(encoded,str) or len(encoded)>((MAX_ASSET_BYTES+2)//3)*4+16:return self._failure(campaign_id,user_id,package_id,"UNSUPPORTED_MEDIA_TYPE" if mime not in SIGNATURES else "VALIDATION_FAILED")
        if self._recent_count(campaign_id,user_id)>=MAX_IMPORTS_PER_MINUTE:return self._failure(campaign_id,user_id,package_id,"RATE_LIMITED")
        self._audit(campaign_id,user_id,package_id,"started")
        try:data=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error):return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        if not data or len(data)>MAX_ASSET_BYTES:return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        if not SIGNATURES[mime](data):return self._failure(campaign_id,user_id,package_id,"UNSUPPORTED_MEDIA_TYPE")
        try:
            with Image.open(BytesIO(data)) as image:
                width,height=int(image.width),int(image.height);actual=(image.format or "").upper()
            expected={"image/png":"PNG","image/jpeg":"JPEG","image/webp":"WEBP"}[mime]
            if actual!=expected or width<=0 or height<=0 or width>8000 or height>8000 or width*height>MAX_PIXELS or width*height*4>MAX_DECODED_BYTES:return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        except (OSError,UnidentifiedImageError,Image.DecompressionBombError):return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        rows=self.assets.list_for_campaign(campaign_id=campaign_id)
        if sum(int(row.get("byte_size") or 0) for row in rows)+len(data)>CAMPAIGN_QUOTA_BYTES:return self._failure(campaign_id,user_id,package_id,"RATE_LIMITED")
        import hashlib
        digest=hashlib.sha256(data).hexdigest();existing=next((row for row in rows if row.get("hash")==digest),None)
        if existing:
            self._audit(campaign_id,user_id,package_id,"succeeded")
            return IngestionResult(True,{"operation":{"status":"ready","progress":"ready"},"asset":self.library._present_asset(existing),"deduplicated":True})
        safe_name=(name.rsplit(".",1)[0] or "asset")+EXTENSIONS[mime]
        created=self.library.upload_asset(campaign_id=campaign_id,user_id=user_id,filename=safe_name,content_type=mime,data=data)
        if not created.success:return self._failure(campaign_id,user_id,package_id,"VALIDATION_FAILED")
        self._audit(campaign_id,user_id,package_id,"succeeded")
        return IngestionResult(True,{"operation":{"status":"ready","progress":"ready"},"asset":created.payload["asset"],"deduplicated":False})
    def validate_portable_payload(self, *, data: bytes, media_type_hint: str = "") -> IngestionResult:
        """Apply ingestion guards to untrusted archive bytes without trusting metadata."""
        if not isinstance(data, bytes) or not data:
            return IngestionResult(False,error_key="VALIDATION_FAILED")
        if data.startswith(b"%PDF-"):
            if len(data)>25*1024*1024 or b"%%EOF" not in data[-4096:]:
                return IngestionResult(False,error_key="VALIDATION_FAILED")
            if media_type_hint and media_type_hint != PDF_MIME:
                return IngestionResult(False,error_key="UNSUPPORTED_MEDIA_TYPE")
            return IngestionResult(True,{"contentType":PDF_MIME,"extension":".pdf","width":None,"height":None})
        if len(data)>MAX_ASSET_BYTES:
            return IngestionResult(False,error_key="VALIDATION_FAILED")
        sniffed=next((mime for mime,check in SIGNATURES.items() if check(data)),None)
        if sniffed is None:
            return IngestionResult(False,error_key="UNSUPPORTED_MEDIA_TYPE")
        try:
            with Image.open(BytesIO(data)) as image:
                width,height=int(image.width),int(image.height);actual=(image.format or "").upper()
            expected={"image/png":"PNG","image/jpeg":"JPEG","image/webp":"WEBP"}[sniffed]
            if actual!=expected or width<=0 or height<=0 or width>8000 or height>8000 or width*height>MAX_PIXELS or width*height*4>MAX_DECODED_BYTES:
                return IngestionResult(False,error_key="VALIDATION_FAILED")
        except (OSError,UnidentifiedImageError,Image.DecompressionBombError):
            return IngestionResult(False,error_key="VALIDATION_FAILED")
        if media_type_hint and media_type_hint != sniffed:
            return IngestionResult(False,error_key="UNSUPPORTED_MEDIA_TYPE")
        return IngestionResult(True,{"contentType":sniffed,"extension":EXTENSIONS[sniffed],"width":width,"height":height})
    def cancel(self,*,campaign_id,user_id,package_id,asset_id):
        role=self.campaigns.get_member_role(campaign_id=campaign_id,user_id=user_id);asset=self.assets.get_by_id(asset_id)
        if not can_manage_assets(actor_role=role):return IngestionResult(False,error_key="PERMISSION_DENIED")
        if not asset or asset.get("campaign_id")!=campaign_id:return IngestionResult(False,error_key="NOT_FOUND")
        return IngestionResult(True,{"operation":{"status":"ready","cancelled":False},"assetId":asset_id})
    def _recent_count(self,campaign_id,user_id):
        rows,_=self.audit.repository.page(campaign_id=campaign_id,event_type="asset.import.started",offset=0,limit=100)
        cutoff=int(time.time())-60;return sum(row.get("actor_user_id")==user_id and row["created_at"]>=cutoff for row in rows)
    def _audit(self,campaign_id,user_id,package_id,transition):
        self.audit.record(campaign_id=campaign_id,actor_user_id=user_id,event_type=f"asset.import.{transition}",subject_type="campaign_asset",subject_id=None,action="import",result=transition,metadata={"package_id":package_id},required=True)
    def _failure(self,campaign_id,user_id,package_id,reason):
        self.audit.record(campaign_id=campaign_id,actor_user_id=user_id,event_type="asset.import.failed",subject_type="campaign_asset",subject_id=None,action="import",result="failed",metadata={"package_id":package_id,"semantic_reason":reason},required=True)
        return IngestionResult(False,error_key=reason)
