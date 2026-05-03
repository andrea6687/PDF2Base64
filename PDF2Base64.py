"""
PDF → Base64 Converter
Carica un PDF e ottieni la stringa base64 pronta per JSON.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import base64
import os
import json
import threading


# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0f1117"
PANEL    = "#1a1d27"
BORDER   = "#2a2d3a"
ACCENT   = "#5b8dee"
ACCENT2  = "#3ecf8e"
TEXT     = "#e8eaf0"
MUTED    = "#6b7089"
ERROR    = "#f06a6a"
MONO     = ("Courier New", 10)
SANS     = ("Segoe UI", 10)


class PDFBase64Tool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → Base64 | ISA Digital")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(700, 560)

        self._b64_string = ""
        self._filename   = ""

        self._build_ui()
        self._center_window(740, 620)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=PANEL, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⬡  PDF → Base64", font=("Courier New", 15, "bold"),
                 fg=ACCENT, bg=PANEL).pack(side="left", padx=24)
        tk.Label(hdr, text="encoder per payload JSON",
                 font=("Segoe UI", 9), fg=MUTED, bg=PANEL).pack(side="left")

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        # Drop zone + pulsante
        drop_frame = tk.Frame(self, bg=BG, pady=20)
        drop_frame.pack(fill="x", padx=24)

        self.drop_label = tk.Label(
            drop_frame,
            text="Nessun file selezionato",
            font=("Segoe UI", 9), fg=MUTED, bg=BG
        )
        self.drop_label.pack(side="left", padx=(0, 12))

        btn_open = tk.Button(
            drop_frame, text="📂  Scegli PDF",
            font=("Segoe UI", 10, "bold"),
            fg=BG, bg=ACCENT, activebackground="#7aabff",
            relief="flat", cursor="hand2", padx=18, pady=8,
            command=self._pick_file
        )
        btn_open.pack(side="right")

        # Info file
        self.info_frame = tk.Frame(self, bg=PANEL, padx=18, pady=12)
        self.info_frame.pack(fill="x", padx=24)

        self._info_rows = {}
        for label in ("File", "Dimensione", "Lunghezza base64", "Campo JSON"):
            row = tk.Frame(self.info_frame, bg=PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", width=18, anchor="w",
                     font=("Segoe UI", 9), fg=MUTED, bg=PANEL).pack(side="left")
            val = tk.Label(row, text="—", anchor="w",
                           font=("Segoe UI", 9, "bold"), fg=TEXT, bg=PANEL)
            val.pack(side="left")
            self._info_rows[label] = val

        sep2 = tk.Frame(self, bg=BORDER, height=1)
        sep2.pack(fill="x", padx=24, pady=(16, 0))

        # Area output
        out_hdr = tk.Frame(self, bg=BG)
        out_hdr.pack(fill="x", padx=24, pady=(14, 4))
        tk.Label(out_hdr, text="Output  ·  stringa base64",
                 font=("Segoe UI", 9, "bold"), fg=ACCENT2, bg=BG).pack(side="left")

        # Opzione campo JSON
        opt_frame = tk.Frame(out_hdr, bg=BG)
        opt_frame.pack(side="right")
        tk.Label(opt_frame, text="Nome campo JSON:",
                 font=("Segoe UI", 9), fg=MUTED, bg=BG).pack(side="left", padx=(0, 6))
        self.field_var = tk.StringVar(value="allegato")
        field_entry = tk.Entry(opt_frame, textvariable=self.field_var,
                               width=16, font=SANS,
                               bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                               relief="flat", bd=0)
        field_entry.pack(side="left")
        field_entry.bind("<KeyRelease>", lambda e: self._refresh_json_preview())

        # Tabs: base64 raw | JSON snippet
        self.tab = ttk.Notebook(self)
        self.tab.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=[14, 6], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", BORDER)],
                  foreground=[("selected", TEXT)])

        self.txt_b64  = self._make_tab("Base64 raw")
        self.txt_json = self._make_tab("JSON snippet")

        # Bottoni azione
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        self._make_btn(btn_frame, "📋  Copia base64",   ACCENT,  self._copy_b64).pack(side="left", padx=(0, 8))
        self._make_btn(btn_frame, "📋  Copia JSON",      ACCENT,  self._copy_json).pack(side="left", padx=(0, 8))
        self._make_btn(btn_frame, "💾  Salva .txt",      "#4a4e6a", self._save_txt).pack(side="left", padx=(0, 8))
        self._make_btn(btn_frame, "💾  Salva .json",     "#4a4e6a", self._save_json).pack(side="left")
        self._make_btn(btn_frame, "✕  Reset",            "#3a3d50", self._reset).pack(side="right")

        # Status bar
        self.status_var = tk.StringVar(value="Pronto.")
        tk.Label(self, textvariable=self.status_var,
                 font=("Segoe UI", 8), fg=MUTED, bg=BG,
                 anchor="w").pack(fill="x", padx=26, pady=(0, 8))

    def _make_tab(self, title):
        frame = tk.Frame(self.tab, bg=BG)
        self.tab.add(frame, text=title)
        scrollbar = tk.Scrollbar(frame, bg=PANEL, troughcolor=BG,
                                 activebackground=ACCENT, relief="flat")
        scrollbar.pack(side="right", fill="y")
        txt = tk.Text(frame, wrap="none", font=MONO,
                      bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                      selectbackground=ACCENT, selectforeground=BG,
                      relief="flat", bd=0, padx=12, pady=10,
                      yscrollcommand=scrollbar.set, state="disabled")
        txt.pack(fill="both", expand=True)
        scrollbar.config(command=txt.yview)

        # Horizontal scrollbar
        hscroll = tk.Scrollbar(frame, orient="horizontal", bg=PANEL,
                               troughcolor=BG, relief="flat")
        hscroll.pack(side="bottom", fill="x")
        txt.config(xscrollcommand=hscroll.set)
        hscroll.config(command=txt.xview)
        return txt

    def _make_btn(self, parent, text, color, cmd):
        return tk.Button(parent, text=text, font=("Segoe UI", 9, "bold"),
                         fg=TEXT, bg=color, activebackground=ACCENT,
                         relief="flat", cursor="hand2", padx=14, pady=7,
                         command=cmd)

    # ── Core logic ───────────────────────────────────────────────────────────

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Seleziona un PDF",
            filetypes=[("PDF files", "*.pdf"), ("Tutti i file", "*.*")]
        )
        if not path:
            return
        self._filename = os.path.basename(path)
        self.drop_label.config(text=self._filename, fg=ACCENT2)
        self._status("Conversione in corso…")
        threading.Thread(target=self._encode, args=(path,), daemon=True).start()

    def _encode(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            size_kb = len(data) / 1024
            b64_len  = len(b64)
            self.after(0, self._update_ui, b64, size_kb, b64_len)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _update_ui(self, b64: str, size_kb: float, b64_len: int):
        self._b64_string = b64
        field = self.field_var.get() or "allegato"

        self._info_rows["File"].config(text=self._filename)
        self._info_rows["Dimensione"].config(
            text=f"{size_kb:.1f} KB  ({int(size_kb*1024):,} byte)")
        self._info_rows["Lunghezza base64"].config(text=f"{b64_len:,} caratteri")
        self._info_rows["Campo JSON"].config(text=f'"{field}"')

        self._set_text(self.txt_b64, b64)
        self._refresh_json_preview()
        self._status(f"✔  Conversione completata — {b64_len:,} caratteri base64")

    def _refresh_json_preview(self):
        if not self._b64_string:
            return
        field = self.field_var.get() or "allegato"
        snippet = json.dumps(
            {field: self._b64_string, "_filename": self._filename},
            ensure_ascii=False, indent=2
        )
        self._set_text(self.txt_json, snippet)
        self._info_rows["Campo JSON"].config(text=f'"{field}"')

    def _set_text(self, widget, content):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.config(state="disabled")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _copy_b64(self):
        if not self._b64_string:
            return self._warn("Nessun file caricato.")
        self.clipboard_clear()
        self.clipboard_append(self._b64_string)
        self._status("✔  Base64 copiato negli appunti.")

    def _copy_json(self):
        if not self._b64_string:
            return self._warn("Nessun file caricato.")
        field = self.field_var.get() or "allegato"
        snippet = json.dumps(
            {field: self._b64_string, "_filename": self._filename},
            ensure_ascii=False, indent=2
        )
        self.clipboard_clear()
        self.clipboard_append(snippet)
        self._status("✔  JSON snippet copiato negli appunti.")

    def _save_txt(self):
        if not self._b64_string:
            return self._warn("Nessun file caricato.")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"{os.path.splitext(self._filename)[0]}_base64.txt",
            filetypes=[("Text file", "*.txt")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._b64_string)
            self._status(f"✔  Salvato: {os.path.basename(path)}")

    def _save_json(self):
        if not self._b64_string:
            return self._warn("Nessun file caricato.")
        field = self.field_var.get() or "allegato"
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"{os.path.splitext(self._filename)[0]}_payload.json",
            filetypes=[("JSON file", "*.json")]
        )
        if path:
            payload = {field: self._b64_string, "_filename": self._filename}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._status(f"✔  Salvato: {os.path.basename(path)}")

    def _reset(self):
        self._b64_string = ""
        self._filename   = ""
        self.drop_label.config(text="Nessun file selezionato", fg=MUTED)
        for key in self._info_rows:
            self._info_rows[key].config(text="—")
        self._set_text(self.txt_b64, "")
        self._set_text(self.txt_json, "")
        self._status("Reset effettuato.")

    def _status(self, msg):
        self.status_var.set(msg)

    def _warn(self, msg):
        messagebox.showwarning("Attenzione", msg)

    def _error(self, msg):
        self.status_var.set(f"Errore: {msg}")
        messagebox.showerror("Errore", msg)


if __name__ == "__main__":
    app = PDFBase64Tool()
    app.mainloop()