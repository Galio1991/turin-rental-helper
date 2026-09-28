import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from rental_helper.adapters import IdealistaMarkdownAdapter, parse_italian_number  # noqa: E402
from rental_helper.pipeline import recommend  # noqa: E402


class AdapterTests(unittest.TestCase):
    def test_italian_numbers(self):
        self.assertEqual(parse_italian_number("1.250"), 1250)
        self.assertEqual(parse_italian_number("1.250,50"), 1250.5)

    def test_adapter_preserves_unknown_boolean_fields(self):
        text = "[Monolocale in Cenisia](https://www.idealista.it/immobile/123/)\n650 €/mese · 28 m²"
        item = IdealistaMarkdownAdapter().parse(text)[0]
        self.assertEqual(item.base_rent, 650)
        self.assertEqual(item.property_type, "studio")
        self.assertEqual(item.district, "Cenisia")
        self.assertIsNone(item.furnished)
        self.assertIsNone(item.has_ac)

    def test_pipeline_deduplicates_tracking_variants(self):
        raw = {
            "id": "a",
            "source": "test",
            "url": "https://example.test/home/?campaign=x",
            "base_rent": 500,
        }
        copy = {**raw, "id": "b", "url": "https://example.test/home"}
        result = recommend([raw, copy], {"max_total_monthly": 800})
        self.assertEqual(len(result.ranked), 1)
        self.assertEqual(result.duplicates, [("b", "a")])

    def test_invalid_records_are_reported_not_silently_scored(self):
        result = recommend([{"source": "test", "base_rent": "oops"}], {})
        self.assertEqual(len(result.ranked), 0)
        self.assertEqual(len(result.invalid), 1)


if __name__ == "__main__":
    unittest.main()
