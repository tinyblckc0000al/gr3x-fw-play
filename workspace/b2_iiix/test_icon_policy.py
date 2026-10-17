"""Reject resource collisions before the builder changes any firmware bytes."""
import sys
import unittest
from unittest.mock import patch

from verify_release import HERE, STOCK
import gr3patch_iiix as gp

sys.modules['gr3patch'] = gp
import make_slots15 as builder
import presets_config


class IconPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.films, _ = presets_config.load(str(HERE / 'presets.json'))

    def test_old_crop_collision_is_rejected_before_writing(self):
        image = gp.Image(str(STOCK))
        old_ids = (5, 6, 7, 0x1D, 0x2D, 0x2E, 0x2A0, 0x2A1)
        with patch.object(builder, 'ICON_IDS', old_ids):
            with self.assertRaisesRegex(ValueError, 'factory icon'):
                builder.patch(image, self.films)
        self.assertEqual(image.target, image.original)

    def test_invalid_resources_are_rejected_without_changing_image(self):
        image = gp.Image(str(STOCK))
        cases = (
            ((5, 6, 7, 0x1D, 0x2C, 0x2A0, 0x2A1, 0x2A2), 'factory icon'),
            ((5, 6, 7, 0x1D, 0x15A, 0x2A0, 0x2A1, 0x2A2), 'factory icon'),
            ((5, 6, 7, 0x1D, 0x29F, 0x2A0, 0x2A1, 0x2A2), 'factory icon'),
            ((5, 6, 7, 0x1D, 0x2A0, 0x2A0, 0x2A1, 0x2A2), 'duplicate'),
            ((5, 6, 7, 0x1D, 0x2A0, 0x2A1, 0x2A2, 0x2A4), 'contiguous'),
            ((5, 6, 7), 'capacity'),
        )
        for ids, reason in cases:
            with self.subTest(ids=ids), patch.object(builder, 'ICON_IDS', ids):
                with self.assertRaisesRegex(ValueError, reason):
                    builder.patch(image, self.films)
                self.assertEqual(image.target, image.original)

    def test_empty_and_over_capacity_lists_are_rejected(self):
        for films in ([], self.films + self.films[:2]):
            with self.subTest(count=len(films)), self.assertRaisesRegex(ValueError, 'capacity'):
                builder.patch(None, films)


if __name__ == '__main__':
    unittest.main()
