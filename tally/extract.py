"""LLM extraction: receipt text in, four fields out, with the reply treated as untrusted.

The model's reply is parsed defensively. Anything that is not a JSON object with string
values becomes empty fields, which validation then flags for review. A bad reply never
crashes a batch run.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .data import FIELDS
from .llm import LLM

SYSTEM_PROMPT = """\
You extract four fields from the OCR text of a retail receipt. The text may contain OCR
mistakes. Reply with one JSON object and nothing else:

{"company": "...", "date": "...", "address": "...", "total": "..."}

Rules
- Copy values exactly as printed on the receipt. Do not correct spelling, reformat dates,
  expand abbreviations or add anything that is not there.
- company: the business that issued the receipt, as printed at the top. Not the customer,
  not the cashier, not a slogan.
- date: the receipt or invoice date as printed, without the time.
- address: the issuing business's full postal address, with its lines joined by ", ".
  Leave out phone numbers, registration numbers and email addresses.
- total: the final amount the customer owed, after tax, discounts and rounding. Digits and
  decimal point only, for example 43.20. Not the subtotal, not the cash handed over, not
  the change.
- If a field is not on the receipt, use an empty string. Never guess.
"""


@dataclass
class Extraction:
    fields: dict[str, str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    problems: list[str] = field(default_factory=list)  # why the reply could not be used as-is


def parse_reply(content: str) -> tuple[dict[str, str], list[str]]:
    """Fields from a model reply, plus a list of problems found while reading it."""
    empty = {f: "" for f in FIELDS}
    text = (content or "").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)  # JSON wrapped in prose or a code fence
        if not match:
            return empty, ["reply:not_json"]
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return empty, ["reply:not_json"]
    if not isinstance(data, dict):
        return empty, ["reply:not_an_object"]
    problems = []
    fields = {}
    for name in FIELDS:
        value = data.get(name, "")
        if value is None:
            value = ""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = f"{value:.2f}" if name == "total" else str(value)
        if not isinstance(value, str):
            problems.append(f"{name}:wrong_type")
            value = ""
        fields[name] = " ".join(value.split())
    return fields, problems


def extract(llm: LLM, receipt_text: str) -> Extraction:
    response = llm.complete(SYSTEM_PROMPT, receipt_text)
    fields, problems = parse_reply(response.content)
    return Extraction(fields=fields, prompt_tokens=response.prompt_tokens,
                      completion_tokens=response.completion_tokens,
                      latency_ms=response.latency_ms, problems=problems)
