from datetime import date
from decimal import Decimal

from tally import baseline
from tally.data import layout_text
from tally.normalize import find_amounts, find_dates, parse_amount, parse_date, text_key
from tally.score import aggregate, score_document, score_field
from tally.validate import validate

RECEIPT = """\
*** COPY ***
OJC MARKETING SDN BHD
ROC NO: 538358-H
NO 2 & 4, JALAN BAYU 4,
BANDAR SERI ALAM,
81750 MASAI, JOHOR
TEL:07-388 2218 FAX:07-388 8218
TAX INVOICE
DATE  : 15/01/2019 11:05:16 AM
KINGS SAFETY SHOES  1  43.20
SUBTOTAL:  40.75
TOTAL GST @6%:  2.45
TOTAL:  43.20
CASH  50.00
CHANGE  6.80
"""
GOOD = {"company": "OJC MARKETING SDN BHD", "date": "15/01/2019",
        "address": "NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, 81750 MASAI, JOHOR", "total": "43.20"}


# ---- normalize -----------------------------------------------------------------

def test_dates_in_every_printed_form_parse_to_the_same_day():
    for printed in ("15/01/2019", "15-01-2019", "15.01.2019", "15/01/19", "15 JAN 2019", "15-Jan-19",
                    "15JAN2019", "2019-01-15", "JAN 15, 2019", "15 January 2019"):
        assert parse_date(printed) == date(2019, 1, 15), printed


def test_impossible_and_missing_dates_are_none():
    assert parse_date("31/02/2019") is None
    assert parse_date("no date here") is None
    assert parse_date("") is None


def test_find_dates_keeps_reading_order_and_skips_times():
    found = find_dates("DATE: 02/03/2018 10:15:22  DUE 5 MAR 2018")
    assert [d for _, d in found] == [date(2018, 3, 2), date(2018, 3, 5)]


def test_amounts():
    assert parse_amount("RM 1,234.50") == Decimal("1234.50")
    assert parse_amount("$9.00") == parse_amount("9") == Decimal("9.00")
    assert parse_amount("-2.50") == Decimal("-2.50")
    assert parse_amount("") is None and parse_amount("12.345") is None and parse_amount("1.2.3") is None
    assert find_amounts("QTY 2  12.50  25.00  TEL 03-1234.5678") == [Decimal("12.50"), Decimal("25.00")]
    assert find_amounts("TOTAL 1,250.00") == [Decimal("1250.00")]


def test_text_key_ignores_case_spacing_and_punctuation():
    assert text_key("No.59, Jalan Permas 9/5") == text_key("NO 59 JALAN PERMAS 9 5")
    assert text_key("OJCMARKETINGSDNBHD") == text_key("OJC Marketing Sdn. Bhd.")


# ---- layout --------------------------------------------------------------------

def test_layout_joins_snippets_on_the_same_row_left_to_right():
    words = ["43.20", "TOTAL:", "OJC MARKETING", "CASH"]
    boxes = [[300, 100, 360, 118], [20, 101, 90, 119], [50, 10, 300, 30], [20, 130, 70, 148]]
    assert layout_text(words, boxes) == "OJC MARKETING\nTOTAL:  43.20\nCASH"


def test_layout_handles_empty_input():
    assert layout_text([], []) == ""
    assert layout_text(["  "], [[0, 0, 5, 5]]) == ""


# ---- baseline ------------------------------------------------------------------

def test_baseline_on_a_clean_receipt():
    out = baseline.extract(RECEIPT)
    assert out["company"] == "OJC MARKETING SDN BHD"
    assert out["date"] == "15/01/2019"
    assert out["total"] == "43.20"            # not the 50.00 cash line, not the subtotal
    assert text_key(out["address"]) == text_key(GOOD["address"])


def test_baseline_on_empty_text_returns_empty_fields():
    assert baseline.extract("") == {"company": "", "date": "", "address": "", "total": ""}


# ---- validation ----------------------------------------------------------------

def test_a_correct_extraction_raises_no_flags():
    assert validate(GOOD, RECEIPT) == []


def test_spacing_differences_from_ocr_do_not_raise_flags():
    squashed = dict(GOOD, company="OJCMARKETINGSDNBHD")
    assert validate(squashed, RECEIPT) == []


def test_values_the_receipt_does_not_contain_are_flagged():
    invented = {"company": "ACME TRADING", "date": "16/01/2019", "address": "1 Main Street, Springfield", "total": "99.99"}
    assert validate(invented, RECEIPT) == ["company:not_in_receipt", "address:not_in_receipt",
                                           "date:not_in_receipt", "total:not_in_receipt"]


def test_missing_and_malformed_values_are_flagged():
    flags = validate({"company": "", "date": "sometime", "address": "", "total": "forty"}, RECEIPT)
    assert flags == ["company:missing", "address:missing", "date:unparseable", "total:unparseable"]
    assert "total:missing" in validate(dict(GOOD, total=""), RECEIPT)


def test_cash_tendered_and_unlabelled_amounts_are_flagged():
    assert "total:looks_like_cash_tendered" in validate(dict(GOOD, total="50.00"), RECEIPT)
    assert validate(dict(GOOD, total="6.80"), RECEIPT) == ["total:no_total_label"]   # the change
    assert validate(dict(GOOD, total="40.75"), RECEIPT) == []   # subtotal: plausible, a known blind spot


def test_date_in_a_different_printed_form_is_still_grounded():
    assert validate(dict(GOOD, date="15 JAN 2019"), RECEIPT) == []


# ---- scoring -------------------------------------------------------------------

def test_score_levels():
    assert score_field("total", "RM 43.20", "43.20") == {"exact": False, "normalized": True, "near": True}
    assert score_field("total", "43.20", "43.20")["exact"] is True
    assert score_field("total", "43.00", "43.20") == {"exact": False, "normalized": False, "near": False}
    assert score_field("date", "15 JAN 2019", "15/01/2019")["normalized"] is True
    assert score_field("date", "16/01/2019", "15/01/2019")["normalized"] is False
    assert score_field("company", "ojc marketing sdn. bhd.", "OJC MARKETING SDN BHD")["normalized"] is True
    near = score_field("address", "NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, 81750 MASAI, JOHOR",
                       "NO 2 & 4, JALAN BAYU 4, BANDAR SERI ALAM, B1750 MASAI, JOHOR")
    assert near == {"exact": False, "normalized": False, "near": True}


def test_empty_prediction_never_matches_even_an_empty_looking_label():
    assert score_field("company", "", "OJC") == {"exact": False, "normalized": False, "near": False}
    assert score_field("total", "", "43.20")["normalized"] is False
    assert score_field("address", "", "---")["normalized"] is False


def test_aggregate():
    docs = [score_document(GOOD, GOOD), score_document(dict(GOOD, total="1.00"), GOOD)]
    summary = aggregate(docs)
    assert summary["n"] == 2
    assert summary["fields"]["total"]["normalized"] == 0.5 and summary["fields"]["date"]["exact"] == 1.0
    assert summary["all_fields"]["normalized"] == 0.5
    assert aggregate([]) == {"n": 0, "fields": {}, "all_fields": {}}


def test_dates_survive_ocr_gluing_the_time_onto_them():
    assert parse_date("15/01/201911:05:16AM") == date(2019, 1, 15)
    assert parse_date("15/01/1911:05") == date(2019, 1, 15)      # two-digit year, not the year 1911
    assert parse_date("DATE:15JAN201909:30") == date(2019, 1, 15)
    assert parse_date("2019-01-1509:30") == date(2019, 1, 15)
    assert parse_date("15/01/20195") is None                      # five digits: not a date


def test_a_false_start_does_not_hide_the_real_date_after_it():
    assert parse_date("ORD#90-REG#19-18/01/201817:09:21") == date(2018, 1, 18)
    assert [d for _, d in find_dates("REF 99/99/99 DATE 05/06/2018")] == [date(2018, 6, 5)]
