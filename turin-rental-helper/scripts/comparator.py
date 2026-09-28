#!/usr/bin/env python3
"""Backward-compatible entry point for the v2 recommendation engine."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from rental_helper import recommend


class ListingComparator:
    """Compatibility wrapper; new code should call ``rental_helper.recommend``."""

    def __init__(self, weights: Optional[Mapping[str, float]] = None):
        self.weights = dict(weights or {})

    def calculate_scores(
        self,
        listings: List[Dict[str, Any]],
        preferences: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        prepared: List[Dict[str, Any]] = []
        originals: Dict[str, Dict[str, Any]] = {}
        for index, listing in enumerate(listings):
            item = dict(listing)
            item.setdefault("id", f"legacy:{index}")
            item.setdefault("source", "legacy")
            item.setdefault("url", "")
            originals[item["id"]] = dict(listing)
            prepared.append(item)

        config = dict(preferences or {})
        if self.weights:
            config["weights"] = self.weights
        result = recommend(prepared, config, limit=None)
        output: List[Dict[str, Any]] = []
        for ranked in result.ranked:
            item = originals[ranked.listing.id]
            item["overall_score"] = ranked.score / 10
            item["closeness"] = ranked.score / 100
            item["score_coverage"] = ranked.coverage
            item["warnings"] = ranked.warnings
            output.append(item)
        return output


def rank_listings(
    listings: List[Dict[str, Any]],
    weights: Optional[Mapping[str, float]] = None,
    preferences: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    return ListingComparator(weights).calculate_scores(listings, preferences)
