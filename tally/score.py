"""Compare extractions with the dataset labels, at three levels of strictness.

  exact       the strings are identical (the original SROIE challenge metric)
  normalized  the parsed value is the same: equal amounts, equal dates, text equal once
              case, spacing and punctuation are ignored
  near        text fields only: at least 90% similar after normalising. The labels contain
              typos and truncations, so this is reported separately, never as the headline.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from .data import FIELDS
from .normalize import parse_amount, parse_date, text_key, tokens

NEAR_THRESHOLD = 0.90
LEVELS = ("exact", "normalized", "near")


def score_field(field: str, predicted: str, truth: str) -> dict[str, bool]:
    predicted, truth = (predicted or "").strip(), (truth or "").strip()
    exact = predicted == truth
    if field == "total":
        p, t = parse_amount(predicted), parse_amount(truth)
        normalized = exact or (p is not None and p == t)
        near = normalized
    elif field == "date":
        p, t = parse_date(predicted), parse_date(truth)
        normalized = exact or (p is not None and p == t)
        near = normalized
    else:
        normalized = exact or (bool(text_key(truth)) and text_key(predicted) == text_key(truth))
        a, b = " ".join(tokens(predicted)), " ".join(tokens(truth))
        near = normalized or (bool(a) and SequenceMatcher(None, a, b).ratio() >= NEAR_THRESHOLD)
    return {"exact": exact, "normalized": normalized, "near": near}


def score_document(predicted: dict[str, str], truth: dict[str, str]) -> dict[str, dict[str, bool]]:
    return {f: score_field(f, predicted.get(f, ""), truth.get(f, "")) for f in FIELDS}


def aggregate(scored: list[dict[str, dict[str, bool]]]) -> dict:
    """Per-field accuracy at each level, plus the share of documents with all four fields right."""
    n = len(scored)
    if n == 0:
        return {"n": 0, "fields": {}, "all_fields": {}}
    return {
        "n": n,
        "fields": {f: {lvl: sum(doc[f][lvl] for doc in scored) / n for lvl in LEVELS} for f in FIELDS},
        "all_fields": {lvl: sum(all(doc[f][lvl] for f in FIELDS) for doc in scored) / n for lvl in LEVELS},
    }
