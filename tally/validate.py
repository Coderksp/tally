"""Checks that need no answer key, used to decide which extractions a person should review.

Every check asks the same question: is this value supported by the receipt itself? A value
the receipt does not contain is the signature of a hallucination or a misread, and it can be
detected without knowing the right answer.

Flags are named `<field>:<problem>`. Any flag sends the document to review.
"""
from __future__ import annotations

import re

from .normalize import find_amounts, find_dates, parse_amount, parse_date, text_key, tokens

_TOTAL_WORD = re.compile(r"TOTAL|AMOUNT|AMT|NETT|DUE|PAYABLE", re.I)
_CASH_WORD = re.compile(r"CASH|TENDER|PAID|PAYMENT", re.I)
_CHANGE_WORD = re.compile(r"CHANGE|BALANCE|BAKI", re.I)
MIN_ADDRESS_SUPPORT = 0.85


def validate(extraction: dict[str, str], text: str) -> list[str]:
    flags: list[str] = []
    lines = text.splitlines()

    company = extraction.get("company", "")
    if not company.strip():
        flags.append("company:missing")
    elif text_key(company) not in text_key(text):
        flags.append("company:not_in_receipt")

    address = extraction.get("address", "")
    address_tokens = tokens(address)
    if not address_tokens:
        flags.append("address:missing")
    else:
        receipt_tokens = set(tokens(text))
        support = sum(t in receipt_tokens for t in address_tokens) / len(address_tokens)
        if support < MIN_ADDRESS_SUPPORT:
            flags.append("address:not_in_receipt")

    raw_date = extraction.get("date", "")
    parsed_date = parse_date(raw_date)
    if not raw_date.strip():
        flags.append("date:missing")
    elif parsed_date is None:
        flags.append("date:unparseable")
    elif parsed_date not in {d for _, d in find_dates(text)}:
        flags.append("date:not_in_receipt")

    raw_total = extraction.get("total", "")
    total = parse_amount(raw_total)
    if not raw_total.strip():
        flags.append("total:missing")
    elif total is None:
        flags.append("total:unparseable")
    else:
        holding = [line for line in lines if total in find_amounts(line)]
        if not holding:
            flags.append("total:not_in_receipt")
        else:
            if not any(_TOTAL_WORD.search(line) for line in holding):
                flags.append("total:no_total_label")
            # Paid 50.00 for a 43.20 bill: the model may return the cash handed over.
            change = [a for line in lines if _CHANGE_WORD.search(line) for a in find_amounts(line)]
            if (any(_CASH_WORD.search(line) for line in holding)
                    and not any(re.search(r"TOTAL", line, re.I) for line in holding)
                    and any(a > 0 for a in change)):
                flags.append("total:looks_like_cash_tendered")
    return flags
