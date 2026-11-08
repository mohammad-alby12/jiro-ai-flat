from pathlib import Path
from pypdf import PdfReader
from docx import Document

def extract_text(path: str, suffix: str) -> str:
    if suffix == ".txt":
        return Path(path).read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Format file tidak didukung.")
