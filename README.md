# Tally

Receipt field extraction with a measured accuracy benchmark: scanned receipt in, four
validated fields out (company, date, address, total), with doubtful results routed to a
person.

Built on the public [SROIE](https://rrc.cvc.uab.es/?ch=13) receipt dataset (361 test
receipts with human labels), so every claim below can be checked against real data.

**Status: first results.** The pipeline, review UI and tests are complete. Two models have
been scored on the first 117 of 361 receipts; the runs stopped at the free tier's daily token
limit and resume from there. See [Results](#results).

## Pipeline

```
image -> OCR -> rebuild rows -> extract (rules or LLM) -> validate -> auto-accept or human review
                                                              |
                                                     score against labels
```

| Stage | What it does | Code |
|---|---|---|
| OCR | Reads the image with a local engine (RapidOCR). Cached, resumable. | [tally/ocr.py](tally/ocr.py) |
| Layout | Joins OCR snippets on the same row, so `TOTAL` and `43.20` end up on one line. | [tally/data.py](tally/data.py) |
| Baseline | Rule-based extractor: no model, no cost. Every LLM number is shown next to it. | [tally/baseline.py](tally/baseline.py) |
| LLM extraction | One call per receipt, JSON reply, parsed defensively. A bad reply becomes empty fields, never a crash. | [tally/extract.py](tally/extract.py) |
| Validation | Checks that need no answer key: is each value printed on the receipt, is the total on a "total" line, does it look like the cash handed over? | [tally/validate.py](tally/validate.py) |
| Scoring | Three levels: identical string, same value, near match. | [tally/score.py](tally/score.py) |
| Runner | Saves each result as it finishes and resumes after a stop (daily quota, closed laptop). | [tally/run.py](tally/run.py) |
| Review UI | Image, extraction, flags and labels side by side, with a correction form. | [tally/server.py](tally/server.py) |

## Why validation matters

An extractor that is 95% accurate is not usable if nobody knows which 5% is wrong. Validation
never sees the labels. It asks whether a value is supported by the receipt itself, and any
flag sends the receipt to a person. The report then measures two things: how accurate the
auto-accepted receipts are, and how many of the wrong ones review caught.

It has a known blind spot, covered by a test: it catches invented values, not a wrong choice
among real ones. A subtotal returned as the total is printed on the receipt and passes.

## Findings so far

**The dataset's bundled OCR text is cut off at commas.** The Hugging Face copy used here
(`jsdnrs/ICDAR2019-SROIE`) ships OCR text with each receipt. None of its 19,386 text snippets
contains a comma: each line stops at the first one. That removes most of every address. Only
24 of 361 label addresses are fully present in that text, against 355 companies, 357 dates
and all 361 totals. A rule-based baseline on that text scores 1.7% on address
([report](results/baseline_dataset-text.md)). So this project reads the images with its own
OCR, which is also closer to a real pipeline.

**Real OCR output is messier than benchmark text.** RapidOCR drops spaces
(`OJCMARKETINGSDNBHD`), misreads characters (`Leve16` for `Level 6`) and glues dates to
whatever follows (`REG#19-18/01/201817:09:21`). Two date-parsing bugs were found this way and
fixed with tests: a year followed directly by a clock time, and a false start (`19-18/01`)
that hid the real date after it.

**Enlarging the images did not help.** On 16 receipts, OCR at 2x size took twice as long
(21 s against 12 s per image on a laptop CPU) and found slightly fewer labels.

## Results

All three extractors on the **same 117 receipts**, reading this project's own OCR text.
"Same value" accuracy: equal amounts, equal dates, text equal ignoring case, spacing and
punctuation.

| Extractor | Company | Date | Address | Total |
|---|---|---|---|---|
| Rule-based baseline | 35.0% | 89.7% | 12.8% | 88.0% |
| openai/gpt-oss-20b | 61.5% | 93.2% | 53.8% | 94.9% |
| openai/gpt-oss-120b | 63.2% | 91.5% | 52.1% | 94.0% |
| *Label present in the OCR text* | *76.1%* | *90.6%* | *58.1%* | *95.7%* |

The last row is how often the correct answer appears in the OCR output at all. It is the
ceiling for an extractor that only copies from the text.

117 receipts is a small sample: one receipt is 0.9 points, so the two models are not
distinguishable here. Reports: [baseline (all 361)](results/baseline.md),
[gpt-oss-20b](results/openai_gpt-oss-20b.md), [gpt-oss-120b](results/openai_gpt-oss-120b.md).

### Review routing, judged on date and total

| Extractor | Auto-accepted | Right among auto-accepted | Wrong receipts caught by review |
|---|---|---|---|
| Rule-based baseline | 101 of 117 (86%) | 89.1% | 13 of 24 |
| openai/gpt-oss-20b | 91 of 117 (78%) | 98.9% | 13 of 14 |
| openai/gpt-oss-120b | 93 of 117 (79%) | 97.8% | 15 of 17 |

With gpt-oss-20b, a person checks 22% of receipts and the other 78% go through with one
wrong date or total in 91.

### What the numbers say

- **OCR is the bottleneck, not the model.** For company and address the models score close
  to the OCR ceiling. No prompt change will fix an address the OCR never read; a better OCR
  engine or a vision model would.
- **The model is worth it over rules, mostly for text fields.** Company goes from 35% to
  62% and address from 13% to 54%. On dates the gain is small (90% to 93%).
- **The model sometimes repairs OCR damage.** gpt-oss-20b scores 93.2% on dates where the
  exact label date is found in only 90.6% of the OCR texts.
- **Model size did not matter on this task.** The 20b and 120b models are within a receipt
  or two of each other on every field.
- **Cost.** About 620 tokens in and 180 to 210 out per receipt, with a median model time
  under one second.

### Bugs the benchmark found in this project's own code

- A year followed directly by a clock time (`15/01/201911:05`) was not read as a date.
- A false start (`19-18/01` inside `REG#19-18/01/2018`) hid the real date after it.
- A date with an order number glued in front (`19-11/03/2018`) was read as 19 November 2003
  because mixed separators were accepted. This one made a correct extraction score as wrong.

Each has a test. Validation flags are recomputed when a report is built, so fixing a rule
re-scores saved runs without calling the model again.

### Not measured yet

- The remaining 244 receipts for both models.
- A stronger OCR engine or a vision model, which the ceiling row says is where the gain is.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-ocr.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pytest
```

Download the test split (191 MB) into `data/`:

```bash
curl -L -o data/sroie-test.parquet https://huggingface.co/datasets/jsdnrs/ICDAR2019-SROIE/resolve/main/data/test-00000-of-00001.parquet
```

Then:

```bash
.venv/Scripts/python -m tally.ocr                 # OCR the images (slow on CPU, resumable)
.venv/Scripts/python -m tally.run baseline        # rule-based, free
.venv/Scripts/python -m tally.run llm --limit 50  # needs a provider in .env (copy .env.example)
.venv/Scripts/python -m tally.demo 4              # one receipt, stage by stage
.venv/Scripts/python -m uvicorn tally.server:app --port 8001   # review UI
```

Any OpenAI-compatible endpoint works (Groq, Gemini, Ollama, OpenAI). The client paces itself
from rate-limit headers and stops cleanly when a daily quota runs out.

## Limitations

- One dataset, one language, one country's receipt formats.
- Dates are read day-first, which is right for this dataset and wrong for US receipts.
- The dataset's labels contain typos and truncations, so "near match" is reported separately
  and exact-string scores understate real accuracy.
- Line items are not extracted, so there is no arithmetic check that items add up to the total.

## Data and licence

The SROIE dataset is by Huang et al. (ICDAR 2019), used here from
[jsdnrs/ICDAR2019-SROIE](https://huggingface.co/datasets/jsdnrs/ICDAR2019-SROIE) under
CC BY 4.0. The dataset is not included in this repository. Reports in `results/` quote
short label values from it. The code is MIT licensed.
