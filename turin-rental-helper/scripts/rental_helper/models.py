"""Domain models and validation for rental recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Mapping, Optional, Tuple


DEFAULT_WEIGHTS: Dict[str, float] = {
    "cost": 0.40,
    "commute": 0.25,
    "space": 0.10,
    "amenities": 0.10,
    "safety": 0.15,
}


def _optional_float(value: Any, field_name: str) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return result


def _optional_bool(value: Any, field_name: str) -> Optional[bool]:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true, false, or null")


def _confidence(value: Any, default: float) -> float:
    result = default if value is None else float(value)
    if not 0 <= result <= 1:
        raise ValueError("confidence values must be between 0 and 1")
    return result


@dataclass(frozen=True)
class Listing:
    """Canonical representation shared by every source adapter."""

    id: str
    source: str
    title: str
    url: str
    base_rent: Optional[float]
    mandatory_expenses: Optional[float] = None
    estimated_utilities: Optional[float] = None
    deposit: Optional[float] = None
    area_sqm: Optional[float] = None
    rooms: Optional[float] = None
    property_type: str = "unknown"
    district: Optional[str] = None
    address: Optional[str] = None
    furnished: Optional[bool] = None
    has_ac: Optional[bool] = None
    has_elevator: Optional[bool] = None
    heating: Optional[str] = None
    commute_minutes: Optional[float] = None
    safety_score: Optional[float] = None
    safety_source: Optional[str] = None
    safety_observed_at: Optional[date] = None
    safety_granularity: Optional[str] = None
    observed_at: Optional[date] = None
    extraction_confidence: float = 0.80
    field_confidence: Mapping[str, float] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def known_monthly_cost(self) -> Optional[float]:
        if self.base_rent is None:
            return None
        return self.base_rent + (self.mandatory_expenses or 0) + (self.estimated_utilities or 0)

    @property
    def cost_confidence(self) -> float:
        if self.base_rent is None:
            return 0.0
        confidence = self.confidence_for("base_rent", self.extraction_confidence)
        if self.mandatory_expenses is None:
            confidence *= 0.75
        if self.estimated_utilities is None:
            confidence *= 0.90
        return max(0.0, min(1.0, confidence))

    def confidence_for(self, field_name: str, fallback: Optional[float] = None) -> float:
        default = self.extraction_confidence if fallback is None else fallback
        return _confidence(self.field_confidence.get(field_name), default)

    @property
    def has_usable_safety_evidence(self) -> bool:
        return bool(
            self.safety_score is not None
            and self.safety_source
            and self.safety_observed_at
            and self.safety_granularity
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Listing":
        source = str(data.get("source") or "unknown")
        url = str(data.get("url") or "")
        listing_id = str(data.get("id") or data.get("source_id") or url)
        if not listing_id:
            raise ValueError("listing requires id, source_id, or url")

        def parse_date(value: Any, field_name: str) -> Optional[date]:
            if value in (None, ""):
                return None
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value[:10])
                except ValueError as exc:
                    raise ValueError(f"{field_name} must use ISO date format") from exc
            raise ValueError(f"{field_name} must be a date or ISO date string")

        observed = parse_date(data.get("observed_at"), "observed_at")
        safety_observed = parse_date(data.get("safety_observed_at"), "safety_observed_at")

        safety = _optional_float(data.get("safety_score"), "safety_score")
        if safety is not None and safety > 10:
            raise ValueError("safety_score must be between 0 and 10")

        return cls(
            id=listing_id,
            source=source,
            title=str(data.get("title") or "Untitled listing"),
            url=url,
            base_rent=_optional_float(data.get("base_rent", data.get("price")), "base_rent"),
            mandatory_expenses=_optional_float(data.get("mandatory_expenses"), "mandatory_expenses"),
            estimated_utilities=_optional_float(data.get("estimated_utilities"), "estimated_utilities"),
            deposit=_optional_float(data.get("deposit"), "deposit"),
            area_sqm=_optional_float(data.get("area_sqm", data.get("area")), "area_sqm"),
            rooms=_optional_float(data.get("rooms"), "rooms"),
            property_type=str(data.get("property_type", data.get("type", "unknown"))),
            district=data.get("district"),
            address=data.get("address"),
            furnished=_optional_bool(data.get("furnished"), "furnished"),
            has_ac=_optional_bool(data.get("has_ac"), "has_ac"),
            has_elevator=_optional_bool(data.get("has_elevator"), "has_elevator"),
            heating=data.get("heating"),
            commute_minutes=_optional_float(data.get("commute_minutes"), "commute_minutes"),
            safety_score=safety,
            safety_source=data.get("safety_source"),
            safety_observed_at=safety_observed,
            safety_granularity=data.get("safety_granularity"),
            observed_at=observed,
            extraction_confidence=_confidence(data.get("extraction_confidence"), 0.80),
            field_confidence=dict(data.get("field_confidence") or {}),
            raw=dict(data),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "base_rent": self.base_rent,
            "mandatory_expenses": self.mandatory_expenses,
            "estimated_utilities": self.estimated_utilities,
            "known_monthly_cost": self.known_monthly_cost,
            "deposit": self.deposit,
            "area_sqm": self.area_sqm,
            "rooms": self.rooms,
            "property_type": self.property_type,
            "district": self.district,
            "address": self.address,
            "furnished": self.furnished,
            "has_ac": self.has_ac,
            "has_elevator": self.has_elevator,
            "heating": self.heating,
            "commute_minutes": self.commute_minutes,
            "safety_score": self.safety_score,
            "safety_source": self.safety_source,
            "safety_observed_at": self.safety_observed_at.isoformat() if self.safety_observed_at else None,
            "safety_granularity": self.safety_granularity,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "extraction_confidence": self.extraction_confidence,
            "field_confidence": dict(self.field_confidence),
        }
        return result


@dataclass(frozen=True)
class Preferences:
    """Explicit constraints and soft preferences supplied by the renter."""

    max_total_monthly: Optional[float] = None
    max_base_rent: Optional[float] = None
    max_commute_minutes: Optional[float] = None
    target_commute_minutes: Optional[float] = None
    min_area_sqm: Optional[float] = None
    property_types: Tuple[str, ...] = ()
    furnished: Optional[bool] = None
    require_ac: Optional[bool] = None
    require_elevator: Optional[bool] = None
    preferred_heating: Optional[str] = None
    preferred_districts: Tuple[str, ...] = ()
    min_safety_score: Optional[float] = None
    unknown_hard_policy: str = "warn"
    weights: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Preferences":
        provided_weights = dict(data.get("weights") or {})
        raw_weights = {key: 0.0 for key in DEFAULT_WEIGHTS} if provided_weights else dict(DEFAULT_WEIGHTS)
        aliases = {"price": "cost", "distance": "commute", "facility": "amenities"}
        for key, value in provided_weights.items():
            if key == "location":
                raw_weights["commute"] += float(value) / 2
                raw_weights["safety"] += float(value) / 2
                continue
            canonical = aliases.get(key, key)
            if canonical not in raw_weights:
                raise ValueError(f"unknown weight: {key}")
            raw_weights[canonical] = float(value)
        if any(value < 0 for value in raw_weights.values()) or sum(raw_weights.values()) <= 0:
            raise ValueError("weights must be non-negative and contain a positive value")
        total = sum(raw_weights.values())
        weights = {key: value / total for key, value in raw_weights.items()}

        policy = str(data.get("unknown_hard_policy") or "warn")
        if policy not in {"warn", "reject"}:
            raise ValueError("unknown_hard_policy must be 'warn' or 'reject'")

        property_types = data.get("property_types")
        if property_types is None and data.get("room_type"):
            property_types = [data["room_type"]]
        if isinstance(property_types, str):
            property_types = [property_types]

        maximum = data.get("max_total_monthly")
        if maximum is None and data.get("max_price") is not None:
            maximum = data.get("max_price")

        min_safety = _optional_float(data.get("min_safety_score"), "min_safety_score")
        if min_safety is not None and min_safety > 10:
            raise ValueError("min_safety_score must be between 0 and 10")
        max_commute = _optional_float(data.get("max_commute_minutes"), "max_commute_minutes")
        target_commute = _optional_float(data.get("target_commute_minutes"), "target_commute_minutes")
        if max_commute is not None and target_commute is not None and target_commute > max_commute:
            raise ValueError("target_commute_minutes cannot exceed max_commute_minutes")

        return cls(
            max_total_monthly=_optional_float(maximum, "max_total_monthly"),
            max_base_rent=_optional_float(data.get("max_base_rent"), "max_base_rent"),
            max_commute_minutes=max_commute,
            target_commute_minutes=target_commute,
            min_area_sqm=_optional_float(data.get("min_area_sqm"), "min_area_sqm"),
            property_types=tuple(str(item) for item in (property_types or ())),
            furnished=_optional_bool(data.get("furnished"), "furnished"),
            require_ac=_optional_bool(data.get("require_ac"), "require_ac"),
            require_elevator=_optional_bool(data.get("require_elevator"), "require_elevator"),
            preferred_heating=data.get("preferred_heating"),
            preferred_districts=tuple(str(item) for item in data.get("preferred_districts", ())),
            min_safety_score=min_safety,
            unknown_hard_policy=policy,
            weights=weights,
        )


@dataclass(frozen=True)
class FeatureScore:
    name: str
    utility: Optional[float]
    confidence: float
    effective_utility: float
    explanation: str


@dataclass
class RankedListing:
    listing: Listing
    score: float
    coverage: float
    features: Dict[str, FeatureScore]
    warnings: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)
    pareto_optimal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listing": self.listing.to_dict(),
            "score": round(self.score, 2),
            "coverage": round(self.coverage, 3),
            "pareto_optimal": self.pareto_optimal,
            "features": {
                name: {
                    "utility": item.utility,
                    "confidence": round(item.confidence, 3),
                    "effective_utility": round(item.effective_utility, 3),
                    "explanation": item.explanation,
                }
                for name, item in self.features.items()
            },
            "warnings": self.warnings,
            "tradeoffs": self.tradeoffs,
        }
