"""Central product-semantic detection for the PDF-sheet ruleset workflow."""
from __future__ import annotations
import json
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository

REQUIRED_CAPABILITIES={"pdf.read","pdf.viewer"}

def is_pdf_sheet_system(system_id: str | None) -> bool:
    if not system_id:return False
    row=InstalledPackageRepository().get(str(system_id))
    if not row or row.get("kind")!="ruleset" or row.get("status")!="enabled":return False
    try: manifest=json.loads(row.get("manifest_json") or "{}")
    except (TypeError,json.JSONDecodeError):return False
    capabilities=set(manifest.get("capabilities") or [])
    mappings=((manifest.get("provides") or {}).get("mappings") or {})
    return REQUIRED_CAPABILITIES.issubset(capabilities) and isinstance(mappings.get("pdfFields"),str)
