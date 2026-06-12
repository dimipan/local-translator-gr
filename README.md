# Greek Document Translator Prototype

A robust local prototype for translating Greek / polytonic Greek documents into English using a local Ollama model (e.g., `translategemma:27b`). 

Recent updates have upgraded this pipeline to support state-of-the-art vision extraction via Marker, persistent local glossaries, and intelligent prompt formatting to preserve scholarly structures (e.g., footnotes, page breaks, and split words).

Supported input files:
- PDF (Native or Scanned)
- TXT
- Markdown (`.md` / `.markdown`)
- XML (extracting text nodes)

Outputs:
- English translation as plain text
- Markdown export
- Side-by-side Markdown export with source chunks and translated chunks

---

## 1. Prerequisites

**A. Ollama & Models**
Make sure Ollama is installed and running (`ollama serve`). Pull the recommended models:
```bash
ollama pull translategemma:27b
```
*(For a faster/lighter fallback, use `translategemma:12b`)*

**B. Python Environment**
From this project folder:
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell
pip install -r requirements.txt
```
*Note: Ensure `marker-pdf` is included in your requirements or installed via `pip install marker-pdf`.*

**C. GPU Drivers (For Marker)**
Marker utilizes PyTorch vision models (Surya). Ensure your NVIDIA drivers (e.g., `nvidia-driver-595`) and CUDA are correctly configured. If PyTorch cannot detect the GPU, Marker will fallback to CPU extraction, which is extremely slow.

---

## 2. Extraction Engines & Polytonic OCR

This application supports two distinct PDF extraction engines, selectable in the sidebar:

1. **Marker (State-of-the-Art OCR):** Recommended for scanned academic papers and complex polytonic diacritics. It physically reads the layout and translates it into clean Markdown. 
2. **PyMuPDF (Fast):** Recommended for born-digital PDFs with perfect font mapping.

**Force complete OCR:** If your scanned PDF contains a hidden layer of "gibberish" text from a primitive scanner, check the **Force complete OCR** box. This commands Marker/Tesseract to ignore the corrupted embedded text and visually read the document from scratch.

**Tesseract Fallback (Polytonic Support):**
If you use PyMuPDF's OCR fallback, you *must* install the Ancient Greek language pack for accurate polytonic support.
- Ubuntu / Debian: `sudo apt-get install tesseract-ocr tesseract-ocr-ell tesseract-ocr-grc`
- Update the app's OCR setting to: `grc+ell+eng`

---

## 3. Run the app

```bash
streamlit run app.py
```
Open the URL shown by Streamlit, usually `http://localhost:8501`.

---

## 4. Recommended Settings (24 GB VRAM / RTX A5000)

To maximize translation fidelity and prevent truncation during large chunk processing, configure the sidebar as follows:

- **Model:** `translategemma:27b`
- **Source Greek variant:** `el-polyton`
- **Max characters per chunk:** `3500` to `4000`
- **Ollama num_ctx:** `8192` *(Crucial for large chunks)*
- **Temperature:** `0.0` *(Essential for literal, deterministic scholarly translation)*

---

## 5. Optimal Workflow & Glossary Management

**A. Logical Batching**
Instead of uploading a massive 40-page PDF at once, process documents in 5–10 page batches. This prevents Streamlit server timeouts, avoids VRAM fragmentation, and prevents the model from hallucinating or compounding errors over massive contexts.

**B. The Persistent Glossary**
The sidebar features an autosaving Glossary. Any terms entered here are instantly saved to `glossary.txt` in your project directory, surviving app restarts and browser refreshes. 

Use this to enforce consistency across your 5-10 page batches. Examples:
```text
ἀγχιβασίην = anxiety / approaching
ἐδιζησάμην ἐμεωυτόν = I sought myself
αἰ. = century (cent. / c.)
ὑ. = footnote (fn.)
```

---

## 6. Project Structure

```text
.
├── app.py                  # Streamlit UI & caching
├── requirements.txt
├── README.md               # This file
├── glossary.txt            # Autosaved translation preferences
└── greek_doc_translator
    ├── extractors.py       # PyMuPDF & Marker extraction logic
    ├── chunking.py         # Paragraph-aware chunking
    ├── ollama_client.py    # Local Ollama API wrapper
    ├── translation.py      # LLM prompts & structural rules
    └── exporters.py        # TXT/MD/side-by-side exports
```

---

## 7. Known Limitations

- **Statefulness:** Streamlit is stateless. Navigating away or hard-refreshing during translation will interrupt the process (though the glossary remains safe).
- **XML Output:** Currently extracts text nodes; it does not rebuild a translated XML file.
