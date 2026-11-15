"""Review UI: browse receipts, compare extractors with the labels, and work the review queue.

    uvicorn tally.server:app --port 8001

The page shows, for any receipt, the image, the OCR text, what each extractor returned,
which validation flags fired, and whether it would be auto-accepted or sent to a person.
A reviewer can correct the fields and approve; corrections are stored in data/reviews.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import baseline
from .config import get_settings
from .data import DEFAULT_PATH, FIELDS, Receipt, load_receipts
from .extract import extract
from .llm import LLM, LLMError, OpenAICompatLLM
from .ocr import OCR_PATH
from .run import RUNS_DIR, build_report, load_run
from .score import score_document
from .validate import validate

STATIC = Path(__file__).parent / "static"
BASELINE = "baseline (rules)"


class ReviewRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


def export_images(parquet: Path, image_dir: Path) -> None:
    """Write each receipt image to its own file once, so the page can load them quickly."""
    import pyarrow.parquet as pq

    image_dir.mkdir(parents=True, exist_ok=True)
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=16, columns=["key", "image"]):
        for row in batch.to_pylist():
            target = image_dir / f"{row['key']}.jpg"
            if not target.exists():
                target.write_bytes(row["image"]["bytes"])


class State:
    def __init__(self, parquet: Path, ocr_path: Path, runs_dir: Path, image_dir: Path,
                 reviews_path: Path, receipts: list[Receipt] | None, llm: LLM | None):
        self.parquet, self.ocr_path, self.runs_dir = parquet, ocr_path, runs_dir
        self.image_dir, self.reviews_path = image_dir, reviews_path
        self.llm = llm
        self._fixed = receipts
        self._stamp: tuple | None = None
        self._receipts: dict[str, Receipt] = {}
        self._runs: dict[str, dict[str, dict]] = {}

    def _signature(self) -> tuple:
        files = [self.ocr_path, *sorted(self.runs_dir.glob("*.jsonl"))] if self.runs_dir.exists() else [self.ocr_path]
        return tuple((str(f), f.stat().st_mtime_ns) for f in files if f.exists())

    def refresh(self) -> None:
        """Reload receipts and saved runs when a file changed (OCR or a run still in progress)."""
        stamp = self._signature()
        if stamp == self._stamp and self._receipts:
            return
        self._stamp = stamp
        if self._fixed is not None:
            receipts = self._fixed
        else:
            receipts = list(load_receipts(self.parquet, ocr_path=self.ocr_path if self.ocr_path.exists() else None))
        self._receipts = {r.key: r for r in receipts}
        self._runs = {BASELINE: {}}
        for r in receipts:
            fields = baseline.extract(r.text)
            self._runs[BASELINE][r.key] = {"key": r.key, "fields": fields, "flags": validate(fields, r.text)}
        if self.runs_dir.exists():
            for path in sorted(self.runs_dir.glob("*.jsonl")):
                if path.stem.startswith(("baseline", "smoke")):
                    continue
                records = {k: v for k, v in load_run(path).items() if k in self._receipts}
                if records:
                    self._runs[path.stem] = records

    @property
    def receipts(self) -> dict[str, Receipt]:
        self.refresh()
        return self._receipts

    @property
    def runs(self) -> dict[str, dict[str, dict]]:
        self.refresh()
        return self._runs

    def reviews(self) -> dict[str, dict]:
        if not self.reviews_path.exists():
            return {}
        return json.loads(self.reviews_path.read_text(encoding="utf-8"))

    def get_llm(self) -> tuple[LLM, str]:
        settings = get_settings()
        label = settings.model.replace("/", "_").replace(":", "_") or "model"
        if self.llm is None:
            if not settings.configured:
                raise HTTPException(503, "No model configured. Copy .env.example to .env and fill in a provider.")
            self.llm = OpenAICompatLLM(settings.base_url, settings.api_key, settings.model,
                                       extra=json.loads(os.environ.get("LLM_EXTRA", "") or "{}"))
        return self.llm, label


def _view(record: dict, receipt: Receipt) -> dict:
    scores = score_document(record["fields"], receipt.truth)
    return {"fields": record["fields"], "flags": record["flags"], "scores": scores,
            "usage": {k: record[k] for k in ("prompt_tokens", "completion_tokens", "latency_ms") if k in record}}


def create_app(*, parquet: Path = DEFAULT_PATH, ocr_path: Path = OCR_PATH, runs_dir: Path = RUNS_DIR,
               image_dir: Path | None = None, reviews_path: Path | None = None,
               receipts: list[Receipt] | None = None, llm: LLM | None = None) -> FastAPI:
    app = FastAPI(title="Tally")
    state = State(parquet, ocr_path, runs_dir, image_dir or parquet.parent / "images",
                  reviews_path or parquet.parent / "reviews.json", receipts, llm)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/api/runs")
    def runs() -> list[dict]:
        return [{"label": label, "receipts": len(records)} for label, records in state.runs.items()]

    @app.get("/api/receipts")
    def receipts_list(run: str = BASELINE) -> list[dict]:
        records = state.runs.get(run)
        if records is None:
            raise HTTPException(404, "Unknown run.")
        reviewed = state.reviews()
        rows = []
        for key, receipt in state.receipts.items():
            record = records.get(key)
            row = {"key": key, "status": "not_run", "correct": None, "reviewed": key in reviewed}
            if record:
                scores = score_document(record["fields"], receipt.truth)
                row["status"] = "review" if record["flags"] else "auto"
                row["correct"] = all(scores[f]["normalized"] for f in ("date", "total"))
                row["all_correct"] = all(scores[f]["near"] for f in FIELDS)
            rows.append(row)
        return rows

    @app.get("/api/summary")
    def summary(run: str = BASELINE) -> dict:
        records = state.runs.get(run)
        if records is None:
            raise HTTPException(404, "Unknown run.")
        _, result = build_report(run, records, list(state.receipts.values()))
        result["total_receipts"] = len(state.receipts)
        return result

    @app.get("/api/receipts/{key}")
    def receipt_detail(key: str) -> dict:
        receipt = state.receipts.get(key)
        if receipt is None:
            raise HTTPException(404, "Unknown receipt.")
        return {"key": key, "text": receipt.text, "truth": receipt.truth,
                "runs": {label: _view(records[key], receipt) for label, records in state.runs.items() if key in records},
                "review": state.reviews().get(key)}

    @app.get("/api/receipts/{key}/image")
    def receipt_image(key: str) -> FileResponse:
        if key not in state.receipts:
            raise HTTPException(404, "Unknown receipt.")
        path = state.image_dir / f"{key}.jpg"
        if not path.exists():
            export_images(state.parquet, state.image_dir)
        if not path.exists():
            raise HTTPException(404, "No image for this receipt.")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/receipts/{key}/extract")
    def extract_now(key: str) -> dict:
        """Run the configured model on this receipt now, and add the result to that model's run."""
        receipt = state.receipts.get(key)
        if receipt is None:
            raise HTTPException(404, "Unknown receipt.")
        llm, label = state.get_llm()
        try:
            result = extract(llm, receipt.text)
        except LLMError as exc:
            raise HTTPException(502, f"Model provider error: {exc}") from exc
        record = {"key": key, "fields": result.fields,
                  "flags": result.problems + validate(result.fields, receipt.text),
                  "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens,
                  "latency_ms": result.latency_ms}
        path = state.runs_dir / f"{label}.jsonl"
        if key not in load_run(path):  # keep the first result, as the batch runner would
            state.runs_dir.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as out:
                out.write(json.dumps(record) + "\n")
        return {"run": label, **_view(record, receipt)}

    @app.post("/api/receipts/{key}/review")
    def save_review(key: str, req: ReviewRequest) -> dict:
        if key not in state.receipts:
            raise HTTPException(404, "Unknown receipt.")
        fields = {f: " ".join(str(req.fields.get(f, "")).split())[:300] for f in FIELDS}
        reviews = state.reviews()
        reviews[key] = {"fields": fields, "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        state.reviews_path.parent.mkdir(parents=True, exist_ok=True)
        state.reviews_path.write_text(json.dumps(reviews, indent=1), encoding="utf-8")
        return reviews[key]

    return app


app = create_app()
