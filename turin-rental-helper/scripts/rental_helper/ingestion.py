"""Normalization and de-duplication for source adapter output."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable, List, Sequence, Tuple
from urllib.parse import urlsplit, urlunsplit

from .models import Listing


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    path = re.sub(r"/+$", "", parts.path)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def normalize_listing(listing: Listing) -> Listing:
    return replace(
        listing,
        url=canonical_url(listing.url),
        title=" ".join(listing.title.split()),
        district=" ".join(listing.district.split()) if listing.district else None,
        address=" ".join(listing.address.split()) if listing.address else None,
    )


def deduplicate(listings: Iterable[Listing]) -> Tuple[List[Listing], List[Tuple[str, str]]]:
    unique: List[Listing] = []
    duplicates: List[Tuple[str, str]] = []
    seen = {}
    for raw in listings:
        listing = normalize_listing(raw)
        key = canonical_url(listing.url)
        if not key:
            key = "|".join(
                [
                    listing.source.lower(),
                    listing.title.lower(),
                    listing.district.lower() if listing.district else "",
                    str(listing.base_rent),
                ]
            )
        if key in seen:
            duplicates.append((listing.id, seen[key]))
            continue
        seen[key] = listing.id
        unique.append(listing)
    return unique, duplicates
