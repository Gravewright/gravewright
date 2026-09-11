"""Native document identity preserved from the original system catalog.

This is a campaign's ruleset reference, not installation of a sheet module.
"""

RULESETS = [{'systemId': 'gravewright-pdf-system', 'title': 'Gravewright PDF System',
             'actorTypes': [{'id': 'character', 'label': 'Character'}]}]
SYSTEM_CHOICES = [(row['systemId'], row['title']) for row in RULESETS]
