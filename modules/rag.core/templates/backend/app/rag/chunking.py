"""Split text into overlapping chunks.

recursive: split on the largest natural boundary that fits (paragraphs, then lines,
then sentences, then words), so chunks rarely cut a sentence in half.
fixed: equal-sized character windows. Predictable, but cuts mid-sentence.
"""

from __future__ import annotations

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]


def fixed_split(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    step = max(1, size - overlap)
    return [text[i : i + size].strip() for i in range(0, len(text), step) if text[i : i + size].strip()]


def _pieces(text: str, size: int, seps: list[str]) -> list[str]:
    """Break text into pieces no longer than `size`, at the coarsest separator possible."""
    if len(text) <= size:
        return [text]
    for i, sep in enumerate(seps):
        if sep in text:
            parts = text.split(sep)
            out: list[str] = []
            for j, part in enumerate(parts):
                piece = part + (sep if j < len(parts) - 1 else "")
                if len(piece) > size:
                    out.extend(_pieces(piece, size, seps[i + 1 :]))
                elif piece:
                    out.append(piece)
            return out
    return [text[i : i + size] for i in range(0, len(text), size)]


def recursive_split(text: str, size: int, overlap: int) -> list[str]:
    pieces = _pieces(text.strip(), size, SEPARATORS)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap else ""
            # Start the overlap at a word boundary.
            if " " in tail:
                tail = tail[tail.index(" ") + 1 :]
            current = tail + piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


def split(text: str, chunker: str, size: int, overlap: int) -> list[str]:
    if chunker == "fixed":
        return fixed_split(text, size, overlap)
    return recursive_split(text, size, overlap)
