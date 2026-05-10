"""Extraction texte PDF/DOCX/TXT pour l'enrichissement RAG du moteur vitaliste."""
import io
import logging

import pdfplumber
from docx import Document

logger = logging.getLogger("vitaform.extractor")
MAX_CHARS = 25_000  # safeguard for prompt size


def extract_pdf(data: bytes) -> str:
    out: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                out.append(txt)
                if sum(len(t) for t in out) > MAX_CHARS:
                    break
    except Exception as exc:
        logger.exception("PDF extraction failed: %s", exc)
        return ""
    return "\n\n".join(out)[:MAX_CHARS]


def extract_docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        logger.exception("DOCX extraction failed: %s", exc)
        return ""
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paragraphs)[:MAX_CHARS]


def extract_txt(data: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc)[:MAX_CHARS]
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")[:MAX_CHARS]


def extract(filename: str, content_type: str, data: bytes) -> str:
    name = (filename or "").lower()
    ct = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ct:
        return extract_pdf(data)
    if name.endswith(".docx") or "wordprocessingml" in ct:
        return extract_docx(data)
    return extract_txt(data)
