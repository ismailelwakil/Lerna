# GitHub upload fix (nothing in the app was deleted)

## What was wrong

GitHub **web “upload folder”** blocks any file **> 25 MB**.

This file is ~44 MB:

`ai-service/data/chroma/chroma.sqlite3`

That is a **runtime vector database**, not source code. It caused the upload to fail.

## What we changed

- **Did not delete** your Chroma files, profiles, or code on disk.
- **Stopped git from uploading** the large DB via `.gitignore`.
- Kept empty folders with `.gitkeep` so Railway still has `data/chroma`, `data/chromadb`, `data/uploads`, `data/artifacts`.
- Chroma is created again on first API use (or from a Railway volume).

Student demo profile **`ai-service/data/profiles/student-001.json` is still in the repo.**

## How to put it on GitHub (required for Railway)

Do **not** drag the folder into github.com.

In a terminal:

```bash
cd LeRna
git init
git add .
git commit -m "LeRna ready for Railway"
git branch -M main
git remote add origin https://github.com/Malak-0sama/LeRna.git
git push -u origin main --force
```

Only use `--force` if this is your repo and you are OK replacing the old “Initial commit” that contained the huge sqlite file.

Then deploy on Railway as in `HOW_TO_DEPLOY.md`.
