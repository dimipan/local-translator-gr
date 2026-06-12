from __future__ import annotations

from pathlib import Path
from translation import TranslationResult


def output_stem(filename: str) -> str:
    path = Path(filename)
    return f"{path.stem}_en"


def as_markdown(filename: str, translated_text: str) -> str:
    title = Path(filename).stem.replace("_", " ").strip() or "Translated document"
    return f"# {title} — English translation\n\n{translated_text.strip()}\n"


def as_side_by_side_markdown(filename: str, result: TranslationResult) -> str:
    lines = [f"# {Path(filename).stem} — Greek to English side-by-side", ""]
    for source, target in zip(result.chunks, result.translated_chunks):
        lines.append(f"## Chunk {source.index}")
        lines.append("")
        lines.append("### Source")
        lines.append(source.text.strip())
        lines.append("")
        lines.append("### Translation")
        lines.append(target.strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"
