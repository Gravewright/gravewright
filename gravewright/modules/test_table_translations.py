"""New table controls use Translator source keys with compatible parameters."""
from collections import Counter
import re

from django.test import SimpleTestCase

from .localization import reviewed_portuguese, reviewed_spanish


FEATURE_KEYS = (
    'Measurement title', 'Empty map', 'Activate after creation',
    'Activate for selected players', 'Select one or more players.',
    'Select one or more players. Other players stay on their current scene.',
    'Your current scene', 'Background color', 'Width (px)', 'Height (px)',
    'Choose a color, dimensions and whether to show the grid.', 'Create map',
    'Circular activation area', 'Activation radius (cells)',
    'Drag the circle handle to resize the area. Connect On area enter or On area exit in the Smart Object to run effects without clicking.',
    'Invalid activation radius.', 'Choose a Smart Object before setting its activation area.',
    'Mouse pointers', "Show participants' pointers", 'Share my pointer',
    "Choose whether to see other participants' pointers and share your own. Saved for your profile on this device.",
    'Shortcuts', 'Keyboard shortcuts',
    'Choose a field and press a key combination. Escape cancels recording. Saved for your profile on this device.',
    'Restore defaults', 'Unassigned', 'Unassign', 'Unassign shortcut for {action}',
    'Press a key combination…', 'Windows',
    'This combination is reserved for editing or the browser.',
    'This shortcut is already assigned to {action}.', ' / cell', 'Move {0}',
    'Invalid empty map settings.', 'Invalid grid visibility.', 'Invalid scene activation.',
    'Use positive whole numbers for map dimensions.', 'Select players from this campaign.',
    'A selected player cannot access this scene.',
)


class TableTranslationTests(SimpleTestCase):
    def test_feature_messages_preserve_translator_placeholders_in_both_languages(self):
        parameters = re.compile(r'\{(?:[A-Za-z_][A-Za-z0-9_.]*|\d+)\}')
        for locale, messages in (('pt-BR', reviewed_portuguese()), ('es', reviewed_spanish())):
            for key in FEATURE_KEYS:
                with self.subTest(locale=locale, source=key):
                    self.assertIn(key, messages)
                    self.assertTrue(messages[key].strip())
                    self.assertNotEqual(messages[key], key)
                    self.assertNotRegex(messages[key], r'\w\?\w', 'Do not ship replacement characters inside translated words.')
                    self.assertEqual(Counter(parameters.findall(key)), Counter(parameters.findall(messages[key])))
