"""Adapters for source text captured by an authorized browsing tool."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from typing import Dict, List, Optional

from .models import Listing


DISTRICT_ALIASES: Dict[str, tuple[str, ...]] = {
    "Cit Turin": ("cit turin", "citturin"),
    "Crocetta": ("crocetta",),
    "Centro": ("centro storico", "centro"),
    "Cenisia": ("cenisia",),
    "San Donato": ("san donato",),
    "Borgo Po": ("borgo po", "gran madre"),
    "San Salvario": ("san salvario",),
    "Aurora": ("aurora",),
    "Barriera di Milano": ("barriera di milano", "barriera"),
    "Vanchiglia": ("vanchiglia",),
    "Campidoglio": ("campidoglio",),
    "Borgo San Paolo": ("borgo san paolo", "san paolo"),
    "Valdocco": ("valdocco",),
    "Madonna di Campagna": ("madonna di campagna",),
    "Mirafiori Nord": ("mirafiori nord",),
    "Mirafiori Sud": ("mirafiori sud",),
}


def parse_italian_number(value: str) -> float:
    cleaned = re.sub(r"[^\d,.-]", "", value.strip())
    if not cleaned:
        raise ValueError("number is empty")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") == 1 and len(cleaned.rsplit(".", 1)[1]) == 3:
        cleaned = cleaned.replace(".", "")
    return float(cleaned)


def detect_district(text: str) -> Optional[str]:
    lowered = text.casefold()
    for district, aliases in DISTRICT_ALIASES.items():
        if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered) for alias in aliases):
            return district
    return None


def _present(text: str, positive: tuple[str, ...], negative: tuple[str, ...] = ()) -> Optional[bool]:
    lowered = text.casefold()
    if any(item in lowered for item in negative):
        return False
    if any(item in lowered for item in positive):
        return True
    return None


class IdealistaMarkdownAdapter:
    """Parse listing cards captured as Markdown from idealista.it."""

    source = "idealista"
    link_pattern = re.compile(
        r"\[(?P<title>.*?)\]\((?P<url>https?://(?:www\.)?idealista\.it/immobile/(?P<id>\d+)/?)\)",
        re.IGNORECASE | re.DOTALL,
    )

    def parse(self, text: str, target_district: Optional[str] = None) -> List[Listing]:
        matches = list(self.link_pattern.finditer(text))
        listings: List[Listing] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.start():end]
            listing = self._parse_block(block, match)
            if listing is not None:
                if listing.district is None and target_district:
                    listing = replace(
                        listing,
                        district=target_district,
                        field_confidence={**listing.field_confidence, "district": 0.35},
                    )
                listings.append(listing)
        return listings

    def _parse_block(self, block: str, match: re.Match[str]) -> Optional[Listing]:
        price_match = re.search(r"(\d[\d.,]*)\s*€\s*(?:/\s*)?mese", block, re.IGNORECASE)
        if not price_match:
            return None
        area_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m[²2]", block, re.IGNORECASE)
        rooms_match = re.search(r"(\d+(?:[.,]\d+)?)\s*locali", block, re.IGNORECASE)
        expenses_match = re.search(
            r"(?:spese\s+condominiali|condominio)\D{0,20}(\d[\d.,]*)\s*€",
            block,
            re.IGNORECASE,
        )
        lowered = block.casefold()
        if "monolocale" in lowered or "1 locale" in lowered:
            property_type = "studio"
        elif "bilocale" in lowered or "2 locali" in lowered:
            property_type = "bilocale"
        elif "trilocale" in lowered or "3 locali" in lowered:
            property_type = "trilocale"
        elif "camera" in lowered or "stanza" in lowered:
            property_type = "room"
        else:
            property_type = "apartment"

        heating = None
        if "riscaldamento autonomo" in lowered:
            heating = "independent"
        elif "riscaldamento centralizzato" in lowered:
            heating = "centralized"
        district = detect_district(block)
        return Listing(
            id=f"idealista:{match.group('id')}",
            source=self.source,
            title=" ".join(match.group("title").split()),
            url=match.group("url"),
            base_rent=parse_italian_number(price_match.group(1)),
            mandatory_expenses=parse_italian_number(expenses_match.group(1)) if expenses_match else None,
            area_sqm=parse_italian_number(area_match.group(1)) if area_match else None,
            rooms=parse_italian_number(rooms_match.group(1)) if rooms_match else None,
            property_type=property_type,
            district=district,
            furnished=_present(block, ("arredato", "arredata"), ("non arredato", "non arredata")),
            has_ac=_present(block, ("aria condizionata", "climatizzatore"), ("senza aria condizionata",)),
            has_elevator=_present(block, ("ascensore",), ("senza ascensore",)),
            heating=heating,
            extraction_confidence=0.80,
            field_confidence={
                "base_rent": 0.95,
                "mandatory_expenses": 0.85 if expenses_match else 0.0,
                "area_sqm": 0.90 if area_match else 0.0,
                "district": 0.75 if district else 0.0,
            },
            raw={"captured_text_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest()},
        )
