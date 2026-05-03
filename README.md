# PDF2Base64

GUI tool to convert a PDF file into a Base64 string ready to embed in JSON payloads.

Built with Python + Tkinter. No external dependencies.

---

## What it does

1. **Pick a PDF** — opens a file dialog to select any `.pdf`
2. **Encodes to Base64** — reads the raw bytes and converts with `base64.b64encode`
3. **Shows two outputs**:
   - `Base64 raw` tab — the plain Base64 string
   - `JSON snippet` tab — a ready-to-use JSON object with a configurable field name (default: `allegato`) and the original filename
4. **Actions available**:
   - Copy Base64 to clipboard
   - Copy JSON snippet to clipboard
   - Save as `.txt`
   - Save as `.json`
   - Reset

---

## Requirements

- Python 3.x
- `tkinter` (included in standard Python distributions)

No `pip install` needed.

---

## Usage

```bash
python PDF2Base64.py
```

---

## Output example

**Base64 raw tab:**
```
JVBERi0xLjQKJeLjz9MKNiAwIG9iago8PC9...
```

**JSON snippet tab:**
```json
{
  "allegato": "JVBERi0xLjQKJeLjz9MKNiAwIG9iago8PC9...",
  "_filename": "documento.pdf"
}
```

The JSON field name is editable live in the UI — change `allegato` to any key your API expects.

---

## Use case

Useful when an API or automation (e.g. n8n, Make, Zapier) expects a PDF embedded as a Base64 string inside a JSON body rather than as a multipart file upload.
