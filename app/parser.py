"""Resume file parsing: PDF (PyMuPDF) and DOCX (python-docx) -> text + layout signals."""
import io
import re
from dataclasses import dataclass, field

import pymupdf  # PyMuPDF
from docx import Document


@dataclass
class ParsedResume:
    text: str
    file_type: str
    pages: int = 1
    layout: dict = field(default_factory=dict)


def clean_text(text: str) -> str:
    text = text.replace(" ", " ").replace("•", "•")
    text = re.sub(r"[​‌‍﻿]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def parse_pdf(data: bytes) -> ParsedResume:
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages_text, images, two_col_blocks = [], 0, 0
    for page in doc:
        pages_text.append(page.get_text("text"))
        images += len(page.get_images(full=True))
        width = page.rect.width
        for block in page.get_text("blocks"):
            x0, _, x1, _, txt = block[0], block[1], block[2], block[3], block[4]
            if isinstance(txt, str) and len(txt.strip()) > 25:
                if x0 > width * 0.45 and (x1 - x0) < width * 0.48:
                    two_col_blocks += 1
    pages = len(doc)
    doc.close()
    return ParsedResume(
        text=clean_text("\n".join(pages_text)),
        file_type="pdf",
        pages=pages,
        layout={"images": images, "tables": 0, "multi_column": two_col_blocks >= 6,
                "header_footer_text": False},
    )


def parse_docx(data: bytes) -> ParsedResume:
    doc = Document(io.BytesIO(data))
    lines = [p.text for p in doc.paragraphs]
    tables = len(doc.tables)
    for table in doc.tables:  # table text is still extracted, but flagged as a risk
        for row in table.rows:
            for cell in row.cells:
                lines.append(cell.text)
    images = len(doc.inline_shapes)
    header_footer = False
    for section in doc.sections:
        for part in (section.header, section.footer):
            if any(p.text.strip() for p in part.paragraphs):
                header_footer = True
    return ParsedResume(
        text=clean_text("\n".join(lines)),
        file_type="docx",
        pages=max(1, round(len(" ".join(lines).split()) / 450)),
        layout={"images": images, "tables": tables, "multi_column": False,
                "header_footer_text": header_footer},
    )


def parse_resume(filename: str, data: bytes) -> ParsedResume:
    name = filename.lower()
    if name.endswith(".pdf"):
        return parse_pdf(data)
    if name.endswith(".docx"):
        return parse_docx(data)
    raise ValueError("Unsupported file type. Please upload a PDF or DOCX resume.")
