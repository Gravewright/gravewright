from copy import deepcopy
from django.test import SimpleTestCase
from gravewright.maps.services import MapError
from .schema import normalize


class DocumentMetadataTests(SimpleTestCase):
    def metadata(self):
        return {'source': 'template:generic', 'pageCount': 2, 'fingerprint': 'synthetic',
                'pages': [{'page': 1, 'width': 595, 'height': 842, 'rotation': 0}]}

    def test_metadata_round_trip_and_omitted_player_save_preserves_it(self):
        previous = normalize({'pdf': {'sourceMetadata': [self.metadata()]}})
        clean = normalize({'fields': {'score': '12'}}, previous, gm=False)
        self.assertEqual(clean['pdf']['sourceMetadata'], previous['pdf']['sourceMetadata'])
        self.assertIsNot(clean['pdf']['sourceMetadata'], previous['pdf']['sourceMetadata'])

    def test_player_cannot_replace_mapping_document_identity(self):
        previous = normalize({'pdf': {'sourceMetadata': [self.metadata()]}})
        for key, value in [('pageCount', 3), ('fingerprint', 'changed')]:
            changed = deepcopy(previous)
            changed['pdf']['sourceMetadata'][0][key] = value
            with self.assertRaises(MapError) as caught:
                normalize(changed, previous, gm=False)
            self.assertEqual(caught.exception.code, 'forbidden')

    def test_metadata_rejects_invalid_dimensions_page_ids_and_complexity(self):
        for field, value in [('width', True), ('height', 0), ('rotation', 45), ('page', 3)]:
            metadata = self.metadata()
            metadata['pages'][0][field] = value
            with self.subTest(field=field), self.assertRaises(MapError):
                normalize({'pdf': {'sourceMetadata': [metadata]}})
        for records in [[self.metadata()] * 65, [self.metadata()] * 2, [{}]]:
            with self.assertRaises(MapError):
                normalize({'pdf': {'sourceMetadata': records}})
