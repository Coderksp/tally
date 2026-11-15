"""Turn printed values into comparable ones: amounts to Decimal, dates to date, text to a key.

Receipts print the same fact many ways ("RM 9.00", "$9.00", "9.00"; "15/01/2019",
"15 JAN 19"). Scoring and validation compare the parsed value, not the string.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
_MON = r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*"

# Each pattern yields (day, month, year) group names. Receipts in this dataset are day-first.
# OCR often drops the space between a date and the time after it ("15/01/201911:05"), so a
# year may be followed directly by a clock time. Four-digit years are limited to 1980-2099
# so that "15/01/1911:05" reads as 15/01/19 at 11:05, not as the year 1911.
_YEAR = r"(?P<y>(?:19[89]|20\d)\d|\d{2})"
_END = r"(?=\D|$|\d{1,2}[:.]\d{2})"
_DATE_PATTERNS = [
    re.compile(r"(?<!\d)(?P<y>(?:19[89]|20\d)\d)[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{2}|\d)" + _END),
    re.compile(r"(?<!\d)(?P<d>\d{1,2})[-/.](?P<m>\d{1,2})[-/.]" + _YEAR + _END),
    re.compile(r"(?<!\d)(?P<d>\d{1,2})[-/. ]?(?P<mon>" + _MON + r")[-/., ]{0,2}" + _YEAR + _END, re.I),
    re.compile(r"(?P<mon>" + _MON + r")[-/. ]?(?P<d>\d{1,2}),?[-/. ]?(?P<y>(?:19[89]|20\d)\d)" + _END, re.I),
]
_AMOUNT = re.compile(r"(?<![\d.])-?\d{1,3}(?:,\d{3})+\.\d{2}(?!\d)|(?<![\d.,])-?\d+\.\d{2}(?!\d)")


def _build_date(match: re.Match) -> date | None:
    groups = match.groupdict()
    year = int(groups["y"])
    if year < 100:
        year += 2000
    month = MONTHS[groups["mon"][:3].upper()] if groups.get("mon") else int(groups["m"])
    try:
        return date(year, month, int(groups["d"]))
    except ValueError:
        return None


def find_dates(text: str) -> list[tuple[str, date]]:
    """All dates printed in the text, in reading order, as (printed form, parsed date)."""
    found: list[tuple[int, str, date]] = []
    taken: list[tuple[int, int]] = []
    text = text or ""
    for pattern in _DATE_PATTERNS:
        position = 0
        while match := pattern.search(text, position):
            claimed = any(match.start() < end and start < match.end() for start, end in taken)
            parsed = None if claimed else _build_date(match)
            if parsed:
                found.append((match.start(), match.group(0), parsed))
                taken.append(match.span())
                position = match.end()
            else:
                # Not a real date ("19-18/01" inside "REG#19-18/01/2018"). Retry one character
                # later instead of skipping the whole span, or the real date inside it is lost.
                position = match.start() + 1
    return [(raw, parsed) for _, raw, parsed in sorted(found)]


def parse_date(text: str) -> date | None:
    dates = find_dates(text)
    return dates[0][1] if dates else None


def find_amounts(text: str) -> list[Decimal]:
    """All money-shaped numbers (two decimals) in the text, in reading order."""
    return [Decimal(m.group(0).replace(",", "")) for m in _AMOUNT.finditer(text or "")]


def parse_amount(text: str) -> Decimal | None:
    """A single amount from a printed value such as 'RM 1,234.50', '$9.00' or '9'."""
    cleaned = re.sub(r"[^\d.,-]", "", text or "").replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d{1,2})?", cleaned):
        return None
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def text_key(text: str) -> str:
    """Case, spacing and punctuation removed: 'No.59, Jalan' and 'NO 59 JALAN' compare equal."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Z0-9]+", (text or "").upper())
