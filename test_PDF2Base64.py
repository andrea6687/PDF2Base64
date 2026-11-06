"""Test della logica di PDF2Base64 (non serve Tkinter).  Avvio: python -m unittest -v"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest

import PDF2Base64 as p

PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDF2Base64.py")


class TestLogic(unittest.TestCase):
    def test_is_pdf(self):
        self.assertTrue(p.is_pdf(PDF))
        self.assertTrue(p.is_pdf(b"\x00" * 100 + PDF))     # intestazione non all'inizio
        self.assertFalse(p.is_pdf(b"PK\x03\x04 zip"))

    def test_encode(self):
        self.assertEqual(p.encode(PDF), base64.b64encode(PDF).decode())
        self.assertTrue(p.encode(PDF, data_uri=True).startswith("data:application/pdf;base64,JVBER"))

    def test_payload(self):
        self.assertEqual(p.build_payload("X", "doc", "a.pdf"), {"doc": "X", "_filename": "a.pdf"})
        self.assertEqual(p.build_payload("X", "", "a.pdf", False), {"allegato": "X"})
        self.assertEqual(p.payload_text({"a": "b"}, compact=True), '{"a":"b"}')

    def test_human_size(self):
        self.assertEqual(p.human_size(500), "500 byte")
        self.assertEqual(p.human_size(2048), "2.0 KB")
        self.assertEqual(p.human_size(5 * 1024 * 1024), "5.0 MB")

    def test_decode_variants(self):
        b64 = base64.b64encode(PDF).decode()
        cases = [
            b64,
            "  " + b64[:20] + "\n" + b64[20:] + "\n",              # con a capo
            "data:application/pdf;base64," + b64,                   # data URI
            b64.rstrip("="),                                        # senza padding
            base64.urlsafe_b64encode(PDF).decode(),                 # url-safe
            f'"{b64}"',                                             # tra virgolette
        ]
        for c in cases:
            data, _ = p.decode_input(c)
            self.assertEqual(data, PDF)

    def test_decode_json(self):
        b64 = base64.b64encode(PDF).decode()
        data, name = p.decode_input(json.dumps({"allegato": b64, "_filename": "fattura.pdf"}))
        self.assertEqual((data, name), (PDF, "fattura.pdf"))
        # campo annidato e campo scelto per nome
        nested = {"meta": {"id": "abc"}, "files": [{"name": "x.pdf", "content": b64}]}
        data, name = p.decode_input(json.dumps(nested), field="content")
        self.assertEqual((data, name), (PDF, "x.pdf"))

    def test_decode_errors(self):
        for bad in ("", "   ", "non è base64 !!!", "{rotto", "{}"):
            with self.assertRaises(ValueError):
                p.decode_input(bad)


class TestCLI(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, SCRIPT, *args], input=stdin,
                              capture_output=True, timeout=30)

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "doc.pdf")
            js = os.path.join(d, "out.json")
            back = os.path.join(d, "back.pdf")
            with open(src, "wb") as f:
                f.write(PDF)

            r = self.run_cli(src)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.decode().strip(), base64.b64encode(PDF).decode())

            r = self.run_cli(src, "--json", "--field", "file", "--compact", "-o", js)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(js) as f:
                self.assertEqual(json.load(f), {"file": base64.b64encode(PDF).decode(),
                                                "_filename": "doc.pdf"})

            r = self.run_cli("--decode", js, "-o", back)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(back, "rb") as f:
                self.assertEqual(f.read(), PDF)

    def test_errors(self):
        r = self.run_cli("non-esiste.pdf")
        self.assertEqual(r.returncode, 1)
        self.assertIn(b"Errore", r.stderr)
        r = self.run_cli("--decode", "-", "-o", os.devnull, stdin=b"$$$ non valido")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
