import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from rental_helper import Listing, Preferences  # noqa: E402
from rental_helper.ranking import evaluate_constraints, rank_listings, score_listing  # noqa: E402


def listing(identifier, rent, **kwargs):
    values = {
        "id": identifier,
        "source": "test",
        "title": identifier,
        "url": f"https://example.test/{identifier}",
        "base_rent": rent,
        "mandatory_expenses": 0,
        "estimated_utilities": 0,
        "commute_minutes": 20,
        "area_sqm": 25,
        "property_type": "studio",
        "district": identifier,
        "extraction_confidence": 1,
    }
    values.update(kwargs)
    return Listing.from_dict(values)


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.preferences = Preferences.from_dict(
            {
                "max_total_monthly": 1000,
                "max_commute_minutes": 45,
                "target_commute_minutes": 20,
                "min_area_sqm": 20,
                "property_types": ["studio"],
                "weights": {"cost": 1, "commute": 1, "space": 1, "amenities": 0, "safety": 0},
            }
        )

    def test_cheaper_listing_cannot_rank_lower_when_other_fields_match(self):
        cheap = listing("cheap", 500)
        expensive = listing("expensive", 850)
        ranked, _ = rank_listings([expensive, cheap], self.preferences)
        self.assertEqual(ranked[0].listing.id, "cheap")

    def test_shorter_commute_cannot_score_lower(self):
        near = listing("near", 600, commute_minutes=15)
        far = listing("far", 600, commute_minutes=35)
        self.assertGreater(score_listing(near, self.preferences).score, score_listing(far, self.preferences).score)

    def test_score_does_not_depend_on_candidate_pool(self):
        target = listing("target", 600)
        score_alone = score_listing(target, self.preferences).score
        ranked, _ = rank_listings([target, listing("other", 800)], self.preferences)
        score_in_pool = next(item.score for item in ranked if item.listing.id == "target")
        self.assertEqual(score_alone, score_in_pool)

    def test_known_over_budget_is_rejected(self):
        decision = evaluate_constraints(listing("over", 1001), self.preferences)
        self.assertFalse(decision.accepted)

    def test_unknown_expenses_generate_warning(self):
        item = listing("unknown", 600, mandatory_expenses=None, estimated_utilities=None)
        decision = evaluate_constraints(item, self.preferences)
        self.assertTrue(decision.accepted)
        self.assertTrue(any("费用未知" in warning for warning in decision.warnings))

    def test_unknown_hard_value_can_be_strictly_rejected(self):
        strict = Preferences.from_dict({"max_commute_minutes": 30, "unknown_hard_policy": "reject"})
        decision = evaluate_constraints(listing("unknown", 500, commute_minutes=None), strict)
        self.assertFalse(decision.accepted)

    def test_area_name_is_not_a_built_in_ban(self):
        candidate = listing("area", 500, district="Aurora")
        decision = evaluate_constraints(candidate, self.preferences)
        self.assertTrue(decision.accepted)

    def test_unsourced_safety_score_is_not_used(self):
        candidate = listing("safety", 500, safety_score=9)
        scored = score_listing(candidate, self.preferences)
        self.assertIsNone(scored.features["safety"].utility)

    def test_sourced_safety_score_can_be_used(self):
        candidate = listing(
            "safety",
            500,
            safety_score=8,
            safety_source="example public dataset",
            safety_observed_at="2026-01-01",
            safety_granularity="street segment",
        )
        scored = score_listing(candidate, self.preferences)
        self.assertEqual(scored.features["safety"].utility, 0.8)


if __name__ == "__main__":
    unittest.main()
