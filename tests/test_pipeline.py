import json

import httpx
import pytest

from tally.data import Receipt
from tally.extract import extract, parse_reply
from tally.llm import LLMError, OpenAICompatLLM, QuotaExhausted, ScriptedLLM
from tally.run import build_report, load_run, run_llm

TEXT = "ACME TRADING\n1 HIGH ST, PENANG\nDATE 02/03/2018\nTOTAL  12.50\nCASH  20.00\nCHANGE  7.50"
TRUTH = {"company": "ACME TRADING", "date": "02/03/2018", "address": "1 HIGH ST, PENANG", "total": "12.50"}
REPLY = json.dumps(TRUTH)


def receipts(n: int) -> list[Receipt]:
    return [Receipt(key=f"R{i}", text=TEXT, truth=TRUTH) for i in range(n)]


# ---- reading the model's reply ---------------------------------------------------

def test_parse_clean_json():
    assert parse_reply(REPLY) == (TRUTH, [])


def test_parse_json_wrapped_in_prose_or_a_code_fence():
    fields, problems = parse_reply("Here you go:\n```json\n" + REPLY + "\n```")
    assert fields == TRUTH and problems == []


def test_parse_numbers_nulls_and_missing_keys():
    fields, problems = parse_reply('{"company": "ACME", "date": null, "total": 12.5}')
    assert fields == {"company": "ACME", "date": "", "address": "", "total": "12.50"} and problems == []


def test_parse_garbage_gives_empty_fields_and_a_problem_not_an_exception():
    empty = {"company": "", "date": "", "address": "", "total": ""}
    assert parse_reply("I could not read this receipt.") == (empty, ["reply:not_json"])
    assert parse_reply("") == (empty, ["reply:not_json"])
    assert parse_reply("[1, 2]") == (empty, ["reply:not_an_object"])
    assert parse_reply("{broken") == (empty, ["reply:not_json"])
    fields, problems = parse_reply('{"company": ["A", "B"], "total": true}')
    assert fields["company"] == "" and fields["total"] == "" and problems == ["company:wrong_type", "total:wrong_type"]


def test_extract_sends_the_receipt_text_and_records_usage():
    llm = ScriptedLLM([REPLY])
    result = extract(llm, TEXT)
    assert result.fields == TRUTH and result.prompt_tokens == 100
    assert llm.calls[0][1] == TEXT and "JSON" in llm.calls[0][0]


# ---- batch runs ------------------------------------------------------------------

def test_run_saves_each_result_and_resumes_without_repeating(tmp_path):
    path = tmp_path / "run.jsonl"
    first = ScriptedLLM([REPLY, REPLY, QuotaExhausted("daily limit")])
    outcome = run_llm(receipts(5), path, first, log=lambda m: None)
    assert outcome.startswith("quota exhausted after 2") and set(load_run(path)) == {"R0", "R1"}

    second = ScriptedLLM([REPLY, REPLY, REPLY])
    assert run_llm(receipts(5), path, second, log=lambda m: None) == "complete"
    assert len(second.calls) == 3 and set(load_run(path)) == {"R0", "R1", "R2", "R3", "R4"}


def test_a_failed_receipt_is_skipped_and_retried_next_time(tmp_path):
    path = tmp_path / "run.jsonl"
    assert run_llm(receipts(3), path, ScriptedLLM([REPLY, LLMError("timeout"), REPLY]), log=lambda m: None) == "complete"
    assert set(load_run(path)) == {"R0", "R2"}
    run_llm(receipts(3), path, ScriptedLLM([REPLY]), log=lambda m: None)
    assert set(load_run(path)) == {"R0", "R1", "R2"}


def test_run_stops_after_repeated_provider_errors(tmp_path):
    llm = ScriptedLLM([LLMError("down")] * 10)
    outcome = run_llm(receipts(8), tmp_path / "run.jsonl", llm, log=lambda m: None)
    assert "errors in a row" in outcome and len(llm.calls) == 3


def test_unreadable_reply_is_saved_flagged_for_review(tmp_path):
    path = tmp_path / "run.jsonl"
    run_llm(receipts(1), path, ScriptedLLM(["sorry, no idea"]), log=lambda m: None)
    record = load_run(path)["R0"]
    assert record["fields"]["total"] == "" and "reply:not_json" in record["flags"] and "total:missing" in record["flags"]


# ---- report ----------------------------------------------------------------------

def test_report_separates_auto_accepted_from_review():
    rs = receipts(4)
    wrong_cash = dict(TRUTH, total="20.00")     # flagged: cash tendered
    invented = dict(TRUTH, date="09/09/2018")   # flagged: not in receipt
    records = {
        "R0": {"key": "R0", "fields": TRUTH, "flags": [], "prompt_tokens": 100, "completion_tokens": 20, "latency_ms": 500},
        "R1": {"key": "R1", "fields": TRUTH, "flags": [], "prompt_tokens": 100, "completion_tokens": 20, "latency_ms": 700},
        "R2": {"key": "R2", "fields": wrong_cash, "flags": ["total:looks_like_cash_tendered"]},
        "R3": {"key": "R3", "fields": invented, "flags": ["date:not_in_receipt"]},
    }
    report, summary = build_report("test", records, rs, price_in=1.0, price_out=2.0)
    assert summary["n"] == 4 and summary["overall"]["fields"]["total"]["normalized"] == 0.75
    routing = summary["routing"]["date and total"]
    assert routing == {"auto_n": 2, "review_n": 2, "auto_accuracy": 1.0, "review_accuracy": 0.0,
                       "errors": 2, "errors_caught": 2}
    assert summary["cost_per_receipt"] == pytest.approx(100 / 1e6 * 1.0 + 20 / 1e6 * 2.0)
    assert "review caught 2 (100.0%)" in report and "| R2 | 20.00 | 12.50 |" in report


def test_report_scores_only_receipts_that_have_been_run():
    report, summary = build_report("partial", {"R0": {"key": "R0", "fields": TRUTH, "flags": []}}, receipts(3))
    assert summary["n"] == 1 and "1 receipts scored (of 3" in report


# ---- HTTP client -----------------------------------------------------------------

def _client(handler, **kwargs) -> OpenAICompatLLM:
    return OpenAICompatLLM("http://test/v1", "key", "m", max_retries=2, sleep=lambda s: None,
                           client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def test_client_requests_json_and_passes_extra_options():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"} and body["reasoning_effort"] == "low"
        assert [m["role"] for m in body["messages"]] == ["system", "user"]
        return httpx.Response(200, json={"choices": [{"message": {"content": REPLY}}],
                                         "usage": {"prompt_tokens": 7, "completion_tokens": 3}})
    response = _client(handler, extra={"reasoning_effort": "low"}).complete("sys", "user")
    assert response.content == REPLY and (response.prompt_tokens, response.completion_tokens) == (7, 3)


def test_client_separates_a_daily_quota_from_an_ordinary_failure():
    with pytest.raises(QuotaExhausted):
        _client(lambda r: httpx.Response(429, text="tokens per day", headers={"retry-after": "3600"})).complete("s", "u")
    with pytest.raises(LLMError) as info:
        _client(lambda r: httpx.Response(401, text="bad key in org_abcdef123456")).complete("s", "u")
    assert not isinstance(info.value, QuotaExhausted) and "org_[redacted]" in str(info.value)


def test_saved_runs_are_rescored_with_current_validation_rules():
    from tally.run import current_flags
    receipt = receipts(1)[0]
    stale = {"key": "R0", "fields": TRUTH, "flags": ["date:not_in_receipt", "reply:not_json"]}
    assert current_flags(stale, receipt) == ["reply:not_json"]     # stale validation flag dropped, reply problem kept
    _, summary = build_report("t", {"R0": stale}, [receipt])
    assert summary["routing"]["date and total"]["review_n"] == 1
