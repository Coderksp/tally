"""Run an extractor over the dataset and write a scored report.

    python -m tally.run baseline                 # rule-based, free, whole dataset
    python -m tally.run llm --limit 50           # model-based, first 50 receipts
    python -m tally.run llm                      # resumes: only receipts not yet done
    python -m tally.run report <label>           # re-score a saved run without calling a model

Each extraction is appended to runs/<label>.jsonl the moment it finishes, so a run that
stops (daily quota, closed laptop) continues where it left off. Scoring happens afterwards
from that file, so the scoring rules can change without paying for the model again.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from . import baseline
from .config import ROOT, get_settings
from .data import FIELDS, Receipt, load_receipts
from .extract import extract
from .llm import LLM, LLMError, OpenAICompatLLM, QuotaExhausted
from .ocr import OCR_PATH
from .score import LEVELS, aggregate, score_document
from .validate import validate

RUNS_DIR = ROOT / "runs"
RESULTS_DIR = ROOT / "results"
MAX_CONSECUTIVE_ERRORS = 3


def load_run(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["key"]: r for r in records}


def current_flags(record: dict, receipt: Receipt) -> list[str]:
    """Flags for a saved result under today's validation rules.

    Problems found while reading the model's reply are kept from the run. Validation flags
    are recomputed from the saved fields, so fixing a validation rule never needs a rerun.
    """
    kept = [f for f in record.get("flags", []) if f.startswith("reply:") or f.endswith(":wrong_type")]
    return kept + validate(record["fields"], receipt.text)


def run_baseline(receipts: list[Receipt], path: Path) -> None:
    with path.open("w", encoding="utf-8") as out:
        for receipt in receipts:
            fields = baseline.extract(receipt.text)
            out.write(json.dumps({"key": receipt.key, "fields": fields,
                                  "flags": validate(fields, receipt.text)}) + "\n")


def run_llm(receipts: list[Receipt], path: Path, llm: LLM, log=print) -> str:
    """Extract every receipt not already in the run file. Returns why it stopped."""
    done = load_run(path)
    todo = [r for r in receipts if r.key not in done]
    log(f"{len(done)} already done, {len(todo)} to go")
    streak = 0
    with path.open("a", encoding="utf-8") as out:
        for i, receipt in enumerate(todo, 1):
            try:
                result = extract(llm, receipt.text)
            except QuotaExhausted as exc:
                return f"quota exhausted after {i - 1} receipts this session: {exc}"
            except LLMError as exc:
                streak += 1
                log(f"  error on {receipt.key}: {str(exc)[:160]}")
                if streak >= MAX_CONSECUTIVE_ERRORS:
                    return f"stopped after {MAX_CONSECUTIVE_ERRORS} provider errors in a row"
                continue  # not saved, so the next run retries it
            streak = 0
            flags = result.problems + validate(result.fields, receipt.text)
            out.write(json.dumps({"key": receipt.key, "fields": result.fields, "flags": flags,
                                  "prompt_tokens": result.prompt_tokens,
                                  "completion_tokens": result.completion_tokens,
                                  "latency_ms": result.latency_ms}) + "\n")
            out.flush()
            if i % 10 == 0:
                log(f"  {i}/{len(todo)}")
    return "complete"


# ---- report ------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{x:.1%}"


def build_report(label: str, records: dict[str, dict], receipts: list[Receipt],
                 price_in: float = 0.0, price_out: float = 0.0) -> tuple[str, dict]:
    rows = [(r, {**records[r.key], "flags": current_flags(records[r.key], r)}) for r in receipts if r.key in records]
    scored = [score_document(rec["fields"], r.truth) for r, rec in rows]
    overall = aggregate(scored)
    n = overall["n"]
    lines = [f"# Extraction report: {label}", "",
             f"{n} receipts scored (of {len(receipts)} in the dataset).", "",
             "## Accuracy", "",
             "| Field | Exact string | Same value | Near match |", "|---|---|---|---|"]
    for f in FIELDS:
        a = overall["fields"].get(f, {})
        lines.append(f"| {f} | {_pct(a.get('exact', 0))} | {_pct(a.get('normalized', 0))} | {_pct(a.get('near', 0))} |")
    lines.append("| **all four fields** | " + " | ".join(
        _pct(overall["all_fields"].get(lvl, 0)) for lvl in LEVELS) + " |")
    lines += ["", "Same value: equal amounts, equal dates, text equal ignoring case, spacing and punctuation.",
              "Near match: text at least 90% similar; allows for typos in the dataset's own labels.", ""]

    # Review routing: does the absence of flags predict a correct extraction?
    def right(doc: dict, fields: tuple[str, ...]) -> bool:
        return all(doc[f]["normalized"] for f in fields)

    summary = {"n": n, "overall": overall, "routing": {}}
    lines += ["## Review routing", "",
              "A receipt is auto-accepted when validation raises no flag, and sent to a person otherwise.",
              "Validation never sees the labels.", ""]
    for title, fields in (("date and total", ("date", "total")), ("all four fields", FIELDS)):
        auto = [doc for doc, (_, rec) in zip(scored, rows) if not rec["flags"]]
        review = [doc for doc, (_, rec) in zip(scored, rows) if rec["flags"]]
        wrong = [bool(rec["flags"]) for doc, (_, rec) in zip(scored, rows) if not right(doc, fields)]
        stats = {
            "auto_n": len(auto), "review_n": len(review),
            "auto_accuracy": sum(right(d, fields) for d in auto) / len(auto) if auto else 0.0,
            "review_accuracy": sum(right(d, fields) for d in review) / len(review) if review else 0.0,
            "errors": len(wrong), "errors_caught": sum(wrong),
        }
        summary["routing"][title] = stats
        lines += [f"**Judged on {title}**", "",
                  "| Queue | Receipts | Correct |", "|---|---|---|",
                  f"| Auto-accepted | {stats['auto_n']} ({_pct(stats['auto_n'] / n if n else 0)}) | {_pct(stats['auto_accuracy'])} |",
                  f"| Sent to review | {stats['review_n']} ({_pct(stats['review_n'] / n if n else 0)}) | {_pct(stats['review_accuracy'])} |",
                  "", f"Of {stats['errors']} receipts with a wrong value, review caught {stats['errors_caught']}"
                  + (f" ({_pct(stats['errors_caught'] / stats['errors'])})." if stats["errors"] else "."), ""]

    flag_counts = Counter(flag for _, rec in rows for flag in rec["flags"])
    if flag_counts:
        lines += ["## Flags raised", "", "| Flag | Receipts |", "|---|---|"]
        lines += [f"| {flag} | {count} |" for flag, count in flag_counts.most_common()]
        lines.append("")

    with_usage = [rec for _, rec in rows if "prompt_tokens" in rec]
    if with_usage:
        m = len(with_usage)
        p = sum(r["prompt_tokens"] for r in with_usage) / m
        c = sum(r["completion_tokens"] for r in with_usage) / m
        latency = sorted(r["latency_ms"] for r in with_usage)
        lines += ["## Cost and speed", "",
                  f"- Tokens per receipt: {p:.0f} in, {c:.0f} out",
                  f"- Model time per receipt: median {latency[m // 2]} ms, 90th percentile {latency[int(m * 0.9)]} ms"]
        if price_in or price_out:
            cost = p / 1e6 * price_in + c / 1e6 * price_out
            lines.append(f"- Cost per receipt: ${cost:.5f} (${cost * 1000:.2f} per 1,000)")
            summary["cost_per_receipt"] = cost
        summary["tokens"] = {"prompt": p, "completion": c}
        lines.append("")

    lines += ["## Wrong values", ""]
    for f in FIELDS:
        misses = [(r, rec) for (r, rec), doc in zip(rows, scored) if not doc[f]["normalized"]]
        lines += [f"### {f}: {len(misses)} wrong", ""]
        if misses:
            lines += ["| Receipt | Extracted | Label | Flags |", "|---|---|---|---|"]
            for r, rec in misses[:15]:
                cells = [r.key, rec["fields"].get(f, ""), r.truth[f], ", ".join(rec["flags"])]
                lines.append("| " + " | ".join(str(c).replace("|", "/")[:90] for c in cells) + " |")
            if len(misses) > 15:
                lines.append(f"| ... and {len(misses) - 15} more | | | |")
            lines.append("")
    return "\n".join(lines) + "\n", summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and score receipt extraction.")
    parser.add_argument("mode", choices=["baseline", "llm", "report"])
    parser.add_argument("label", nargs="?", default="", help="run name (default: 'baseline' or the model name)")
    parser.add_argument("--limit", type=int, default=None, help="only the first N receipts")
    parser.add_argument("--text", choices=["ocr", "dataset"], default="ocr",
                        help="ocr: our OCR of the images (run tally.ocr first). "
                             "dataset: the bundled OCR text, which is cut off at commas")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    if args.text == "ocr" and not OCR_PATH.exists():
        print("No OCR output yet. Run: python -m tally.ocr", file=sys.stderr)
        return 2
    receipts = list(load_receipts(limit=args.limit, ocr_path=OCR_PATH if args.text == "ocr" else None))
    settings = get_settings()
    RUNS_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    if args.mode == "baseline":
        label = args.label or "baseline"
        run_baseline(receipts, RUNS_DIR / f"{label}.jsonl")
    elif args.mode == "llm":
        if not settings.configured:
            print("No model configured. Copy .env.example to .env and fill in a provider.", file=sys.stderr)
            return 2
        label = args.label or settings.model.replace("/", "_").replace(":", "_")
        extra = json.loads(os.environ.get("LLM_EXTRA", "") or "{}")
        llm = OpenAICompatLLM(settings.base_url, settings.api_key, settings.model, extra=extra)
        print(f"Model: {settings.model}", flush=True)
        outcome = run_llm(receipts, RUNS_DIR / f"{label}.jsonl", llm,
                          log=lambda message: print(message, flush=True))
        print(f"Run {outcome}", flush=True)
    else:
        label = args.label
        if not label or not (RUNS_DIR / f"{label}.jsonl").exists():
            print("Give the label of an existing run in runs/.", file=sys.stderr)
            return 2

    records = load_run(RUNS_DIR / f"{label}.jsonl")
    if not records:
        print("Nothing to score yet.", file=sys.stderr)
        return 1
    report, summary = build_report(label, records, receipts,
                                   settings.price_input_per_m, settings.price_output_per_m)
    (RESULTS_DIR / f"{label}.md").write_text(report, encoding="utf-8")
    fields = summary["overall"]["fields"]
    print(f"\n{summary['n']} receipts | same-value accuracy: "
          + ", ".join(f"{f} {_pct(fields[f]['normalized'])}" for f in FIELDS)
          + f" | all four {_pct(summary['overall']['all_fields']['normalized'])}")
    print(f"Report: results/{label}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
