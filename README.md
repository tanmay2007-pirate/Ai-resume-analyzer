# Resume Lens - AI Resume Analyzer

Upload a resume (PDF or DOCX) and paste a job description. Get an ATS match score, matched and
missing skills, formatting problems and a ranked list of fixes. Optional Gemini-written tips.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

## Test
```bash
pip install -r requirements-dev.txt
python samples/make_samples.py   # only if samples/ is empty
pytest -q
```

## Deploy on Render
Build command: `pip install -r requirements.txt`
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
Health check path: `/api/health`
Python is pinned to 3.13 by `.python-version`. Optional env vars: `GEMINI_API_KEY`, `GEMINI_MODEL`.
See the Word guide for the full step-by-step.
