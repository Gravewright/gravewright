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
}


def validate_asset(data, campaign_id):
    from gravewright.actors.models import Asset
    asset = data['pdf']['asset']
    if asset and not Asset.objects.filter(
        pk=identifier(asset), campaign_id=campaign_id, kind='pdf',
    ).exists():
        raise MapError('PDF not found.')


def register():
    from gravewright.campaigns.systems import register as register_system
    register_system(DESCRIPTOR['systemId'], descriptor=DESCRIPTOR, sheet=SHEET, normalize=normalize, validate=validate_asset, remove_asset=remove_asset_references,
                    combat={'formula': '1d20 + @initiative', 'manual_input': 'number', 'roll': roll_initiative})


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
