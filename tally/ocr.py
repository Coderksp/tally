"""Run a local OCR engine over the receipt images and cache the result.

    python -m tally.ocr            # all receipts, resumable
    python -m tally.ocr --limit 20

The dataset ships its own OCR text, but that text is cut off at every comma (see README),
which removes most of each address. This module reads the images instead. Output goes to
data/ocr.jsonl as one {"key", "words", "bboxes"} record per receipt, in the same shape the
dataset uses, so the rest of the pipeline does not care where the text came from.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import unicodedata
from pathlib import Path

from .data import DEFAULT_PATH

OCR_PATH = DEFAULT_PATH.parent / "ocr.jsonl"
SCALE = 1  # measured on 16 receipts: 2x was twice as slow and found slightly fewer labels


def clean(text: str) -> str:
    """Fold full-width and other compatibility characters to plain ones (':' for a wide colon)."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def read_image(engine, image_bytes: bytes, scale: int = SCALE) -> tuple[list[str], list[list[int]]]:
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if scale != 1:
        image = image.resize((image.width * scale, image.height * scale), Image.LANCZOS)
    result, _ = engine(np.array(image))
    words, boxes = [], []
    for quad, text, _confidence in result or []:
        text = clean(text)
        if not text:
            continue
        xs, ys = [p[0] for p in quad], [p[1] for p in quad]
        words.append(text)
        boxes.append([int(min(xs) / scale), int(min(ys) / scale), int(max(xs) / scale), int(max(ys) / scale)])
    return words, boxes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCR the receipt images into data/ocr.jsonl.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    import pyarrow.parquet as pq
    from rapidocr_onnxruntime import RapidOCR

    done = set()
    if OCR_PATH.exists():
        done = {json.loads(line)["key"] for line in OCR_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}
    engine = RapidOCR()
    table = pq.ParquetFile(DEFAULT_PATH)
    seen = 0
    with OCR_PATH.open("a", encoding="utf-8") as out:
        for batch in table.iter_batches(batch_size=16, columns=["key", "image"]):
            for row in batch.to_pylist():
                if args.limit is not None and seen >= args.limit:
                    return 0
                seen += 1
                if row["key"] in done:
                    continue
                words, boxes = read_image(engine, row["image"]["bytes"])
                out.write(json.dumps({"key": row["key"], "words": words, "bboxes": boxes}) + "\n")
                out.flush()
                if seen % 20 == 0:
                    print(f"{seen} receipts read", flush=True)
    print(f"done: {seen} receipts", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
