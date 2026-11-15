"""Load SROIE receipts and rebuild readable text from the OCR line boxes.

The dataset gives each receipt as a list of text snippets with bounding boxes. A total and
its label ("TOTAL" ... "193.00") are usually separate snippets on the same row, so the text
is rebuilt row by row: snippets whose boxes overlap vertically are joined left to right.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

FIELDS = ("company", "date", "address", "total")
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "sroie-test.parquet"


@dataclass(frozen=True)
class Receipt:
    key: str
    text: str                 # layout-rebuilt text, one receipt row per line
    truth: dict[str, str]     # the dataset's labels for FIELDS


def layout_text(words: list[str], bboxes: list[list[int]]) -> str:
    """Join OCR snippets into rows. Boxes are [x0, y0, x1, y1]."""
    items = sorted(zip(bboxes, words), key=lambda bw: (bw[0][1], bw[0][0]))
    rows: list[list[tuple[list[int], str]]] = []
    for box, word in items:
        word = " ".join(str(word).split())
        if not word:
            continue
        if rows:
            last = rows[-1]
            top = min(b[1] for b, _ in last)
            bottom = max(b[3] for b, _ in last)
            overlap = min(bottom, box[3]) - max(top, box[1])
            height = max(1, min(bottom - top, box[3] - box[1]))
            if overlap / height >= 0.5:  # same visual row
                last.append((box, word))
                continue
        rows.append([(box, word)])
    return "\n".join("  ".join(w for _, w in sorted(row, key=lambda bw: bw[0][0])) for row in rows)


def load_receipts(path: Path = DEFAULT_PATH, limit: int | None = None,
                  ocr_path: Path | None = None) -> Iterator[Receipt]:
    """Receipts with their labels. Text comes from `ocr_path` (our own OCR of the images, as
    written by tally.ocr) when given, otherwise from the dataset's bundled, truncated OCR.
    Receipts missing from the OCR file are skipped."""
    import json

    import pyarrow.parquet as pq  # imported here so the rest of the package works without it

    ocr = None
    if ocr_path is not None:
        ocr = {r["key"]: r for r in map(json.loads, filter(str.strip, ocr_path.read_text(encoding="utf-8").splitlines()))}
    table = pq.read_table(path, columns=["key", "entities", "words", "bboxes"])
    for i, row in enumerate(table.to_pylist()):
        if limit is not None and i >= limit:
            return
        source = row if ocr is None else ocr.get(row["key"])
        if source is None:
            continue
        yield Receipt(
            key=row["key"],
            text=layout_text(source["words"], source["bboxes"]),
            truth={f: (row["entities"].get(f) or "").strip() for f in FIELDS},
        )
