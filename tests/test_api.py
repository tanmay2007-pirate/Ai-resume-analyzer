"""Run:  pytest -q      (from the project root)"""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parent.parent / "samples"
JD = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")


def _post(filename, jd=JD, mime="application/octet-stream", data=None):
    data = data if data is not None else (SAMPLES / filename).read_bytes()
    return client.post("/api/analyze", files={"resume": (filename, data, mime)}, data={"job_description": jd})


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "Resume" in r.text


def test_pdf_analysis():
    r = _post("sample_resume.pdf")
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["score"] <= 100
    assert "Python" in body["skills"]["matched"]
    assert body["profile"]["email"] == "aarav.kulkarni@example.com"
    assert body["suggestions"]


def test_docx_analysis():
    r = _post("sample_resume.docx")
    assert r.status_code == 200
    assert r.json()["stats"]["file_type"] == "docx"


def test_missing_skills_detected():
    body = _post("sample_resume.pdf").json()
    assert "TypeScript" in body["skills"]["missing"]


def test_rejects_bad_type():
    r = _post("notes.txt", data=b"hello")
    assert r.status_code == 400


def test_rejects_short_jd():
    assert _post("sample_resume.pdf", jd="too short").status_code == 400


def test_rejects_corrupt_pdf():
    assert _post("broken.pdf", data=b"not a real pdf").status_code == 422


# ---- AI feedback path (mocked: no network, no real key needed) ----
import asyncio
import httpx
from app import llm


def _fake_client(status, payload=None):
    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, **kw):
            return httpx.Response(status, json=payload or {}, request=httpx.Request("POST", url))
    return FakeClient


def _run(monkeypatch, status, payload=None):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm.httpx, "AsyncClient", _fake_client(status, payload))
    result = {"score": 50, "skills": {"missing": ["Docker"]}}
    return asyncio.run(llm.ai_feedback(result, "resume text", "jd text"))


def test_ai_success(monkeypatch):
    ok = {"candidates": [{"content": {"parts": [{"text": "- Add Docker"}]}}]}
    assert _run(monkeypatch, 200, ok) == ("- Add Docker", None)


def test_ai_model_not_found(monkeypatch):
    text, err = _run(monkeypatch, 404)
    assert text is None and "GEMINI_MODEL" in err


def test_ai_bad_key(monkeypatch):
    assert "key" in _run(monkeypatch, 403)[1].lower()


def test_ai_off_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert asyncio.run(llm.ai_feedback({}, "", ""))[0] is None
