"""Core NLP pipeline: extraction -> matching -> scoring -> feedback."""
import re
from collections import Counter
from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skills import ACTION_VERBS, SKILLS, STOPWORDS

# --------------------------------------------------------------------------- #
# Section detection
# --------------------------------------------------------------------------- #
SECTION_HEADINGS = {
    "summary": r"(professional\s+)?(summary|profile|objective|about\s+me|career\s+objective)",
    "education": r"(education|academic(s| background| qualifications?)?|qualifications?)",
    "skills": r"((technical|core|key)\s+)?skills?(\s+(&|and)\s+tools)?|technologies|tech\s+stack|competencies",
    "experience": r"((work|professional|relevant)\s+)?experience|employment(\s+history)?|internships?|work\s+history",
    "projects": r"(academic\s+|personal\s+|key\s+)?projects?",
    "certifications": r"certifications?|certificates?|licenses?|courses?(\s+and\s+certifications?)?",
    "achievements": r"achievements?|awards?(\s+(&|and)\s+honou?rs)?|honou?rs|accomplishments?",
}
HEADING_RES = {k: re.compile(rf"^\W*({v})\W*:?\s*$", re.I) for k, v in SECTION_HEADINGS.items()}


def split_sections(text: str) -> dict:
    sections, current = {"header": []}, "header"
    for line in text.splitlines():
        stripped = line.strip()
        matched = None
        if 0 < len(stripped) <= 40:
            for name, rx in HEADING_RES.items():
                if rx.match(stripped):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(stripped)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip() or k != "header"}


# --------------------------------------------------------------------------- #
# Skill extraction
# --------------------------------------------------------------------------- #
def _alias_pattern(alias: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.I)


_SKILL_PATTERNS = {
    canonical: [_alias_pattern(a) for a in aliases] for canonical, aliases in SKILLS.items()
}


def extract_skills(text: str) -> list:
    found = []
    for canonical, patterns in _SKILL_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            found.append(canonical)
    return found


# --------------------------------------------------------------------------- #
# Contact / entity extraction
# --------------------------------------------------------------------------- #
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[\w\-/%]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.I)
DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|b\.?\s?sc|b\.?\s?c\.?a|bachelor[’' ]?s?|m\.?\s?tech|m\.?\s?e\.?|m\.?\s?sc|"
    r"m\.?\s?c\.?a|master[’' ]?s?|mba|ph\.?\s?d|diploma|hsc|ssc|12th|10th|b\.?\s?com|b\.?\s?a\.?)\b",
    re.I,
)
CERT_HINT_RE = re.compile(r"certif|certificate|coursera|udemy|nptel|google\s+cloud|aws\s+certified|hackerrank", re.I)
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_RANGE_RE = re.compile(
    rf"((?:{MONTHS})[a-z]*\.?\s+)?((?:19|20)\d{{2}})\s*(?:-|–|—|to)\s*"
    rf"(present|current|now|((?:{MONTHS})[a-z]*\.?\s+)?((?:19|20)\d{{2}}))",
    re.I,
)
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS.split("|")[:12])}


def _month(m):
    if not m:
        return 6
    return MONTH_NUM.get(m.strip().lower()[:3], 6)


def estimate_experience_years(text: str) -> float:
    total_months = 0
    today = date.today()
    for m in DATE_RANGE_RE.finditer(text):
        sm, sy, end_raw, em, ey = m.group(1), int(m.group(2)), m.group(3), m.group(4), m.group(5)
        start = sy * 12 + _month(sm)
        if end_raw.lower() in ("present", "current", "now"):
            end = today.year * 12 + today.month
        else:
            end = int(ey) * 12 + _month(em)
        if 0 < end - start <= 12 * 20:
            total_months += end - start
    return round(total_months / 12, 1)


def extract_name(header_text: str):
    for line in header_text.splitlines()[:6]:
        line = line.strip()
        if not line or EMAIL_RE.search(line) or re.search(r"\d", line) or "http" in line.lower():
            continue
        words = line.replace(",", " ").split()
        if 1 < len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'\-]+", w) for w in words):
            return " ".join(w.capitalize() if w.isupper() else w for w in words)
    return None


def extract_phone(text: str):
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 10 <= len(digits) <= 13 and not re.fullmatch(r"(19|20)\d{2}(19|20)\d{2}", digits):
            return m.group().strip()
    return None


def extract_entities(text: str, sections: dict) -> dict:
    header = sections.get("header", "") or text[:300]
    email = EMAIL_RE.search(text)
    edu_text = sections.get("education", "")
    education = []
    for line in edu_text.splitlines():
        if DEGREE_RE.search(line) or re.search(r"university|college|institute|school|academy", line, re.I):
            education.append(line.strip())
    if not education:
        education = [l.strip() for l in text.splitlines() if DEGREE_RE.search(l)][:3]

    certs = [l.lstrip("•-* ").strip() for l in sections.get("certifications", "").splitlines() if l.strip()]
    if not certs:
        certs = [l.lstrip("•-* ").strip() for l in text.splitlines() if CERT_HINT_RE.search(l)][:4]

    exp_lines = [
        l.lstrip("•-* ").strip()
        for l in sections.get("experience", "").splitlines()
        if DATE_RANGE_RE.search(l) or (l.strip() and not l.strip().startswith(("•", "-", "*")) and len(l) < 90)
    ][:6]

    return {
        "name": extract_name(header),
        "email": email.group() if email else None,
        "phone": extract_phone(text),
        "linkedin": (LINKEDIN_RE.search(text) or [None])[0] if LINKEDIN_RE.search(text) else None,
        "github": (GITHUB_RE.search(text) or [None])[0] if GITHUB_RE.search(text) else None,
        "education": education[:5],
        "certifications": certs[:6],
        "experience": exp_lines,
        # Only dated ranges outside the Education section count as experience
        "experience_years": estimate_experience_years(
            "\n".join(v for k, v in sections.items() if k in ("experience", "projects"))
        ),
    }


# --------------------------------------------------------------------------- #
# Job description processing
# --------------------------------------------------------------------------- #
def jd_required_years(jd: str):
    m = re.search(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", jd, re.I)
    return int(m.group(1)) if m else None


def jd_keywords(jd: str, skip: set, limit: int = 15) -> list:
    tokens = [t.lower().strip(".-") for t in re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", jd)]
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    counts = Counter(tokens)
    bigrams = Counter(
        f"{a} {b}" for a, b in zip(tokens, tokens[1:]) if a != b
    )
    for bg, c in bigrams.items():
        if c >= 2:
            counts[bg] = c + 1
    skip_lower = {s.lower() for s in skip}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    out = []
    for term, _ in ranked:
        if term in skip_lower or any(term == p for p in out):
            continue
        if any(term in o.split() for o in out):  # drop a word already covered by a bigram
            continue
        out.append(term)
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
WEIGHTS = {
    "skills": 40,
    "similarity": 20,
    "sections": 15,
    "formatting": 15,
    "fit": 10,
}


def tfidf_similarity(resume: str, jd: str) -> float:
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        matrix = vec.fit_transform([resume, jd])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except ValueError:
        return 0.0


def formatting_checks(text: str, sections: dict, entities: dict, parsed) -> tuple:
    """Return (score 0-100, list of findings)."""
    issues, score = [], 100
    words = len(text.split())
    layout = parsed.layout

    def flag(sev, title, detail, penalty):
        nonlocal score
        issues.append({"severity": sev, "title": title, "detail": detail})
        score -= penalty

    if words < 150:
        flag("high", "Resume is very short", f"Only {words} words were detected. Add detail about projects, tools and results.", 20)
    elif words > 1100:
        flag("medium", "Resume is very long", f"{words} words detected. Keep it focused, ideally one page for students.", 10)
    if not entities["email"]:
        flag("high", "No email address found", "Add a professional email in the header so recruiters and ATS can reach you.", 15)
    if not entities["phone"]:
        flag("medium", "No phone number found", "Add a phone number in the header.", 8)
    if layout.get("tables", 0) > 0:
        flag("high", "Tables detected", "Many ATS parsers read tables out of order or skip them. Use plain paragraphs and bullets.", 15)
    if layout.get("multi_column"):
        flag("high", "Multi-column layout detected", "Two-column layouts can scramble reading order in ATS. Use a single column.", 15)
    if layout.get("images", 0) > 0:
        flag("medium", "Images or graphics detected", "Photos, icons and skill-bar graphics are ignored by ATS. Replace them with text.", 8)
    if layout.get("header_footer_text"):
        flag("medium", "Text inside header/footer", "Some ATS ignore headers and footers. Keep contact details in the main body.", 6)
    if parsed.pages > 2:
        flag("low", "More than two pages", "Keep the resume to one or two pages.", 5)

    bullets = [l for l in text.splitlines() if l.strip().startswith(("•", "-", "*", "▪", "●", "◦"))]
    if len(bullets) < 4:
        flag("medium", "Few bullet points", "Use bullet points for project and experience details so they scan easily.", 8)
    starts = [re.sub(r"^\W+", "", b).split(" ")[0].lower() for b in bullets if b.strip()]
    verb_ratio = (sum(1 for s in starts if s in ACTION_VERBS) / len(starts)) if starts else 0
    if bullets and verb_ratio < 0.4:
        flag("medium", "Weak action verbs", "Start bullets with verbs such as Built, Developed, Optimized or Led.", 6)
    numbers = sum(1 for b in bullets if re.search(r"\d+\s*(%|x|\+|k|ms|users|hours|days)?", b))
    if bullets and numbers < 3:
        flag("medium", "Few measurable results", "Add numbers where you can, such as users, speed-ups, accuracy or time saved.", 6)
    return max(0, score), issues


def section_score(sections: dict, entities: dict) -> tuple:
    checks = {
        "Contact details": (bool(entities["email"]) + bool(entities["phone"])) / 2,
        "Education": 1.0 if "education" in sections else 0.0,
        "Skills": 1.0 if "skills" in sections else 0.0,
        "Experience or projects": 1.0 if ("experience" in sections or "projects" in sections) else 0.0,
        "Summary": 1.0 if "summary" in sections else 0.0,
        "Certifications or achievements": 1.0 if ("certifications" in sections or "achievements" in sections) else 0.0,
    }
    weights = {"Contact details": 25, "Education": 20, "Skills": 25, "Experience or projects": 20,
               "Summary": 5, "Certifications or achievements": 5}
    score = sum(checks[k] * weights[k] for k in checks)
    return round(score), checks


def analyze(parsed, job_description: str) -> dict:
    text, jd = parsed.text, job_description.strip()
    sections = split_sections(text)
    entities = extract_entities(text, sections)

    resume_skills = extract_skills(text)
    jd_skills = extract_skills(jd)
    matched = [s for s in jd_skills if s in resume_skills]
    missing = [s for s in jd_skills if s not in resume_skills]
    extra = [s for s in resume_skills if s not in jd_skills]

    skip_terms = set(jd_skills) | {a for s in jd_skills for a in SKILLS[s]}
    skip_terms |= {w for s in skip_terms for w in re.findall(r"[a-z]{3,}", s.lower())}  # parts of skill phrases
    kw = jd_keywords(jd, skip=skip_terms)
    text_l = text.lower()
    kw_present = [k for k in kw if k in text_l]
    kw_missing = [k for k in kw if k not in text_l]

    skills_pct = (len(matched) / len(jd_skills) * 100) if jd_skills else min(100, len(resume_skills) * 8)
    sim = tfidf_similarity(text, jd)
    sim_pct = min(100, sim * 100 * 2.2)  # raw cosine is low for long vs short text; rescale
    sec_pct, sec_checks = section_score(sections, entities)
    fmt_pct, fmt_issues = formatting_checks(text, sections, entities, parsed)

    req_years = jd_required_years(jd)
    exp_years = entities["experience_years"]
    exp_fit = 100 if not req_years else min(100, (exp_years / req_years) * 100 if req_years else 100)
    edu_fit = 100 if entities["education"] else 40
    fit_pct = round(exp_fit * 0.5 + edu_fit * 0.5)

    parts = {"skills": skills_pct, "similarity": sim_pct, "sections": sec_pct, "formatting": fmt_pct, "fit": fit_pct}
    total = round(sum(parts[k] * WEIGHTS[k] / 100 for k in parts))

    breakdown = [
        {"key": "skills", "label": "Skills match", "score": round(skills_pct), "weight": WEIGHTS["skills"]},
        {"key": "similarity", "label": "Keyword similarity", "score": round(sim_pct), "weight": WEIGHTS["similarity"]},
        {"key": "sections", "label": "Section completeness", "score": round(sec_pct), "weight": WEIGHTS["sections"]},
        {"key": "formatting", "label": "ATS-safe formatting", "score": round(fmt_pct), "weight": WEIGHTS["formatting"]},
        {"key": "fit", "label": "Experience and education fit", "score": round(fit_pct), "weight": WEIGHTS["fit"]},
    ]

    verdict = (
        "Strong match" if total >= 80 else "Good match" if total >= 65 else
        "Needs work" if total >= 45 else "Low match"
    )

    suggestions = build_suggestions(missing, kw_missing, fmt_issues, sec_checks, req_years, exp_years, matched, jd_skills)

    return {
        "score": total,
        "verdict": verdict,
        "breakdown": breakdown,
        "skills": {"matched": matched, "missing": missing, "extra": extra[:15],
                   "jd_total": len(jd_skills), "resume_total": len(resume_skills)},
        "keywords": {"present": kw_present, "missing": kw_missing},
        "sections": {"found": [k for k in sections if k != "header"], "checks": sec_checks},
        "formatting": fmt_issues,
        "profile": entities,
        "stats": {"words": len(text.split()), "pages": parsed.pages, "file_type": parsed.file_type,
                  "similarity": round(sim, 3), "required_years": req_years},
        "suggestions": suggestions,
    }


def build_suggestions(missing, kw_missing, fmt_issues, sec_checks, req_years, exp_years, matched, jd_skills):
    out = []
    if missing:
        top = ", ".join(missing[:6])
        out.append({"severity": "high", "title": f"Add the missing skills: {top}",
                    "detail": "These appear in the job description but not in your resume. Add the ones you truly have to your Skills section and to a project or experience bullet that shows how you used them."})
    if kw_missing:
        out.append({"severity": "medium", "title": "Mirror the job description's wording",
                    "detail": "Terms the JD repeats but your resume lacks: " + ", ".join(kw_missing[:8]) + ". Use the same phrasing where it is accurate."})
    for issue in fmt_issues:
        out.append(issue)
    if sec_checks.get("Skills", 1) == 0:
        out.append({"severity": "high", "title": "Add a dedicated Skills section",
                    "detail": "ATS looks for a clear 'Skills' heading. List tools and technologies grouped by type."})
    if sec_checks.get("Experience or projects", 1) == 0:
        out.append({"severity": "high", "title": "Add Projects or Experience",
                    "detail": "Include at least 2 projects or internships with what you built, the stack, and the result."})
    if sec_checks.get("Summary", 1) == 0:
        out.append({"severity": "low", "title": "Add a 2-line summary",
                    "detail": "A short summary near the top that names the target role helps both ATS and recruiters."})
    if req_years and exp_years < req_years:
        out.append({"severity": "medium", "title": f"Role asks for {req_years}+ years of experience",
                    "detail": "Your dated experience adds up to less than that. Highlight internships, freelance work and substantial projects with dates."})
    if jd_skills and len(matched) == len(jd_skills):
        out.append({"severity": "low", "title": "All JD skills are covered",
                    "detail": "Strengthen them with measurable results so the match is backed by evidence."})
    order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda s: order.get(s["severity"], 3))
    return out
