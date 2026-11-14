# Security Policy

🇮🇹 Italiano più sotto.

## Reporting a vulnerability

Please **don't open a public issue** for security problems.

Use GitHub's private reporting instead: go to the [Security tab](https://github.com/andrea6687/PDF2Base64/security) and choose **Report a vulnerability**. You'll get an answer as soon as possible, usually within a week.

Examples of what to report:

- a PDF, a JSON body or a Base64 string that makes PDF2Base64 write somewhere other than the file you chose, or run code;
- anything that sends the file contents off the computer. The program makes no network requests;
- a hang or a crash on a file you were asked to open, when it can lock the window or the terminal.

The Base64 text is the document itself. Don't attach a private PDF, payload or screenshot to the report.

## Supported versions

Only the latest version on the `main` branch is supported.

## What PDF2Base64 does and doesn't do

- It makes no network requests and has no server.
- It reads the file you pick and writes only to the path you choose, or to the terminal.
- You can read the full code in [`PDF2Base64.py`](PDF2Base64.py) before running it. There is no installer and no downloaded script.

---

## Italiano

Per i problemi di sicurezza **non aprire una issue pubblica**: usa la [scheda Security](https://github.com/andrea6687/PDF2Base64/security) → **Report a vulnerability**, che è privata.

È supportata solo l'ultima versione su `main`. PDF2Base64 non fa richieste di rete, non ha un server e scrive solo nel file che scegli tu o nel terminale. Il codice completo è in [`PDF2Base64.py`](PDF2Base64.py): puoi leggerlo prima di eseguirlo. Non allegare un PDF, un payload o uno screenshot privati: il testo Base64 è il documento.
