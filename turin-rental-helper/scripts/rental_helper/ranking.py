"""Constraint evaluation and candidate-independent utility ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import FeatureScore, Listing, Preferences, RankedListing


UNKNOWN_UTILITY = 0.35


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _feature(name: str, utility: Optional[float], confidence: float, explanation: str) -> FeatureScore:
    confidence = _clamp(confidence if utility is not None else 0.0)
    effective = UNKNOWN_UTILITY if utility is None else confidence * _clamp(utility) + (1 - confidence) * UNKNOWN_UTILITY
    return FeatureScore(name, utility, confidence, effective, explanation)


@dataclass
class ConstraintResult:
    accepted: bool = True
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def evaluate_constraints(listing: Listing, preferences: Preferences) -> ConstraintResult:
    result = ConstraintResult()

    def unknown(message: str) -> None:
        if preferences.unknown_hard_policy == "reject":
            result.accepted = False
            result.reasons.append(message)
        else:
            result.warnings.append(message)

    if preferences.max_total_monthly is not None:
        cost = listing.known_monthly_cost
        if cost is None:
            unknown("月度总成本未知，无法确认预算约束")
        elif cost > preferences.max_total_monthly:
            result.accepted = False
            result.reasons.append("已知月度总成本超过预算")
        elif listing.mandatory_expenses is None or listing.estimated_utilities is None:
            result.warnings.append("部分月度费用未知，当前总额不是最终全包成本")

    if preferences.max_base_rent is not None:
        if listing.base_rent is None:
            unknown("基础租金未知")
        elif listing.base_rent > preferences.max_base_rent:
            result.accepted = False
            result.reasons.append("基础租金超过上限")

    if preferences.max_commute_minutes is not None:
        if listing.commute_minutes is None:
            unknown("通勤时间未知")
        elif listing.commute_minutes > preferences.max_commute_minutes:
            result.accepted = False
            result.reasons.append("通勤时间超过上限")

    if preferences.min_area_sqm is not None:
        if listing.area_sqm is None:
            unknown("面积未知")
        elif listing.area_sqm < preferences.min_area_sqm:
            result.accepted = False
            result.reasons.append("面积低于最低要求")

    if preferences.property_types and listing.property_type not in preferences.property_types:
        result.accepted = False
        result.reasons.append("房型不符合要求")

    for required, actual, label in (
        (preferences.furnished, listing.furnished, "家具状态"),
        (preferences.require_ac, listing.has_ac, "空调状态"),
        (preferences.require_elevator, listing.has_elevator, "电梯状态"),
    ):
        if required is True:
            if actual is None:
                unknown(f"{label}未知")
            elif actual is False:
                result.accepted = False
                result.reasons.append(f"不满足{label}要求")

    if preferences.min_safety_score is not None:
        if not listing.has_usable_safety_evidence:
            unknown("缺少有来源的安全指标")
        elif listing.safety_score < preferences.min_safety_score:
            result.accepted = False
            result.reasons.append("安全指标低于用户设置的下限")

    return result


def _cost_score(listing: Listing, preferences: Preferences) -> FeatureScore:
    budget = preferences.max_total_monthly or preferences.max_base_rent
    value = listing.known_monthly_cost if preferences.max_total_monthly else listing.base_rent
    if budget is None or value is None:
        return _feature("cost", None, 0, "缺少预算或费用数据")
    ratio = value / budget
    if ratio <= 0.65:
        utility = 1.0
    elif ratio <= 1.0:
        utility = 1.0 - (ratio - 0.65) / 0.35 * 0.65
    else:
        utility = max(0.0, 0.35 - (ratio - 1.0))
    confidence = listing.cost_confidence if preferences.max_total_monthly else listing.confidence_for("base_rent")
    return _feature("cost", utility, confidence, f"已知月度费用 €{value:.0f}，预算 €{budget:.0f}")


def _commute_score(listing: Listing, preferences: Preferences) -> FeatureScore:
    value = listing.commute_minutes
    target = preferences.target_commute_minutes
    maximum = preferences.max_commute_minutes
    if target is None and maximum is not None:
        target = max(10.0, maximum * 0.5)
    if maximum is None and target is not None:
        maximum = max(target + 15.0, target * 2.0)
    if value is None or target is None or maximum is None:
        return _feature("commute", None, 0, "缺少地址级通勤时间或通勤目标")
    if value <= target:
        utility = 1.0
    elif value >= maximum:
        utility = 0.0
    else:
        utility = 1.0 - (value - target) / (maximum - target)
    return _feature(
        "commute",
        utility,
        listing.confidence_for("commute_minutes"),
        f"预计通勤 {value:.0f} 分钟，目标 {target:.0f} 分钟",
    )


def _space_score(listing: Listing, preferences: Preferences) -> FeatureScore:
    if preferences.min_area_sqm is None or listing.area_sqm is None:
        return _feature("space", None, 0, "缺少面积数据或面积偏好")
    ratio = listing.area_sqm / preferences.min_area_sqm
    utility = _clamp(0.5 + (ratio - 1.0) * 0.75)
    return _feature(
        "space",
        utility,
        listing.confidence_for("area_sqm"),
        f"面积 {listing.area_sqm:g} m²，最低要求 {preferences.min_area_sqm:g} m²",
    )


def _amenity_score(listing: Listing, preferences: Preferences) -> FeatureScore:
    checks: List[Tuple[Optional[bool], Optional[bool], str]] = [
        (preferences.furnished, listing.furnished, "家具"),
        (preferences.require_ac, listing.has_ac, "空调"),
        (preferences.require_elevator, listing.has_elevator, "电梯"),
    ]
    known: List[float] = []
    labels: List[str] = []
    for desired, actual, label in checks:
        if desired is None:
            continue
        labels.append(label)
        if actual is not None:
            known.append(1.0 if actual == desired else 0.0)
    if preferences.preferred_heating:
        labels.append("供暖")
        if listing.heating:
            known.append(1.0 if listing.heating == preferences.preferred_heating else 0.0)
    if not labels:
        return _feature("amenities", None, 0, "用户未设置设施偏好")
    if not known:
        return _feature("amenities", None, 0, "所需设施信息均未知")
    confidence = len(known) / len(labels) * listing.extraction_confidence
    return _feature("amenities", sum(known) / len(known), confidence, f"已核对 {len(known)}/{len(labels)} 项设施")


def _safety_score(listing: Listing, preferences: Preferences) -> FeatureScore:
    if not listing.has_usable_safety_evidence:
        return _feature("safety", None, 0, "安全指标缺少来源、日期或地理粒度")
    return _feature(
        "safety",
        listing.safety_score / 10,
        listing.confidence_for("safety_score", 0.5),
        f"安全指标 {listing.safety_score:g}/10；需结合来源与更新时间解读",
    )


def score_listing(listing: Listing, preferences: Preferences, warnings: Optional[List[str]] = None) -> RankedListing:
    features = {
        "cost": _cost_score(listing, preferences),
        "commute": _commute_score(listing, preferences),
        "space": _space_score(listing, preferences),
        "amenities": _amenity_score(listing, preferences),
        "safety": _safety_score(listing, preferences),
    }
    weighted = sum(preferences.weights[name] * item.effective_utility for name, item in features.items())
    coverage = sum(preferences.weights[name] * item.confidence for name, item in features.items())
    tradeoffs = [item.explanation for item in features.values() if item.utility is not None and item.utility < 0.5]
    missing = [item.explanation for item in features.values() if item.utility is None]
    return RankedListing(
        listing=listing,
        score=weighted * 100,
        coverage=coverage,
        features=features,
        warnings=list(warnings or []) + missing,
        tradeoffs=tradeoffs,
    )


def pareto_front(candidates: Sequence[RankedListing]) -> set[str]:
    ids: set[str] = set()
    for candidate in candidates:
        vector = [item.effective_utility for item in candidate.features.values()]
        dominated = False
        for other in candidates:
            if other is candidate:
                continue
            other_vector = [item.effective_utility for item in other.features.values()]
            if all(a >= b for a, b in zip(other_vector, vector)) and any(a > b for a, b in zip(other_vector, vector)):
                dominated = True
                break
        if not dominated:
            ids.add(candidate.listing.id)
    return ids


def diversify(candidates: Sequence[RankedListing], limit: Optional[int] = None, penalty: float = 4.0) -> List[RankedListing]:
    remaining = list(candidates)
    selected: List[RankedListing] = []
    target = len(remaining) if limit is None else min(limit, len(remaining))
    while remaining and len(selected) < target:
        def adjusted(item: RankedListing) -> Tuple[float, float, str]:
            repeats = sum(
                int(bool(item.listing.district) and item.listing.district == chosen.listing.district)
                + int(item.listing.source == chosen.listing.source)
                + int(item.listing.property_type == chosen.listing.property_type)
                for chosen in selected
            )
            return (item.score - repeats * penalty, item.coverage, item.listing.id)

        choice = max(remaining, key=adjusted)
        selected.append(choice)
        remaining.remove(choice)
    return selected


def rank_listings(
    listings: Iterable[Listing], preferences: Preferences, limit: Optional[int] = None
) -> Tuple[List[RankedListing], Dict[str, List[str]]]:
    accepted: List[RankedListing] = []
    rejected: Dict[str, List[str]] = {}
    for listing in listings:
        constraints = evaluate_constraints(listing, preferences)
        if not constraints.accepted:
            rejected[listing.id] = constraints.reasons
            continue
        accepted.append(score_listing(listing, preferences, constraints.warnings))

    front = pareto_front(accepted)
    for candidate in accepted:
        candidate.pareto_optimal = candidate.listing.id in front
    accepted.sort(key=lambda item: (item.score, item.coverage, item.listing.id), reverse=True)
    return diversify(accepted, limit=limit), rejected
