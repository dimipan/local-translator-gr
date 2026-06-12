from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import io
import unicodedata


@dataclass
class ExtractedDocument:
    filename: str
    extension: str
    text: str
    warnings: list[str] = field(default_factory=list)
    page_count: int | None = None


def normalise_greek_text(text: str) -> str:
    """Normalise Unicode without stripping Greek/polytonic diacritics."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # NFC keeps precomposed characters where available and is safer for Greek diacritics.
    return unicodedata.normalize("NFC", text)


def decode_text_bytes(data: bytes) -> tuple[str, str]:
    """Try encodings often seen in Greek text files."""
    encodings = ["utf-8-sig", "utf-8", "utf-16", "cp1253", "iso-8859-7"]
    last_error: Exception | None = None
    for enc in encodings:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError as exc:
            last_error = exc
    # Last-resort replacement keeps the pipeline running and surfaces a warning upstream.
    return data.decode("utf-8", errors="replace"), "utf-8-with-replacement"


def extract_text_from_pdf(
    data: bytes,
    *,
    use_ocr_for_empty_pages: bool = False,
    ocr_lang: str = "ell+eng",
    min_page_chars_before_ocr: int = 40,
) -> tuple[str, list[str], int]:
    """Extract text from a PDF using PyMuPDF, with optional OCR fallback for empty/scanned pages."""
    warnings: list[str] = []
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover - environment issue
        raise RuntimeError("PyMuPDF is required for PDF extraction. Install requirements.txt.") from exc

    pages: list[str] = []
    doc = fitz.open(stream=data, filetype="pdf")

    for page_index, page in enumerate(doc, start=1):
        page_text = page.get_text("text", sort=True) or ""
        page_text = normalise_greek_text(page_text).strip()

        if use_ocr_for_empty_pages and len(page_text) < min_page_chars_before_ocr:
            try:
                import pytesseract
                from PIL import Image

                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(image, lang=ocr_lang)
                ocr_text = normalise_greek_text(ocr_text).strip()
                if len(ocr_text) > len(page_text):
                    page_text = ocr_text
                else:
                    warnings.append(
                        f"Page {page_index}: OCR ran but did not improve extracted text."
                    )
            except Exception as exc:
                warnings.append(
                    f"Page {page_index}: native text was sparse and OCR failed or is not configured: {exc}"
                )

        if not page_text:
            warnings.append(f"Page {page_index}: no text extracted.")

        pages.append(f"[Page {page_index}]\n{page_text}".strip())

    return "\n\n".join(pages), warnings, len(doc)


def extract_text_from_xml(data: bytes) -> tuple[str, list[str]]:
    """Extract visible text from XML while avoiding tags and attributes."""
    warnings: list[str] = []
    decoded, encoding = decode_text_bytes(data)
    try:
        from lxml import etree

        parser = etree.XMLParser(recover=True, remove_comments=True)
        root = etree.fromstring(decoded.encode("utf-8"), parser=parser)
        parts = [part.strip() for part in root.itertext() if part and part.strip()]
        text = "\n\n".join(parts)
        if not text.strip():
            warnings.append("XML parsed, but no text nodes were found.")
        if encoding.endswith("replacement"):
            warnings.append("Some characters could not be decoded cleanly from the XML file.")
        return normalise_greek_text(text), warnings
    except Exception as exc:
        warnings.append(f"XML parsing failed, falling back to plain text extraction: {exc}")
        return normalise_greek_text(decoded), warnings


def extract_document(
    filename: str,
    data: bytes,
    *,
    use_ocr_for_empty_pdf_pages: bool = False,
    ocr_lang: str = "ell+eng",
) -> ExtractedDocument:
    ext = Path(filename).suffix.lower().lstrip(".")
    warnings: list[str] = []
    page_count: int | None = None

    if ext == "pdf":
        text, pdf_warnings, page_count = extract_text_from_pdf(
            data,
            use_ocr_for_empty_pages=use_ocr_for_empty_pdf_pages,
            ocr_lang=ocr_lang,
        )
        warnings.extend(pdf_warnings)
    elif ext in {"txt", "md", "markdown"}:
        text, encoding = decode_text_bytes(data)
        if encoding.endswith("replacement"):
            warnings.append("Some characters could not be decoded cleanly.")
        text = normalise_greek_text(text)
    elif ext == "xml":
        text, xml_warnings = extract_text_from_xml(data)
        warnings.extend(xml_warnings)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    if not text.strip():
        warnings.append("The extracted document text is empty.")

    return ExtractedDocument(
        filename=filename,
        extension=ext,
        text=text,
        warnings=warnings,
        page_count=page_count,
    )
