"""FastAPI entry point: serves the UI and the /api/analyze endpoint."""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from .analyzer import analyze  # noqa: E402
from .llm import ai_enabled, ai_feedback  # noqa: E402
from .parser import parse_resume  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"
MAX_BYTES = 5 * 1024 * 1024

app = FastAPI(title="AI Resume Analyzer", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_feedback_available": ai_enabled()}


@app.post("/api/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    use_ai: bool = Form(False),
):
    name = resume.filename or ""
    if not name.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Please upload a PDF or DOCX resume.")
    data = await resume.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB. Please upload a smaller resume.")
    if len(job_description.strip()) < 40:
        raise HTTPException(400, "Paste a fuller job description (at least a couple of sentences).")

    try:
        parsed = parse_resume(name, data)
    except Exception:
        raise HTTPException(422, "We could not read this file. Make sure it is a valid, unprotected PDF or DOCX.")
    if len(parsed.text.split()) < 30:
        raise HTTPException(
            422,
            "Almost no text was found. If your PDF is a scanned image, export it as a text-based PDF or DOCX.",
        )

    result = analyze(parsed, job_description)
    result["ai_feedback"], result["ai_error"] = None, None
    if use_ai:
        result["ai_feedback"], result["ai_error"] = await ai_feedback(result, parsed.text, job_description)
    return JSONResponse(result)
