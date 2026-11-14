# Contributing

🇮🇹 Italiano più sotto.

Thanks for helping! Bug reports are the most useful contribution: the window is Tkinter, and macOS, Windows and Linux don't draw it the same way.

## Reporting a bug

Open an [issue](https://github.com/andrea6687/PDF2Base64/issues/new/choose) with the bug template and include:

- your system (macOS, Windows or Linux) and the Python version (`python --version`);
- whether you used the window or the command line, and the exact command if you used one;
- what you expected and what happened;
- a screenshot, if you can.

Before posting, remove anything private. The Base64 string is the PDF: don't paste a real document, a real JSON payload, or a screenshot that shows one.

## Suggesting an idea

Open an issue with the idea template and explain the problem you want to solve, not only the solution.

## Sending code

1. Open an issue first for anything bigger than a small fix, so we can agree on the approach.
2. Keep the conversion usable without the window. The tests import `PDF2Base64.py` and never open it.
3. Add or update a test in `test_PDF2Base64.py` for every behavior you change, and run `python -m unittest -v`.
4. If you change the window, try it on a real desktop too and say in the pull request what you tested.
5. PDF2Base64 stays on the computer: no network requests, and no new package that the program requires. `tkinterdnd2` stays optional.
6. Interface text is in Italian. Keep it short and plain.
7. Update both READMEs (`README.md` and `README.it.md`) if the behavior changes.

## Scope

In scope: turning a PDF you already have into Base64 or JSON, and turning that text back into a PDF, on your computer.
Out of scope: uploading files, adding a server, editing the PDF, or hiding a file inside the encoding.

---

## Italiano

Grazie per l'aiuto! Le segnalazioni di problemi sono il contributo più utile: la finestra è Tkinter, e macOS, Windows e Linux non la disegnano allo stesso modo.

- **Problema:** apri una [issue](https://github.com/andrea6687/PDF2Base64/issues/new/choose) con il modello "bug" indicando sistema, versione di Python, se usi la finestra o la riga di comando, il comando esatto se ne hai usato uno, cosa ti aspettavi e cosa è successo. La stringa Base64 è il PDF: non incollare un documento vero, un JSON vero o uno screenshot che li mostri.
- **Idea:** apri una issue con il modello "idea" e spiega il problema da risolvere.
- **Codice:** per modifiche non piccole apri prima una issue. La conversione deve restare usabile senza finestra: i test importano `PDF2Base64.py` e non la aprono. Aggiungi un test in `test_PDF2Base64.py` per ogni comportamento che cambi ed esegui `python -m unittest -v`. Se tocchi la finestra, provala anche su un desktop vero. Niente richieste di rete e nessun pacchetto nuovo obbligatorio (`tkinterdnd2` resta facoltativo). I testi dell'interfaccia restano in italiano, corti e chiari. Aggiorna entrambi i README se cambia il comportamento.
- **Fuori tema:** caricare file, aggiungere un server, modificare il PDF, nascondere un file dentro la codifica.
