# Turin Rental Helper development guide

This repository contains a platform-independent Python decision engine and a thin Agent Skill entrypoint.

## Ground rules

- Require Python 3.10+ and keep the core standard-library-only unless a source adapter has a demonstrated dependency.
- Treat `turin-rental-helper/scripts/rental_helper/` as the source of truth. Top-level `comparator.py` and `scraper.py` are compatibility wrappers.
- Source adapters parse content already captured with authorization; they do not make network requests.
- Preserve `None` for unknown values. Never convert an absent amenity to `False` or an unknown risk value to a neutral score.
- Keep hard constraints separate from soft utility scoring.
- Scoring functions must be candidate-independent. Diversification may reorder presentation, but must not mutate the underlying score.
- Do not derive safety conclusions from district names or demographic composition. Any safety metric needs source, date, geographic granularity, and confidence.
- Do not describe `assets/data/turin-districts.json` as authoritative; it is legacy, unverified reference data and is excluded from default v2 ranking.

## Verification

Run before handing off changes:

```bash
cd turin-rental-helper
python3 -m unittest discover -s tests -v
python3 scripts/rank_listings.py \
  --listings tests/fixtures/listings.json \
  --preferences tests/fixtures/preferences.json \
  --limit 2
```

Algorithm changes should include behavioral tests. At minimum preserve monotonicity for cost and commute, explicit missing-data behavior, and candidate-pool independence.
