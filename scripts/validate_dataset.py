"""
CI gate for pramaana_data.py.

Validates every entry in the seed dataset against the schema PR authors are
supposed to follow (see CONTRIBUTING.md). Exits non-zero with a readable
report if anything is malformed, so a bad dataset PR fails CI instead of
silently landing in main.
"""
import re
import sys
import urllib.request
from pathlib import Path

REQUIRED_STR_FIELDS = [
    "article_title", "source_url", "outlet", "region",
    "verdict", "source_funding", "narrative_beneficiary",
]
VALID_REGIONS = {"india", "global", "official"}
VALID_CLAIM_TYPES = {"fact", "opinion", "contested", "unverifiable"}
VALID_STANCES = {"agree", "partial", "diverge", "silent"}
EXPECTED_DIMENSIONS = {
    "Source trust", "Claim verifiability", "Cross-source consensus",
    "Narrative transparency", "Contextual completeness",
}


def load_seed():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pramaana_data import PRAMAANA_SEED
    return PRAMAANA_SEED


def check_url_reachable(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD",
                                      headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status < 400
    except Exception:
        return False


def validate_entry(i: int, item: dict, check_urls: bool) -> list:
    errs = []
    tag = f"[entry {i}] {item.get('article_title', '?')!r}"

    for field in REQUIRED_STR_FIELDS:
        if not isinstance(item.get(field), str) or not item[field].strip():
            errs.append(f"{tag}: missing or empty '{field}'")

    if item.get("region") not in VALID_REGIONS:
        errs.append(f"{tag}: region must be one of {VALID_REGIONS}, got {item.get('region')!r}")

    url = item.get("source_url", "")
    if url and not re.match(r"^https?://", url):
        errs.append(f"{tag}: source_url must start with http:// or https://")
    elif url and check_urls and not check_url_reachable(url):
        errs.append(f"{tag}: source_url not reachable: {url}")

    score = item.get("overall_score")
    if not isinstance(score, int) or not (0 <= score <= 100):
        errs.append(f"{tag}: overall_score must be an int 0-100, got {score!r}")

    dims = item.get("dimensions") or []
    if len(dims) != 5:
        errs.append(f"{tag}: expected exactly 5 dimensions, got {len(dims)}")
    dim_names = {d.get("name") for d in dims}
    if dim_names != EXPECTED_DIMENSIONS:
        errs.append(f"{tag}: dimension names must be exactly {EXPECTED_DIMENSIONS}, got {dim_names}")
    for d in dims:
        ds = d.get("score")
        if not isinstance(ds, int) or not (0 <= ds <= 100):
            errs.append(f"{tag}: dimension {d.get('name')!r} score must be an int 0-100, got {ds!r}")

    claims = item.get("claims") or []
    if len(claims) != 4:
        errs.append(f"{tag}: expected exactly 4 claims, got {len(claims)}")
    for c in claims:
        if c.get("type") not in VALID_CLAIM_TYPES:
            errs.append(f"{tag}: claim type must be one of {VALID_CLAIM_TYPES}, got {c.get('type')!r}")

    cross = item.get("cross_source") or []
    if len(cross) != 4:
        errs.append(f"{tag}: expected exactly 4 cross_source entries, got {len(cross)}")
    for cs in cross:
        if cs.get("stance") not in VALID_STANCES:
            errs.append(f"{tag}: cross_source stance must be one of {VALID_STANCES}, got {cs.get('stance')!r}")

    missing = item.get("missing_context") or []
    if len(missing) != 3:
        errs.append(f"{tag}: expected exactly 3 missing_context items, got {len(missing)}")

    return errs


def main():
    check_urls = "--check-urls" in sys.argv
    seed = load_seed()

    urls = [item.get("source_url") for item in seed]
    dupes = {u for u in urls if urls.count(u) > 1}
    all_errors = []
    if dupes:
        all_errors.append(f"Duplicate source_url entries found: {dupes}")

    for i, item in enumerate(seed):
        all_errors.extend(validate_entry(i, item, check_urls))

    if all_errors:
        print(f"✗ {len(all_errors)} problem(s) found in pramaana_data.py:\n")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"✓ pramaana_data.py: {len(seed)} entries, all valid.")


if __name__ == "__main__":
    main()
