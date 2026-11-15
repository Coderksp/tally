"""Walk one receipt through every stage and print what each stage produced.

    python -m tally.demo              # first receipt
    python -m tally.demo 5            # sixth receipt
    python -m tally.demo 5 --no-llm   # skip the model call

Also saves the receipt image to data/demo-<key>.jpg so you can look at the original.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import baseline
from .config import get_settings
from .data import DEFAULT_PATH, FIELDS, load_receipts
from .extract import extract
from .llm import LLMError, OpenAICompatLLM
from .ocr import OCR_PATH
from .score import score_document
from .validate import validate


def _table(title: str, fields: dict[str, str], truth: dict[str, str], flags: list[str]) -> None:
    scores = score_document(fields, truth)
    print(f"\n{title}")
    for f in FIELDS:
        verdict = "correct" if scores[f]["normalized"] else ("near match" if scores[f]["near"] else "WRONG")
        print(f"  {f:<8} {fields.get(f, '')!r:<72} {verdict}")
    print(f"  validation flags: {', '.join(flags) if flags else 'none'}"
          f"  ->  {'send to human review' if flags else 'auto-accept'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show one receipt going through the pipeline.")
    parser.add_argument("index", type=int, nargs="?", default=0)
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    receipts = list(load_receipts(ocr_path=OCR_PATH if OCR_PATH.exists() else None))
    if not 0 <= args.index < len(receipts):
        print(f"Pick an index from 0 to {len(receipts) - 1}.", file=sys.stderr)
        return 2
    receipt = receipts[args.index]

    import pyarrow.parquet as pq
    keys = pq.read_table(DEFAULT_PATH, columns=["key"]).column("key").to_pylist()
    image = pq.read_table(DEFAULT_PATH, columns=["image"]).slice(keys.index(receipt.key), 1).to_pylist()[0]["image"]
    image_path = DEFAULT_PATH.parent / f"demo-{receipt.key}.jpg"
    image_path.write_bytes(image["bytes"])

    print(f"RECEIPT {receipt.key}   (image saved to {image_path})")
    print("\nSTAGE 1  OCR: text read from the image, rebuilt row by row")
    print("-" * 60)
    print(receipt.text)
    print("-" * 60)

    print("\nWHAT THE DATASET SAYS IS CORRECT (never shown to the extractor or to validation)")
    for f in FIELDS:
        print(f"  {f:<8} {receipt.truth[f]!r}")

    rule_fields = baseline.extract(receipt.text)
    _table("STAGE 2a  Rule-based baseline (regular expressions, no model)",
           rule_fields, receipt.truth, validate(rule_fields, receipt.text))

    if not args.no_llm:
        settings = get_settings()
        if not settings.configured:
            print("\nNo model configured in .env, so the LLM stage was skipped.")
            return 0
        llm = OpenAICompatLLM(settings.base_url, settings.api_key, settings.model,
                              extra=json.loads(os.environ.get("LLM_EXTRA", "") or "{}"))
        try:
            result = extract(llm, receipt.text)
        except LLMError as exc:
            print(f"\nThe model call failed: {exc}")
            return 1
        _table(f"STAGE 2b  LLM extraction ({settings.model})",
               result.fields, receipt.truth, result.problems + validate(result.fields, receipt.text))
        print(f"  cost: {result.prompt_tokens} tokens in, {result.completion_tokens} out, {result.latency_ms} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
