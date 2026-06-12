from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from extractors import extract_document
from ollama_client import OllamaClient, OllamaConfig, OllamaError
from translation import TranslationSettings, translate_document
from exporters import as_markdown, as_side_by_side_markdown, output_stem


st.set_page_config(
    page_title="Greek Document Translator",
    page_icon="🇬🇷",
    layout="wide",
)

st.title("Greek / Polytonic Greek → English Local Translator")
st.caption("Prototype UI for translating PDF, TXT, MD, and XML files with a local Ollama model.")

with st.sidebar:
    st.header("Local model")
    ollama_host = st.text_input(
        "Ollama host",
        value=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        help="Default Ollama endpoint is usually http://localhost:11434.",
    )
    model = st.text_input(
        "Model",
        value=os.getenv("OLLAMA_MODEL", "translategemma:27b"),
        help="Examples: translategemma:27b, translategemma:12b, translategemma:4b.",
    )
    source_variant = st.selectbox(
        "Source Greek variant",
        options=["el-polyton", "el-GR", "el"],
        index=0,
    )
    max_chunk_chars = st.slider(
        "Max characters per chunk",
        min_value=1200,
        max_value=9000,
        value=3500,
        step=100,
        help="Lower values are slower but usually safer for translation fidelity.",
    )
    num_ctx = st.select_slider(
        "Ollama num_ctx",
        options=[2048, 4096, 8192, 16384, 32768],
        value=4096,
        help="Higher context uses more VRAM. 4096 is a safe starting point for chunked translation.",
    )
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        help="Translation should usually be deterministic, so 0.0 is recommended.",
    )

    st.header("PDF extraction")
    extractor_engine = st.radio(
        "PDF Extraction Engine",
        options=["PyMuPDF (Fast)", "Marker (State-of-the-Art OCR)"],
        index=0,
        help="Marker parses layout and handles polytonic diacritics beautifully, but is slower and requires VRAM."
    )
    
    use_ocr = st.checkbox(
        "Use Tesseract for empty pages (PyMuPDF only)",
        value=False,
    )
    force_ocr = st.checkbox(
        "Force complete OCR",
        value=False,
        help="Use for scanned documents or PDFs with corrupted font mapping."
    )
    ocr_lang = st.text_input(
        "Tesseract OCR languages", 
        value="grc+ell+eng",
        help="Use 'grc' for polytonic/ancient Greek support."
    )

    st.header("Glossary")
    glossary = st.text_area(
        "Optional translation preferences",
        placeholder="Example:\nλόγος = reason / discourse depending on context\nΚωνσταντινούπολις = Constantinople",
        height=120,
    )


client = OllamaClient(
    OllamaConfig(
        host=ollama_host,
        model=model,
        temperature=temperature,
        num_ctx=num_ctx,
    )
)

uploaded = st.file_uploader(
    "Drop a Greek document here",
    type=["pdf", "txt", "md", "markdown", "xml"],
    accept_multiple_files=False,
)

manual_text = ""
with st.expander("Or paste Greek text manually"):
    manual_text = st.text_area("Greek source text", height=200)
    manual_title = st.text_input("Manual text title", value="manual_text")

col_a, col_b = st.columns([1, 1])
with col_a:
    check = st.button("Check Ollama connection")
with col_b:
    translate_clicked = st.button("Translate to English", type="primary")

if check:
    try:
        models = client.check_server()
        if models:
            st.success(f"Connected to Ollama. Installed models: {', '.join(models[:10])}")
            if model not in models:
                st.warning(f"The selected model `{model}` was not listed. Pull it with: `ollama pull {model}`")
        else:
            st.warning("Connected to Ollama, but no local models were listed.")
    except OllamaError as exc:
        st.error(str(exc))


def load_source() -> tuple[str, str, list[str], int | None]:
    if uploaded is not None:
        engine_map = {
            "PyMuPDF (Fast)": "pymupdf", 
            "Marker (State-of-the-Art OCR)": "marker"
        }
        doc = extract_document(
            uploaded.name,
            uploaded.getvalue(),
            extractor_engine=engine_map[extractor_engine],
            use_ocr_for_empty_pdf_pages=use_ocr,
            force_ocr=force_ocr,
            ocr_lang=ocr_lang,
        )
        return doc.filename, doc.text, doc.warnings, doc.page_count
    if manual_text.strip():
        return f"{manual_title.strip() or 'manual_text'}.txt", manual_text.strip(), [], None
    return "", "", ["Upload a file or paste text first."], None


if uploaded is not None or manual_text.strip():
    try:
        with st.spinner("Extracting document text (Marker may take a moment)..."):
            filename, source_text, warnings, page_count = load_source()
        with st.chat_message("user"):
            st.write(f"Loaded **{filename}**")
            if page_count is not None:
                st.write(f"PDF pages: **{page_count}**")
            st.write(f"Extracted characters: **{len(source_text):,}**")
            if warnings:
                for warning in warnings:
                    st.warning(warning)

        with st.expander("Preview extracted source text", expanded=False):
            st.text_area("Source preview", value=source_text[:8000], height=260)
    except Exception as exc:
        st.error(f"Could not extract the document: {exc}")
        source_text = ""
        filename = uploaded.name if uploaded else "manual_text.txt"

if translate_clicked:
    try:
        with st.spinner("Extracting document text for translation..."):
            filename, source_text, warnings, page_count = load_source()
        if not source_text.strip():
            st.error("No source text was available for translation.")
            st.stop()

        # Fail fast on Ollama connectivity/model availability where possible.
        try:
            models = client.check_server()
            if models and model not in models:
                st.warning(f"`{model}` is not listed locally. If translation fails, run: `ollama pull {model}`")
        except OllamaError as exc:
            st.error(str(exc))
            st.stop()

        settings = TranslationSettings(
            source_variant=source_variant,
            target_language="en",
            max_chunk_chars=max_chunk_chars,
            glossary=glossary,
        )

        progress = st.progress(0, text="Preparing chunks…")
        status_box = st.empty()

        def update_progress(done: int, total: int, stage: str) -> None:
            progress.progress(done / max(total, 1), text=f"Translating chunk {done}/{total}")
            status_box.info(f"Working on chunk {done} of {total}.")

        result = translate_document(
            source_text,
            document_title=filename,
            client=client,
            settings=settings,
            progress_callback=update_progress,
        )
        progress.progress(1.0, text="Translation complete")
        status_box.success("Translation complete.")

        st.session_state["last_translation"] = result
        st.session_state["last_filename"] = filename

    except OllamaError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Translation failed: {exc}")


if "last_translation" in st.session_state:
    result = st.session_state["last_translation"]
    filename = st.session_state["last_filename"]
    stem = output_stem(filename)

    with st.chat_message("assistant"):
        st.subheader("English translation")
        st.text_area("Translation", value=result.translated_text, height=420)

        md = as_markdown(filename, result.translated_text)
        side_by_side = as_side_by_side_markdown(filename, result)

        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Download .txt",
            data=result.translated_text.encode("utf-8"),
            file_name=f"{stem}.txt",
            mime="text/plain",
        )
        c2.download_button(
            "Download .md",
            data=md.encode("utf-8"),
            file_name=f"{stem}.md",
            mime="text/markdown",
        )
        c3.download_button(
            "Download side-by-side .md",
            data=side_by_side.encode("utf-8"),
            file_name=f"{stem}_side_by_side.md",
            mime="text/markdown",
        )

st.divider()
st.caption(
    "Prototype notes: for scanned PDFs, install Tesseract + Greek language data and enable OCR. "
    "For best quality, keep chunk size conservative and use temperature 0."
)
