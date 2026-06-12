from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    index: int
    text: str
    start_char: int
    end_char: int


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split very long paragraphs at sentence-ish boundaries when possible."""
    if len(paragraph) <= max_chars:
        return [paragraph]

    # Greek punctuation includes ano teleia and Greek question mark; keep them as boundaries.
    pieces = re.split(r"(?<=[.!?;;。·])\s+", paragraph)
    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if not piece:
            continue
        if len(buf) + len(piece) + 1 <= max_chars:
            buf = f"{buf} {piece}".strip()
        else:
            if buf:
                chunks.append(buf)
            if len(piece) > max_chars:
                # Hard split as a last resort.
                chunks.extend(piece[i : i + max_chars] for i in range(0, len(piece), max_chars))
                buf = ""
            else:
                buf = piece
    if buf:
        chunks.append(buf)
    return chunks


def chunk_text(text: str, *, max_chars: int = 3500, overlap_chars: int = 0) -> list[TextChunk]:
    """Paragraph-aware chunker for translation.

    Character-based chunking is deliberate here. It is model-agnostic, simple,
    and safer for a prototype than relying on a tokenizer that may not match the
    local model exactly.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[TextChunk] = []
    buf = ""
    char_cursor = 0
    chunk_start = 0

    def flush() -> None:
        nonlocal buf, chunk_start
        cleaned = buf.strip()
        if cleaned:
            chunks.append(
                TextChunk(
                    index=len(chunks) + 1,
                    text=cleaned,
                    start_char=chunk_start,
                    end_char=chunk_start + len(cleaned),
                )
            )
        if overlap_chars > 0 and cleaned:
            buf = cleaned[-overlap_chars:]
            chunk_start = max(0, chunk_start + len(cleaned) - overlap_chars)
        else:
            buf = ""
            chunk_start = char_cursor

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            char_cursor += 2
            continue
        for part in _split_long_paragraph(paragraph, max_chars):
            candidate = f"{buf}\n\n{part}".strip() if buf else part
            if len(candidate) <= max_chars:
                if not buf:
                    chunk_start = char_cursor
                buf = candidate
            else:
                flush()
                chunk_start = char_cursor
                buf = part
            char_cursor += len(part) + 2

    flush()
    return chunks
