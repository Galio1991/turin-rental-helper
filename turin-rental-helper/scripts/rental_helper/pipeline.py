"""End-to-end recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .ingestion import deduplicate
from .models import Listing, Preferences, RankedListing
from .ranking import rank_listings


@dataclass
class RecommendationResult:
    ranked: List[RankedListing]
    rejected: Dict[str, List[str]]
    duplicates: List[Tuple[str, str]]
    invalid: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations": [item.to_dict() for item in self.ranked],
            "rejected": self.rejected,
            "duplicates": [list(pair) for pair in self.duplicates],
            "invalid": self.invalid,
        }


def recommend(
    raw_listings: Iterable[Mapping[str, Any] | Listing],
    raw_preferences: Mapping[str, Any] | Preferences,
    limit: Optional[int] = 10,
) -> RecommendationResult:
    preferences = raw_preferences if isinstance(raw_preferences, Preferences) else Preferences.from_dict(raw_preferences)
    listings: List[Listing] = []
    invalid: List[Dict[str, str]] = []
    for index, raw in enumerate(raw_listings):
        if isinstance(raw, Listing):
            listings.append(raw)
            continue
        try:
            listings.append(Listing.from_dict(raw))
        except (TypeError, ValueError) as exc:
            invalid.append({"index": str(index), "error": str(exc)})

    unique, duplicates = deduplicate(listings)
    ranked, rejected = rank_listings(unique, preferences, limit=limit)
    return RecommendationResult(ranked, rejected, duplicates, invalid)
