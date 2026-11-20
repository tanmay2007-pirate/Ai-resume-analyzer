"""Generate a sample resume (PDF + DOCX) and a sample job description for testing.
Run:  python samples/make_samples.py
Requires: pip install reportlab   (only for this helper, not needed on Render)
"""
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent

LINES = [
    ("Aarav Kulkarni", "title"),
    ("aarav.kulkarni@example.com | +91 98765 43210 | github.com/aaravk | linkedin.com/in/aaravk", "text"),
    ("Summary", "h"),
    ("Second-year Computer Engineering student focused on full-stack development and applied machine learning.", "text"),
    ("Education", "h"),
    ("B.Tech in Computer Science Engineering, MIT Academy of Engineering, Pune (2025 - 2029)", "text"),
    ("Skills", "h"),
    ("Python, JavaScript, HTML, CSS, React, Node.js, Flask, SQL, MongoDB, Git, GitHub, Docker, REST API, scikit-learn, Pandas", "text"),
    ("Projects", "h"),
    ("• Built a quiz platform with HTML, CSS, JavaScript and Supabase used by 120 students.", "text"),
    ("• Developed a goal-tracking web app using React and Node.js with JWT authentication.", "text"),
    ("• Created a sorting algorithm visualizer in JavaScript to teach data structures.", "text"),
    ("• Implemented a TF-IDF based text classifier in Python reaching 88% accuracy.", "text"),
    ("Experience", "h"),
    ("Web Development Intern, Pune Tech Labs  Jun 2026 - Aug 2026", "text"),
    ("• Improved page load time by 30% by optimizing React components.", "text"),
    ("• Collaborated with a team of 4 using Git and Agile sprints.", "text"),
    ("Certifications", "h"),
    ("• Python for Everybody - Coursera", "text"),
    ("• Introduction to Machine Learning - NPTEL", "text"),
]

JD = """Software Engineer Intern - Full Stack (AI)

We are looking for a motivated intern to join our product team. You will build web features with
React and FastAPI, design REST APIs, and work with PostgreSQL and Docker. Experience with Python,
JavaScript, TypeScript and Git is required. Familiarity with machine learning, NLP and AWS is a plus.
Strong communication, problem solving and teamwork skills are expected. You will write unit tests,
use CI/CD pipelines and follow Agile practices. 1+ years of project or internship experience preferred.
"""


def make_pdf():
    c = canvas.Canvas(str(OUT / "sample_resume.pdf"), pagesize=A4)
    y = 800
    for text, kind in LINES:
        if kind == "title":
            c.setFont("Helvetica-Bold", 20); y -= 4
        elif kind == "h":
            y -= 8; c.setFont("Helvetica-Bold", 12)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(50, y, text.replace("•", "-"))
        y -= 18 if kind != "title" else 24
    c.save()


def make_docx():
    d = Document()
    for text, kind in LINES:
        if kind == "title":
            d.add_heading(text, 0)
        elif kind == "h":
            d.add_heading(text, 2)
        else:
            d.add_paragraph(text)
    d.save(OUT / "sample_resume.docx")


if __name__ == "__main__":
    make_pdf()
    make_docx()
    (OUT / "sample_job_description.txt").write_text(JD, encoding="utf-8")
    print("Sample files written to", OUT)
