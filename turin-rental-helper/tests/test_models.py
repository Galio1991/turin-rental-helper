import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from rental_helper.models import Listing, Preferences  # noqa: E402


class ModelTests(unittest.TestCase):
    def test_legacy_fields_are_normalized(self):
        listing = Listing.from_dict(
            {"id": "1", "source": "test", "title": "x", "price": 500, "area": 30, "type": "studio"}
        )
        self.assertEqual(listing.base_rent, 500)
        self.assertEqual(listing.area_sqm, 30)
        self.assertEqual(listing.property_type, "studio")

    def test_known_monthly_cost_and_confidence(self):
        complete = Listing.from_dict(
            {
                "id": "1",
                "source": "test",
                "base_rent": 500,
                "mandatory_expenses": 80,
                "estimated_utilities": 40,
            }
        )
        incomplete = Listing.from_dict({"id": "2", "source": "test", "base_rent": 500})
        self.assertEqual(complete.known_monthly_cost, 620)
        self.assertGreater(complete.cost_confidence, incomplete.cost_confidence)

    def test_weights_are_normalized_and_aliases_work(self):
        preferences = Preferences.from_dict({"weights": {"price": 2, "distance": 1}})
        self.assertAlmostEqual(sum(preferences.weights.values()), 1)
        self.assertGreater(preferences.weights["cost"], preferences.weights["commute"])

    def test_invalid_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            Listing.from_dict({"id": "1", "source": "test", "furnished": "yes"})


if __name__ == "__main__":
    unittest.main()
