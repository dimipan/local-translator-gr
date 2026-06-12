# Greek Document Translator Prototype

A small local prototype for translating Greek / polytonic Greek documents into English using a local Ollama model such as `translategemma:27b`.

Supported input files in this prototype:

- PDF
- TXT
- Markdown (`.md` / `.markdown`)
- XML, by extracting text nodes

Outputs:

- English translation as plain text
- Markdown export
- Side-by-side Markdown export with source chunks and translated chunks

## 1. Prerequisites

Install Ollama and pull a translation model:

```bash
ollama pull translategemma:27b
```

For a faster/lighter first test, use:

```bash
ollama pull translategemma:12b
```

Make sure Ollama is running:

```bash
ollama serve
```

In many desktop installations Ollama may already be running in the background.

## 2. Create a Python environment

From this project folder:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell
pip install -r requirements.txt
```

## 3. Run the app

```bash
streamlit run app.py
```

Open the URL shown by Streamlit, usually:

```text
http://localhost:8501
```

## 4. Recommended settings for your 24 GB VRAM machine

Start with:

- Model: `translategemma:27b`
- Source Greek variant: `el-polyton` for polytonic Greek, otherwise `el-GR`
- Max characters per chunk: `3000` to `4000`
- Ollama `num_ctx`: `4096`
- Temperature: `0.0`

If you hit VRAM pressure or slow performance:

- Try `translategemma:12b`
- Reduce `num_ctx` to `2048` or `4096`
- Reduce max chunk size to `2500` to `3000`

## 5. OCR for scanned PDFs

The prototype first tries native PDF text extraction. This is best for digitally generated PDFs.

For scanned PDFs, enable **Use OCR for PDF pages with little/no text** in the sidebar. You must also install Tesseract and Greek language data locally.

### Ubuntu / Debian

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-ell
```

### macOS with Homebrew

```bash
brew install tesseract tesseract-lang
```

### Windows

Install Tesseract from the official Windows installer and make sure it is on your PATH. Also install Greek language data.

The default OCR language setting in the app is:

```text
ell+eng
```

## 6. Project structure

```text
.
├── app.py
├── requirements.txt
├── README.md
└── greek_doc_translator
    ├── extractors.py       # PDF/TXT/MD/XML extraction
    ├── chunking.py         # paragraph-aware chunking
    ├── ollama_client.py    # local Ollama API wrapper
    ├── translation.py      # prompt construction and chunk translation
    └── exporters.py        # TXT/MD/side-by-side exports
```

## 7. Important limitations

This is a prototype, not a production translation system.

Known limitations:

- Layout preservation is minimal; exports are text/Markdown rather than a reconstructed PDF.
- PDF extraction quality depends on the source file.
- Scanned polytonic Greek PDFs may require careful OCR setup and manual review.
- XML output currently extracts text nodes; it does not rebuild a translated XML file.
- Chunk-by-chunk translation may occasionally create inconsistent terminology unless you use the glossary field.

## 8. Next improvements

Useful next steps:

- Add DOCX export.
- Add glossary memory per project.
- Add a proper job queue for very large PDFs.
- Add page-by-page review and correction.
- Add translated XML reconstruction.
- Add OCR confidence reporting.
- Add a second local model for general chat/Q&A over the translated document.
