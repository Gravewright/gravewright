"""Generate the browser method registry from the server's public contract."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'gravewright/modules'
contract = json.loads((root / 'contracts/frontend.json').read_text())
(root / 'static/gravewright_modules/frontend-contract.js').write_text(
    '// Generated from contracts/frontend.json; run scripts/generate_frontend_api.py.\n'
    + 'export const FRONTEND_CONTRACT = ' + json.dumps(contract, indent=2) + ';\n'
)
