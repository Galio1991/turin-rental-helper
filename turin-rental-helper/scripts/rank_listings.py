#!/usr/bin/env python3
"""Rank canonical JSON listings using explicit renter preferences."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from rental_helper import recommend


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", required=True, type=Path, help="JSON array of canonical listings")
    parser.add_argument("--preferences", required=True, type=Path, help="JSON object with constraints and weights")
    parser.add_argument("--output", type=Path, help="write JSON here; stdout when omitted")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    raw_listings = load_json(args.listings)
    raw_preferences: Dict[str, Any] = load_json(args.preferences)
    if not isinstance(raw_listings, list):
        parser.error("--listings must contain a JSON array")
    if not isinstance(raw_preferences, dict):
        parser.error("--preferences must contain a JSON object")

    payload = json.dumps(
        recommend(raw_listings, raw_preferences, limit=args.limit).to_dict(),
        ensure_ascii=False,
        indent=2,
    )
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
