#!/usr/bin/env python3
"""Compatibility helpers for captured listing text.

This module does not fetch websites. It parses content already obtained with
the user's authorization and delegates filtering/ranking to the v2 engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rental_helper import Preferences
from rental_helper.adapters import IdealistaMarkdownAdapter, detect_district, parse_italian_number
from rental_helper.models import Listing
from rental_helper.ranking import evaluate_constraints, score_listing as score_canonical_listing


_districts_data: Optional[Dict[str, Any]] = None


def load_districts_data() -> Dict[str, Any]:
    """Load legacy area data; callers must not treat it as authoritative."""
    global _districts_data
    if _districts_data is None:
        path = Path(__file__).parent.parent / "assets" / "data" / "turin-districts.json"
        _districts_data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"districts": {}}
    return _districts_data


def get_search_districts(user_preferences: Dict[str, Any]) -> List[str]:
    """Order areas without silently excluding them using unverified scores."""
    areas = load_districts_data().get("districts", {})
    preferred = list(user_preferences.get("preferred_districts", []))
    preferred_known = [name for name in preferred if name in areas]
    recommended = [name for name, info in areas.items() if info.get("recommended") and name not in preferred_known]
    remaining = [name for name in areas if name not in preferred_known and name not in recommended]
    return preferred_known + recommended + remaining


def extract_listings_from_text(
    text: str, website: str = "idealista", target_district: str = ""
) -> List[Dict[str, Any]]:
    if website.casefold() != "idealista":
        raise ValueError(f"unsupported source adapter: {website}")
    return [item.to_dict() for item in IdealistaMarkdownAdapter().parse(text, target_district or None)]


def extract_single_listing(
    text: str, website: str = "idealista", target_district: str = ""
) -> Optional[Dict[str, Any]]:
    listings = extract_listings_from_text(text, website, target_district)
    return listings[0] if listings else None


def parse_price(price_str: str) -> float:
    try:
        return parse_italian_number(price_str)
    except ValueError:
        return 0.0


def filter_listings(listings: List[Dict[str, Any]], user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    preferences = Preferences.from_dict(user_preferences)
    result: List[Dict[str, Any]] = []
    for index, raw in enumerate(listings):
        item = dict(raw)
        item.setdefault("id", f"legacy:{index}")
        item.setdefault("source", "legacy")
        item.setdefault("url", "")
        if evaluate_constraints(Listing.from_dict(item), preferences).accepted:
            result.append(raw)
    return result


def score_listing(listing: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(listing)
    item.setdefault("id", "legacy:single")
    item.setdefault("source", "legacy")
    item.setdefault("url", "")
    ranked = score_canonical_listing(Listing.from_dict(item), Preferences.from_dict(user_preferences))
    output = dict(listing)
    output["overall_score"] = ranked.score / 10
    output["score_coverage"] = ranked.coverage
    output["warnings"] = ranked.warnings
    return output


def generate_recommendation_reason(listing: Dict[str, Any], user_preferences: Dict[str, Any]) -> str:
    scored = score_listing(listing, user_preferences)
    reasons = []
    if scored["score_coverage"] < 0.5:
        reasons.append("资料完整度偏低，建议先核实费用和通勤")
    if listing.get("furnished") is True:
        reasons.append("明确带家具")
    if listing.get("heating"):
        reasons.append(f"供暖类型：{listing['heating']}")
    return "；".join(reasons) if reasons else "符合已知偏好，仍需核实缺失信息"
