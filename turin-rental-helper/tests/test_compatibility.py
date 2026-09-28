import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import comparator  # noqa: E402
import scraper  # noqa: E402
import utils  # noqa: E402


class CompatibilityTests(unittest.TestCase):
    def test_legacy_comparator_uses_v2_cost_direction(self):
        listings = [
            {
                "id": "expensive",
                "source": "test",
                "price": 800,
                "mandatory_expenses": 0,
                "estimated_utilities": 0,
                "commute_minutes": 20,
            },
            {
                "id": "cheap",
                "source": "test",
                "price": 500,
                "mandatory_expenses": 0,
                "estimated_utilities": 0,
                "commute_minutes": 20,
            },
        ]
        ranked = comparator.rank_listings(
            listings,
            preferences={
                "max_total_monthly": 1000,
                "target_commute_minutes": 20,
                "max_commute_minutes": 40,
            },
        )
        self.assertEqual(ranked[0]["id"], "cheap")

    def test_legacy_parser_and_utils_imports(self):
        self.assertEqual(scraper.parse_price("1.250,50"), 1250.5)
        self.assertEqual(utils.format_price(500), "€500")


if __name__ == "__main__":
    unittest.main()
