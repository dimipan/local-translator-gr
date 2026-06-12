from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from chunking import TextChunk, chunk_text
from ollama_client import OllamaClient


# SYSTEM_PROMPT = """You are a professional translator from Greek to English.
# You handle modern Greek, katharevousa, and polytonic Greek.
# Translate faithfully into clear English.
# Preserve paragraph boundaries, headings, names, citations, page markers, numbers, and lists.
# Do not summarise, explain, add commentary, or wrap the answer in Markdown fences.
# Output only the English translation.
# """.strip()

SYSTEM_PROMPT = """You are a professional translator from Greek to English.
You handle modern Greek, katharevousa, and polytonic Greek.
Translate faithfully into clear English.

STRUCTURAL AND FORMATTING RULES:
- Strictly preserve all original paragraph boundaries.
- Keep all markdown headings (e.g., #, ##) exactly as they appear in the source.
- Keep angle brackets < > and square brackets [ ] exactly as they appear, as they denote specific manuscript additions and omissions.
- If a word is split across a line or page break in the source text, merge it and translate it naturally.
- Consolidate all footnotes (marked with *, †, or numbers) and place them at the very bottom of your translated output block.
- Preserve names, citations, page markers, numbers, and lists.
- Do not summarise, explain, add commentary, or wrap the answer in Markdown fences.
- Output only the English translation.
""".strip()


@dataclass
class TranslationSettings:
    source_variant: str = "el-polyton"
    target_language: str = "en"
    max_chunk_chars: int = 3500
    glossary: str = ""


@dataclass
class TranslationResult:
    translated_text: str
    chunks: list[TextChunk]
    translated_chunks: list[str]


def build_translation_prompt(
    chunk: TextChunk,
    *,
    total_chunks: int,
    settings: TranslationSettings,
    document_title: str,
) -> str:
    glossary_block = ""
    if settings.glossary.strip():
        glossary_block = f"""
Use this glossary/preference list when relevant. Do not translate glossary terms mechanically if the context requires a better rendering.
{settings.glossary.strip()}
""".strip()

    return f"""
Task: Translate the following document chunk from {settings.source_variant} to {settings.target_language}.
Document: {document_title}
Chunk: {chunk.index} of {total_chunks}

Rules:
- Preserve meaning, tone, paragraph boundaries, headings, page markers, names, dates, references, and numbering.
- If a word or name is ambiguous, choose the most likely English rendering and keep the original in parentheses only when necessary.
- Do not add notes outside the translation.
- Return only the translated English text for this chunk.

{glossary_block}

SOURCE CHUNK START
{chunk.text}
SOURCE CHUNK END
""".strip()


def translate_document(
    text: str,
    *,
    document_title: str,
    client: OllamaClient,
    settings: TranslationSettings,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> TranslationResult:
    chunks = chunk_text(text, max_chars=settings.max_chunk_chars)
    translated_chunks: list[str] = []

    for chunk in chunks:
        if progress_callback:
            progress_callback(chunk.index, len(chunks), "translating")
        prompt = build_translation_prompt(
            chunk,
            total_chunks=len(chunks),
            settings=settings,
            document_title=document_title,
        )
        translated = client.generate(prompt, system=SYSTEM_PROMPT)
        translated_chunks.append(clean_translation(translated))

    return TranslationResult(
        translated_text="\n\n".join(translated_chunks).strip(),
        chunks=chunks,
        translated_chunks=translated_chunks,
    )


def clean_translation(text: str) -> str:
    cleaned = text.strip()
    # Remove common fence leakage without touching legitimate content.
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2:
            cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned
