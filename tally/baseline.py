"""A rule-based extractor: no model, no cost.

It exists to answer "is the LLM worth paying for?". Every LLM number in the report is
shown next to this one.
"""
from __future__ import annotations

import re

from .normalize import find_amounts, find_dates

_COMPANY_HINT = re.compile(
    r"\b(SDN\.? ?BHD|BHD|ENTERPRISE|TRADING|RESTAURANT|RESTORAN|MARKETING|HARDWARE|STORE|"
    r"MART|CAFE|KEDAI|PERNIAGAAN|HOLDINGS|PHARMACY|BOOK|BAKERY|S/B|S\.B\.)\b", re.I)
_NOT_COMPANY = re.compile(r"COPY|INVOICE|RECEIPT|TEL|FAX|GST|REG|WWW|@|\d{5,}", re.I)
_ADDRESS_STOP = re.compile(
    r"TEL|FAX|GST|INVOICE|RECEIPT|CASHIER|DATE|EMAIL|WWW|@|REG|ROC|CO\.? ?NO|BILL|TAX|\(\d{5,}", re.I)
_TOTAL_LINE = re.compile(r"TOTAL|AMOUNT DUE|NET AMT|NETT", re.I)
_NOT_TOTAL_LINE = re.compile(
    r"SUB ?-?TOTAL|TOTAL ?(QTY|ITEM|DISC|GST|TAX|SAV|QUANTITY)|CASH|CHANGE|TENDER|EXCL", re.I)


def extract(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    company_index = _company_index(lines)
    return {
        "company": lines[company_index] if company_index is not None else "",
        "date": _date(text),
        "address": _address(lines, company_index),
        "total": _total(lines),
    }


def _company_index(lines: list[str]) -> int | None:
    head = lines[:8]
    for i, line in enumerate(head):
        if _COMPANY_HINT.search(line) and not _NOT_COMPANY.search(line):
            return i
    for i, line in enumerate(head):
        if len(re.findall(r"[A-Za-z]{2,}", line)) >= 2 and not _NOT_COMPANY.search(line):
            return i
    return 0 if lines else None


def _date(text: str) -> str:
    dates = find_dates(text)
    return dates[0][0] if dates else ""


def _address(lines: list[str], company_index: int | None) -> str:
    if company_index is None:
        return ""
    parts: list[str] = []
    for line in lines[company_index + 1: company_index + 7]:
        if _ADDRESS_STOP.search(line):
            if parts:
                break
            continue  # registration number between name and address: skip it
        parts.append(line.replace("  ", " ").strip(" ,"))
        if len(parts) == 4:
            break
    return ", ".join(parts)


def _total(lines: list[str]) -> str:
    on_total_lines = [a for line in lines
                      if _TOTAL_LINE.search(line) and not _NOT_TOTAL_LINE.search(line)
                      for a in find_amounts(line)]
    if on_total_lines:
        return f"{max(on_total_lines):.2f}"
    others = [a for line in lines if not _NOT_TOTAL_LINE.search(line) for a in find_amounts(line)]
    return f"{max(others):.2f}" if others else ""
