import json

from fastapi.testclient import TestClient

from tally.data import Receipt
from tally.llm import ScriptedLLM
from tally.server import BASELINE, create_app

TEXT = "ACME TRADING\n1 HIGH ST, PENANG\nDATE 02/03/2018\nTOTAL  12.50\nCASH  20.00\nCHANGE  7.50"
TRUTH = {"company": "ACME TRADING", "date": "02/03/2018", "address": "1 HIGH ST, PENANG", "total": "12.50"}


def client(tmp_path, replies=()) -> TestClient:
    receipts = [Receipt(key=f"R{i}", text=TEXT, truth=TRUTH) for i in range(3)]
    images = tmp_path / "images"
    images.mkdir()
    (images / "R0.jpg").write_bytes(b"\xff\xd8fake")
    return TestClient(create_app(parquet=tmp_path / "none.parquet", ocr_path=tmp_path / "ocr.jsonl",
                                 runs_dir=tmp_path / "runs", image_dir=images,
                                 reviews_path=tmp_path / "reviews.json", receipts=receipts,
                                 llm=ScriptedLLM(list(replies))))


def test_page_and_baseline_run_are_served(tmp_path):
    c = client(tmp_path)
    assert "Tally" in c.get("/").text
    assert c.get("/api/runs").json() == [{"label": BASELINE, "receipts": 3}]
    rows = c.get("/api/receipts").json()
    assert [r["key"] for r in rows] == ["R0", "R1", "R2"] and rows[0]["status"] == "auto" and rows[0]["correct"] is True
    summary = c.get("/api/summary").json()
    assert summary["n"] == 3 and summary["overall"]["fields"]["total"]["normalized"] == 1.0
    assert c.get("/api/receipts?run=nope").status_code == 404


def test_receipt_detail_and_image(tmp_path):
    c = client(tmp_path)
    detail = c.get("/api/receipts/R0").json()
    assert detail["truth"] == TRUTH and detail["runs"][BASELINE]["scores"]["total"]["normalized"] is True
    assert detail["review"] is None
    assert c.get("/api/receipts/R0/image").content.startswith(b"\xff\xd8")
    assert c.get("/api/receipts/R9").status_code == 404
    assert c.get("/api/receipts/R9/image").status_code == 404


def test_live_extraction_is_scored_flagged_and_added_to_the_run(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "test/model")
    monkeypatch.setenv("LLM_BASE_URL", "http://test")
    wrong = json.dumps(dict(TRUTH, total="20.00"))
    c = client(tmp_path, replies=[wrong, json.dumps(TRUTH)])
    out = c.post("/api/receipts/R1/extract").json()
    assert out["run"] == "test_model" and out["scores"]["total"]["normalized"] is False
    assert "total:looks_like_cash_tendered" in out["flags"]
    labels = [r["label"] for r in c.get("/api/runs").json()]
    assert labels == [BASELINE, "test_model"]
    row = next(r for r in c.get("/api/receipts?run=test_model").json() if r["key"] == "R1")
    assert row["status"] == "review" and row["correct"] is False
    c.post("/api/receipts/R1/extract")  # a second call does not overwrite the saved result
    assert len((tmp_path / "runs" / "test_model.jsonl").read_text().splitlines()) == 1


def test_provider_failure_is_a_502(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "test/model")
    monkeypatch.setenv("LLM_BASE_URL", "http://test")
    assert client(tmp_path).post("/api/receipts/R0/extract").status_code == 502


def test_review_is_saved_and_returned(tmp_path):
    c = client(tmp_path)
    saved = c.post("/api/receipts/R2/review", json={"fields": {"company": "  ACME   TRADING ", "total": "12.50", "extra": "x"}}).json()
    assert saved["fields"] == {"company": "ACME TRADING", "date": "", "address": "", "total": "12.50"}
    assert c.get("/api/receipts/R2").json()["review"]["fields"]["company"] == "ACME TRADING"
    assert next(r for r in c.get("/api/receipts").json() if r["key"] == "R2")["reviewed"] is True
    assert c.post("/api/receipts/R9/review", json={"fields": {}}).status_code == 404
