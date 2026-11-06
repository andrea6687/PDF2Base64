"""
PDF → Base64 Converter
Carica un PDF e ottieni la stringa base64 pronta per JSON (e viceversa).

Uso:
  python PDF2Base64.py                          # interfaccia grafica
  python PDF2Base64.py --gui documento.pdf      # interfaccia grafica con file già caricato
  python PDF2Base64.py documento.pdf            # stampa la stringa base64
  python PDF2Base64.py documento.pdf --json --field allegato -o payload.json
  python PDF2Base64.py --decode payload.json -o documento.pdf

Drag & drop nella finestra: opzionale, attivo se è installato `tkinterdnd2`.
"""

import argparse
import base64
import binascii
import json
import os
import sys
import threading

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:          # la riga di comando funziona anche senza Tkinter
    tk = None

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except Exception:
    TkinterDnD = None


DEFAULT_FIELD   = "allegato"
DATA_URI_PREFIX = "data:application/pdf;base64,"
PREVIEW_LIMIT   = 20_000     # caratteri mostrati a video; copia/salva usano sempre la stringa completa
NAME_KEYS       = ("_filename", "filename", "file_name", "nome_file", "nomefile", "name")


# ══════════════════════════════════════════════════════════════════════════════
#  Logica (nessuna dipendenza dalla GUI)
# ══════════════════════════════════════════════════════════════════════════════

def is_pdf(data: bytes) -> bool:
    """Un PDF valido contiene '%PDF-' entro i primi 1024 byte."""
    return b"%PDF-" in data[:1024]


def encode(data: bytes, data_uri: bool = False) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return DATA_URI_PREFIX + b64 if data_uri else b64


def build_payload(b64: str, field: str, filename: str, include_filename: bool = True) -> dict:
    payload = {field or DEFAULT_FIELD: b64}
    if include_filename and filename:
        payload["_filename"] = filename
    return payload


def payload_text(payload: dict, compact: bool = False) -> str:
    if compact:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n:,} byte"
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024 or unit == "GB":
            return f"{n:,.1f} {unit}"


def _collect_strings(obj, out, key=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _collect_strings(v, out, k)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out, key)
    elif isinstance(obj, str):
        out.append((key, obj))


def _extract_from_json(obj, field=None):
    """Trova la stringa base64 dentro un JSON: il campo indicato o, in mancanza, la stringa più lunga."""
    strings = []
    _collect_strings(obj, strings)
    if not strings:
        raise ValueError("Il JSON non contiene testo da decodificare.")

    name = next((v for k, v in strings if k in NAME_KEYS and v.strip()), None)
    if field:
        match = [v for k, v in strings if k == field]
        if match:
            return match[0], name
    return max(strings, key=lambda kv: len(kv[1]))[1], name


def decode_input(text: str, field: str = None):
    """
    Accetta base64 puro, data URI (data:application/pdf;base64,...) o un JSON che lo contiene.
    Restituisce (bytes, nome_file_suggerito_o_None).
    """
    s = (text or "").strip()
    if not s:
        raise ValueError("Nessun dato da decodificare.")

    name = None
    if s[0] in "{[":
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON non valido: {e.msg} (riga {e.lineno})")
        s, name = _extract_from_json(obj, field)

    s = s.strip().strip('"')
    if s.startswith("data:"):
        s = s.partition(",")[2]
    s = "".join(s.split())                         # via spazi e a capo
    s = s.replace("-", "+").replace("_", "/")      # variante "url-safe"
    s += "=" * (-len(s) % 4)                       # padding mancante

    try:
        data = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Il testo non è una stringa base64 valida.")
    if not data:
        raise ValueError("La stringa base64 è vuota.")
    return data, name


def _preview(s: str, limit: int = PREVIEW_LIMIT) -> str:
    if len(s) <= limit:
        return s
    return (s[:limit] + f"…\n\n[Anteprima: {limit:,} di {len(s):,} caratteri. "
            "I pulsanti Copia e Salva usano la stringa completa.]")


# ══════════════════════════════════════════════════════════════════════════════
#  Riga di comando
# ══════════════════════════════════════════════════════════════════════════════

def run_cli(args) -> int:
    def fail(msg):
        print(f"Errore: {msg}", file=sys.stderr)
        return 1

    # Il terminale di Windows non usa UTF-8: senza questo accenti e nomi file particolari danno errore
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    # ── Base64 → PDF
    if args.decode:
        try:
            if args.decode == "-":
                text = sys.stdin.read()
            else:
                with open(args.decode, "r", encoding="utf-8-sig") as f:
                    text = f.read()
            data, name = decode_input(text, args.field)
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return fail(e)
        if not is_pdf(data):
            print("Attenzione: il contenuto decodificato non sembra un PDF.", file=sys.stderr)
        out = args.output or name
        if not out:
            if sys.stdout.isatty():
                return fail("indica il file di destinazione con -o documento.pdf")
            sys.stdout.buffer.write(data)
            return 0
        try:
            with open(out, "wb") as f:
                f.write(data)
        except OSError as e:
            return fail(e)
        print(f"Salvato {out} ({human_size(len(data))})", file=sys.stderr)
        return 0

    # ── PDF → Base64
    try:
        if args.file == "-":
            data, filename = sys.stdin.buffer.read(), ""
        else:
            with open(args.file, "rb") as f:
                data = f.read()
            filename = os.path.basename(args.file)
    except OSError as e:
        return fail(e)
    if not is_pdf(data):
        print("Attenzione: il file non sembra un PDF, lo converto comunque.", file=sys.stderr)

    b64 = encode(data, args.data_uri)
    if args.json:
        result = payload_text(build_payload(b64, args.field or DEFAULT_FIELD, filename,
                                            not args.no_filename), args.compact)
    else:
        result = b64

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
        except OSError as e:
            return fail(e)
        print(f"Salvato {args.output} ({len(b64):,} caratteri base64)", file=sys.stderr)
    else:
        sys.stdout.write(result + "\n")
    return 0


# ══════════════════════════════════════════════════════════════════════════════
#  Interfaccia grafica
# ══════════════════════════════════════════════════════════════════════════════

# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0f1117"
PANEL    = "#1a1d27"
BORDER   = "#2a2d3a"
ACCENT   = "#5b8dee"
ACCENT2  = "#3ecf8e"
TEXT     = "#e8eaf0"
MUTED    = "#6b7089"
WARN     = "#f0b44a"
ERROR    = "#f06a6a"
GREY_BTN = "#4a4e6a"
DARK_BTN = "#3a3d50"

# Font che esistono davvero su ogni sistema (Segoe UI c'è solo su Windows)
if sys.platform == "darwin":
    SANS_FAMILY, MONO_FAMILY = "Helvetica Neue", "Menlo"
elif sys.platform.startswith("win"):
    SANS_FAMILY, MONO_FAMILY = "Segoe UI", "Consolas"
else:
    SANS_FAMILY, MONO_FAMILY = "DejaVu Sans", "DejaVu Sans Mono"


def font(size=10, weight="normal", mono=False):
    # su Mac i punti rendono più piccoli: +2 per avere lo stesso aspetto
    if sys.platform == "darwin":
        size += 2
    return (MONO_FAMILY if mono else SANS_FAMILY, size, weight)


def _lighten(hex_color, amount=0.15):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (int(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


_TkBase = object
if tk is not None:
    _TkBase = TkinterDnD.Tk if TkinterDnD else tk.Tk

    class FlatButton(tk.Label):
        """
        Bottone piatto colorato. I tk.Button su macOS ignorano il colore di sfondo
        (venivano bianchi con testo chiaro, quasi illeggibili): questo funziona ovunque.
        """
        def __init__(self, parent, text, command, bg, fg=TEXT, size=9, padx=14, pady=7):
            super().__init__(parent, text=text, bg=bg, fg=fg, font=font(size, "bold"),
                             padx=padx, pady=pady, cursor="hand2", takefocus=1,
                             highlightthickness=1, highlightbackground=bg, highlightcolor=ACCENT2)
            self._bg, self._hover, self._command = bg, _lighten(bg), command
            self.bind("<Enter>", lambda e: self.config(bg=self._hover))
            self.bind("<Leave>", lambda e: self.config(bg=self._bg))
            self.bind("<ButtonRelease-1>", self._click)
            self.bind("<Return>", self._click)
            self.bind("<space>", self._click)

        def _click(self, event=None):
            if event is not None and str(event.type) == "ButtonRelease":
                # click annullato se il mouse è uscito dal bottone prima di rilasciare
                if not (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()):
                    return
            self._command()


def _make_text(parent):
    frame = tk.Frame(parent, bg=PANEL)
    scroll = ttk.Scrollbar(frame, orient="vertical", style="Dark.Vertical.TScrollbar")
    scroll.pack(side="right", fill="y")
    txt = tk.Text(frame, wrap="char", font=font(10, mono=True), height=8,
                  bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                  selectbackground=ACCENT, selectforeground=BG,
                  relief="flat", bd=0, padx=12, pady=10, highlightthickness=0,
                  yscrollcommand=scroll.set, state="disabled")
    txt.pack(fill="both", expand=True)
    scroll.config(command=txt.yview)
    return frame, txt


def _set_text(widget, content, editable=False):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="normal" if editable else "disabled")


def _setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("default")
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    padding=[14, 6], font=font(9), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", BORDER)], foreground=[("selected", TEXT)])
    style.configure("Dark.Vertical.TScrollbar", background=BORDER, troughcolor=PANEL,
                    bordercolor=PANEL, arrowcolor=MUTED, relief="flat")
    style.map("Dark.Vertical.TScrollbar", background=[("active", ACCENT)])
    # Tk 8.6 colora la casella con "indicatorcolor", Tk 9 con "indicatorbackground":
    # impostiamo entrambi così la spunta si vede con qualsiasi versione di Python.
    style.configure("Dark.TCheckbutton", background=BG, foreground=TEXT, font=font(9),
                    indicatorcolor=BORDER, indicatorbackground=BORDER, indicatorforeground=BG,
                    indicatorrelief="flat", indicatormargin=[0, 0, 6, 0], focuscolor=BG)
    selected = [("selected", ACCENT2), ("active", MUTED)]
    style.map("Dark.TCheckbutton", background=[("active", BG)],
              indicatorcolor=selected, indicatorbackground=selected,
              indicatorrelief=[])


class PDFBase64Tool(_TkBase):
    def __init__(self, initial_file=None):
        super().__init__()
        self.title("PDF → Base64 | ISA Digital")
        self.configure(bg=BG)
        self.minsize(760, 600)

        self._data_b64    = ""     # base64 puro (senza prefisso)
        self._filename    = ""
        self._busy        = False
        self._refresh_job = None

        self.field_var     = tk.StringVar(value=DEFAULT_FIELD)
        self.with_name_var = tk.BooleanVar(value=True)
        self.data_uri_var  = tk.BooleanVar(value=False)
        self.compact_var   = tk.BooleanVar(value=False)
        self.status_var    = tk.StringVar(value="Pronto.")

        _setup_styles(self)
        self._build_ui()
        self._bind_shortcuts()
        self._center_window(800, 680)

        if initial_file:
            self.after(100, self._load_file, initial_file)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _center_window(self, w, h):
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _empty_hint(self):
        return "Trascina qui un PDF, oppure" if TkinterDnD else "Nessun file selezionato"

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=PANEL, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⬡  PDF → Base64", font=font(15, "bold", mono=True),
                 fg=ACCENT, bg=PANEL).pack(side="left", padx=24)
        tk.Label(hdr, text="encoder per payload JSON", font=font(9),
                 fg=MUTED, bg=PANEL).pack(side="left")
        FlatButton(hdr, "↩  Base64 → PDF", self._open_decoder, DARK_BTN).pack(side="right", padx=24)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Zona file (anche drag & drop se disponibile)
        drop = tk.Frame(self, bg=BG, pady=18)
        drop.pack(fill="x", padx=24)
        self.drop_label = tk.Label(drop, text=self._empty_hint(), font=font(10), fg=MUTED, bg=BG)
        self.drop_label.pack(side="left", padx=(0, 12))
        FlatButton(drop, "📂  Scegli PDF", self._pick_file, ACCENT,
                   fg=BG, size=10, padx=18, pady=8).pack(side="right")

        if TkinterDnD:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

        # Info file
        info = tk.Frame(self, bg=PANEL, padx=18, pady=12)
        info.pack(fill="x", padx=24)
        self._info_rows = {}
        for label in ("File", "Tipo", "Dimensione", "Lunghezza base64"):
            row = tk.Frame(info, bg=PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", width=18, anchor="w",
                     font=font(9), fg=MUTED, bg=PANEL).pack(side="left")
            val = tk.Label(row, text="—", anchor="w", font=font(9, "bold"), fg=TEXT, bg=PANEL)
            val.pack(side="left")
            self._info_rows[label] = val

        # Opzioni output
        opts = tk.Frame(self, bg=BG)
        opts.pack(fill="x", padx=24, pady=(16, 6))
        tk.Label(opts, text="Nome campo JSON:", font=font(9), fg=MUTED, bg=BG).pack(side="left", padx=(0, 6))
        tk.Entry(opts, textvariable=self.field_var, width=16, font=font(10),
                 bg=PANEL, fg=TEXT, insertbackground=ACCENT, relief="flat", bd=4,
                 highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT
                 ).pack(side="left", padx=(0, 16))
        self.field_var.trace_add("write", lambda *_: self._schedule_refresh())

        for text, var in (("Includi nome file", self.with_name_var),
                          ("Prefisso data URI", self.data_uri_var),
                          ("JSON compatto", self.compact_var)):
            ttk.Checkbutton(opts, text=text, variable=var, style="Dark.TCheckbutton",
                            command=self._refresh_outputs).pack(side="left", padx=(0, 12))

        # Status bar e bottoni vanno "agganciati" in basso PRIMA dell'area di testo,
        # così restano sempre visibili anche con la finestra piccola.
        self.status_label = tk.Label(self, textvariable=self.status_var, font=font(8),
                                     fg=MUTED, bg=BG, anchor="w")
        self.status_label.pack(side="bottom", fill="x", padx=26, pady=(0, 10))

        btns = tk.Frame(self, bg=BG)
        btns.pack(side="bottom", fill="x", padx=24, pady=(0, 8))
        FlatButton(btns, "📋  Copia base64", self._copy_b64,  ACCENT).pack(side="left", padx=(0, 8))
        FlatButton(btns, "📋  Copia JSON",   self._copy_json, ACCENT).pack(side="left", padx=(0, 8))
        FlatButton(btns, "💾  Salva .txt",   self._save_txt,  GREY_BTN).pack(side="left", padx=(0, 8))
        FlatButton(btns, "💾  Salva .json",  self._save_json, GREY_BTN).pack(side="left")
        FlatButton(btns, "✕  Reset",         self._reset,     DARK_BTN).pack(side="right")

        # Tabs: base64 raw | JSON snippet (occupano tutto lo spazio che resta)
        self.tab = ttk.Notebook(self)
        self.tab.pack(fill="both", expand=True, padx=24, pady=(4, 10))
        f1, self.txt_b64  = _make_text(self.tab)
        f2, self.txt_json = _make_text(self.tab)
        self.tab.add(f1, text="Base64 raw")
        self.tab.add(f2, text="JSON snippet")

    def _bind_shortcuts(self):
        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind(f"<{mod}-o>", lambda e: self._pick_file())
        self.bind(f"<{mod}-s>", lambda e: self._save_json())

    # ── Caricamento ──────────────────────────────────────────────────────────

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Seleziona un PDF",
            filetypes=[("PDF", "*.pdf *.PDF"), ("Tutti i file", "*.*")]
        )
        if path:
            self._load_file(path)

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if paths:
            self._load_file(paths[0])
            if len(paths) > 1:
                self._status(f"Hai trascinato {len(paths)} file: carico solo il primo.", WARN)

    def _load_file(self, path):
        if self._busy:
            return
        if not os.path.isfile(path):
            return self._error(f"File non trovato:\n{path}")
        try:
            with open(path, "rb") as f:
                head = f.read(1024)
        except OSError as e:
            return self._error(str(e))

        if not is_pdf(head):
            if not messagebox.askyesno(
                    "File non PDF",
                    f"«{os.path.basename(path)}» non sembra un PDF.\n\nConvertirlo comunque?",
                    parent=self):
                return

        self._busy = True
        self._filename = os.path.basename(path)
        self.drop_label.config(text=self._filename, fg=ACCENT2)
        self._status("Conversione in corso…")
        self.config(cursor="watch")
        threading.Thread(target=self._encode_worker, args=(path,), daemon=True).start()

    def _encode_worker(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            b64 = encode(data)
            self.after(0, self._on_encoded, b64, len(data), is_pdf(data))
        except Exception as e:
            self.after(0, self._on_encode_error, str(e))

    def _on_encode_error(self, msg):
        self._busy = False
        self.config(cursor="")
        self._error(msg)

    def _on_encoded(self, b64, size, pdf_ok):
        self._busy = False
        self.config(cursor="")
        self._data_b64 = b64
        self._info_rows["File"].config(text=self._filename)
        self._info_rows["Tipo"].config(text="PDF ✓" if pdf_ok else "⚠ non sembra un PDF",
                                       fg=ACCENT2 if pdf_ok else WARN)
        self._info_rows["Dimensione"].config(text=human_size(size))
        self._refresh_outputs()
        self._status(f"✔  Conversione completata — {len(self._b64()):,} caratteri base64", ACCENT2)

    # ── Output ───────────────────────────────────────────────────────────────

    def _field(self):
        return self.field_var.get().strip() or DEFAULT_FIELD

    def _b64(self):
        if not self._data_b64:
            return ""
        return DATA_URI_PREFIX + self._data_b64 if self.data_uri_var.get() else self._data_b64

    def _payload_text(self, preview=False):
        b64 = self._b64()
        if preview and len(b64) > PREVIEW_LIMIT:
            b64 = b64[:PREVIEW_LIMIT] + "…"
        payload = build_payload(b64, self._field(), self._filename, self.with_name_var.get())
        return payload_text(payload, self.compact_var.get())

    def _schedule_refresh(self):
        # aspetta che si smetta di scrivere prima di aggiornare l'anteprima
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(250, self._refresh_outputs)

    def _refresh_outputs(self):
        self._refresh_job = None
        if not self._data_b64:
            return
        b64 = self._b64()
        _set_text(self.txt_b64, _preview(b64))
        json_preview = self._payload_text(preview=True)
        if len(b64) > PREVIEW_LIMIT:
            json_preview += (f"\n\n[Anteprima: il valore di \"{self._field()}\" è troncato a video. "
                             "I pulsanti Copia e Salva usano la stringa completa.]")
        _set_text(self.txt_json, json_preview)
        self._info_rows["Lunghezza base64"].config(text=f"{len(b64):,} caratteri")

    # ── Azioni ───────────────────────────────────────────────────────────────

    def _require_file(self):
        if not self._data_b64:
            self._warn("Nessun file caricato.")
            return False
        return True

    def _copy(self, text, what):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()        # su alcuni sistemi gli appunti si perdono senza questo
        self._status(f"✔  {what} copiato negli appunti.", ACCENT2)

    def _copy_b64(self):
        if self._require_file():
            self._copy(self._b64(), "Base64")

    def _copy_json(self):
        if self._require_file():
            self._copy(self._payload_text(), "JSON")

    def _save(self, content, ext, suffix, label):
        if not self._require_file():
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=ext,
            initialfile=f"{os.path.splitext(self._filename)[0]}{suffix}{ext}",
            filetypes=[(label, f"*{ext}")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            return self._error(f"Impossibile salvare il file:\n{e}")
        self._status(f"✔  Salvato: {os.path.basename(path)}", ACCENT2)

    def _save_txt(self):
        self._save(self._b64(), ".txt", "_base64", "File di testo")

    def _save_json(self):
        self._save(self._payload_text(), ".json", "_payload", "File JSON")

    def _reset(self):
        if self._busy:
            return
        self._data_b64 = ""
        self._filename = ""
        self.drop_label.config(text=self._empty_hint(), fg=MUTED)
        for val in self._info_rows.values():
            val.config(text="—", fg=TEXT)
        _set_text(self.txt_b64, "")
        _set_text(self.txt_json, "")
        self._status("Reset effettuato.")

    def _open_decoder(self):
        DecodeWindow(self)

    def _status(self, msg, color=MUTED):
        self.status_var.set(msg)
        self.status_label.config(fg=color)

    def _warn(self, msg):
        messagebox.showwarning("Attenzione", msg, parent=self)

    def _error(self, msg):
        self._status(f"Errore: {msg.splitlines()[0]}", ERROR)
        messagebox.showerror("Errore", msg, parent=self)


if tk is not None:
    class DecodeWindow(tk.Toplevel):
        """Operazione inversa: da base64 (o JSON che lo contiene) a file PDF."""

        def __init__(self, master):
            super().__init__(master)
            self.title("Base64 → PDF")
            self.configure(bg=BG)
            self.minsize(620, 460)
            self.geometry(f"680x520+{master.winfo_x() + 60}+{master.winfo_y() + 60}")
            self._source = None      # testo completo caricato da file/appunti (può essere enorme)

            tk.Label(self, text="Incolla qui la stringa base64, un data URI o un JSON che la contiene.",
                     font=font(9), fg=MUTED, bg=BG, anchor="w").pack(fill="x", padx=20, pady=(16, 8))

            frame, self.txt = _make_text(self)
            frame.pack(fill="both", expand=True, padx=20)
            self.txt.config(state="normal")
            self.txt.focus_set()

            btns = tk.Frame(self, bg=BG)
            btns.pack(fill="x", padx=20, pady=12)
            FlatButton(btns, "📋  Incolla",         self._paste,     GREY_BTN).pack(side="left", padx=(0, 8))
            FlatButton(btns, "📂  Apri .txt/.json", self._open_file, GREY_BTN).pack(side="left", padx=(0, 8))
            FlatButton(btns, "✕  Pulisci",          self._clear,     DARK_BTN).pack(side="left")
            FlatButton(btns, "💾  Salva PDF",       self._save,      ACCENT).pack(side="right")

            self.status = tk.Label(self, text="", font=font(8), fg=MUTED, bg=BG, anchor="w")
            self.status.pack(fill="x", padx=22, pady=(0, 10))

        def _load_source(self, text, origin):
            # testi enormi: a video solo l'anteprima, il contenuto completo resta in memoria
            self._source = text
            _set_text(self.txt, _preview(text))
            self._set_status(f"Caricato da {origin}: {len(text):,} caratteri.")

        def _paste(self):
            try:
                text = self.clipboard_get()
            except tk.TclError:
                return self._set_status("Gli appunti sono vuoti.", WARN)
            self._load_source(text, "appunti")

        def _open_file(self):
            path = filedialog.askopenfilename(
                parent=self, title="Apri file con base64",
                filetypes=[("Testo o JSON", "*.txt *.json"), ("Tutti i file", "*.*")])
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    self._load_source(f.read(), os.path.basename(path))
            except (OSError, UnicodeDecodeError) as e:
                self._set_status(f"Impossibile leggere il file: {e}", ERROR)

        def _clear(self):
            self._source = None
            _set_text(self.txt, "", editable=True)
            self._set_status("")

        def _save(self):
            text = self._source if self._source is not None else self.txt.get("1.0", "end")
            try:
                data, name = decode_input(text, self.master._field())
            except ValueError as e:
                return self._set_status(str(e), ERROR)

            if not is_pdf(data):
                if not messagebox.askyesno("Non è un PDF",
                                           "Il contenuto decodificato non sembra un PDF.\n\nSalvarlo comunque?",
                                           parent=self):
                    return
            path = filedialog.asksaveasfilename(
                parent=self, defaultextension=".pdf",
                initialfile=name or "documento.pdf", filetypes=[("PDF", "*.pdf")])
            if not path:
                return
            try:
                with open(path, "wb") as f:
                    f.write(data)
            except OSError as e:
                return self._set_status(f"Impossibile salvare: {e}", ERROR)
            self._set_status(f"✔  Salvato {os.path.basename(path)} ({human_size(len(data))})", ACCENT2)

        def _set_status(self, msg, color=MUTED):
            self.status.config(text=msg, fg=color)


# ══════════════════════════════════════════════════════════════════════════════

def main(argv=None):
    p = argparse.ArgumentParser(
        prog="PDF2Base64",
        description="Converte un PDF in base64 (o JSON) e viceversa. Senza argomenti apre la finestra.")
    p.add_argument("file", nargs="?", help="PDF da convertire ('-' = standard input)")
    p.add_argument("--gui", action="store_true", help="apre la finestra, con il file già caricato se indicato")
    p.add_argument("--json", action="store_true", help="produce il JSON invece della stringa base64")
    p.add_argument("--field", default=None, help=f"nome del campo JSON (predefinito: {DEFAULT_FIELD})")
    p.add_argument("--no-filename", action="store_true", help="non aggiunge _filename al JSON")
    p.add_argument("--data-uri", action="store_true", help="aggiunge il prefisso data:application/pdf;base64,")
    p.add_argument("--compact", action="store_true", help="JSON su una riga sola")
    p.add_argument("--decode", metavar="INPUT",
                   help="operazione inversa: da base64/JSON (file o '-') a PDF")
    p.add_argument("-o", "--output", help="file di destinazione (predefinito: standard output)")
    args = p.parse_args(argv)

    if args.gui or (not args.file and not args.decode):
        if tk is None:
            print("Tkinter non è disponibile: usa la riga di comando (vedi --help).", file=sys.stderr)
            return 1
        PDFBase64Tool(initial_file=args.file).mainloop()
        return 0
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
