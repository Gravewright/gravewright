"""The bundled PDF system owns its schema, assets and complete sheet body."""

from gravewright.journals.services import identifier
from gravewright.maps.services import MapError
from .schema import normalize

DESCRIPTOR = {
    'systemId': 'gravewright-pdf-system',
    'title': 'Gravewright PDF System',
    'actorTypes': [{'id': 'character', 'label': 'Character'}],
}
SHEET = {
    'entry': '/static/gravewright_pdf_system/sheet.js',
    'template': 'gravewright_pdf_system/sheet.html',
    'stylesheet': 'gravewright_pdf_system/pdf-sheet.css',
    'directory_actions_template': 'gravewright_pdf_system/directory-actions.html',
    'directory_icons_template': 'gravewright_pdf_system/directory-icons.html',
}


def validate_upload(file):
    from django.conf import settings
    limit = settings.PDF_SYSTEM_UPLOAD_MAX_BYTES
    if not file or file.size > limit:
        raise MapError(f'The PDF must be no larger than {limit / (1024 * 1024):g} MB.')
    raw = file.read()
    if not raw.startswith(b'%PDF-'):
        raise MapError('Choose a PDF document.')
    return raw, '.pdf'


def templates(campaign_id):
    from gravewright.actors.models import Asset
    return [{'id': str(asset.pk), 'name': asset.name}
            for asset in Asset.objects.filter(campaign_id=campaign_id, kind='pdf')]


def validate_asset(data, campaign_id):
    from gravewright.actors.models import Asset
    asset = data['pdf']['asset']
    if asset and not Asset.objects.filter(
        pk=identifier(asset), campaign_id=campaign_id, kind='pdf',
    ).exists():
        raise MapError('PDF not found.')


def register():
    from api.combat import register_provider
    from api.systems import register_api
    from gravewright.campaigns.systems import register as register_system
    from .combat import advance_effects
    from .public import operations
    register_system(
        DESCRIPTOR['systemId'], descriptor=DESCRIPTOR, sheet=SHEET,
        normalize=normalize, validate=validate_asset,
        remove_asset=remove_asset_references, default=True, templates=templates,
        assets={'kind': 'pdf', 'content_type': 'application/pdf', 'validate_upload': validate_upload,
                'template': {'dataPath': ['pdf', 'asset'], 'icon': 'FilePdf', 'label': 'PDF'}},
        combat={'formula': '1d20 + @initiative', 'manual_input': 'number', 'roll': roll_initiative,
                'show_roll': False},
    )
    register_provider(DESCRIPTOR['systemId'], advance_effects=advance_effects)
    register_api(DESCRIPTOR['systemId'], operations())


def roll_initiative(formula, data):
    """The PDF initiative mapping writes to init on the authoritative sheet."""
    import re
    from gravewright.dice.engine import evaluate
    from gravewright.maps.objects import number
    modifier = number(data.get('init', 0), -1e6, 1e6)
    expression = re.sub(r'@initiative\b', lambda _: f'({modifier})', formula)
    return evaluate(expression, 1)['value']['value']


def remove_asset_references(campaign_id, asset):
    from gravewright.actors.models import Actor
    from gravewright.tokens.models import Token
    sources = [
        (Actor.objects.filter(campaign_id=campaign_id), 'data'),
        (Token.objects.filter(scene__campaign_id=campaign_id, linked=False), 'snapshot'),
    ]
    for rows, field in sources:
        for row in rows:
            pdf = getattr(row, field).get('pdf')
            if isinstance(pdf, dict) and pdf.get('asset') == str(asset.pk):
                pdf.update(asset='', template='generic')
                row.sheet_version += 1
                row.save()
