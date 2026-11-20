"""Optional Gemini feedback. Disabled unless GEMINI_API_KEY is set. Never raises.

Returns (text, error). Exactly one of them is not None when a key is configured.
"""
import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def ai_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


async def ai_feedback(result: dict, resume_text: str, jd: str):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None, "AI tips are not configured on this server."
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    prompt = (
        "You are an expert technical recruiter and ATS specialist coaching a student.\n"
        f"ATS score: {result['score']}/100. Missing skills: {', '.join(result['skills']['missing']) or 'none'}.\n"
        "Write 4 short, specific, encouraging improvement tips for this resume against the job description. "
        "Do not invent experience the candidate does not have. Use plain text bullets starting with '- '.\n\n"
        f"JOB DESCRIPTION:\n{jd[:3000]}\n\nRESUME:\n{resume_text[:5000]}"
    )
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(
                GEMINI_URL.format(model=model),
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        if r.status_code == 404:
            return None, f"AI model '{model}' was not found. Set GEMINI_MODEL to a current model name."
        if r.status_code in (400, 401, 403):
            return None, "The Gemini API key was rejected. Check GEMINI_API_KEY."
        if r.status_code == 429:
            return None, "Gemini free-tier limit reached. Try again in a minute."
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip(), None
    except Exception:
        return None, "AI tips are unavailable right now. Your score and fixes above are unaffected."
