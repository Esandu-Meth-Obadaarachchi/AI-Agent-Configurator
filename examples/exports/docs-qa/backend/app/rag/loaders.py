"""Turn files into plain text."""

from __future__ import annotations

import io
from pathlib import Path

EXTENSIONS = {
    "pdf": (".pdf",),
    "markdown": (".md", ".markdown"),
    "text": (".txt",),
    "html": (".html", ".htm"),
}


def load_bytes(name: str, data: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(f"[page {i}]\n{p}" for i, p in enumerate(pages, start=1) if p)
    text = data.decode("utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return text


def load_file(path: Path) -> str:
    return load_bytes(path.name, path.read_bytes())
