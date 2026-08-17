# Local Guide

## Windows PowerShell

```powershell
git clone <repo-url>
cd Notes
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
notepad .env
```

## macOS / Linux

```bash
git clone <repo-url>
cd Notes
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
nano .env
```

## Configure `.env`

```text
LLM_BASE_URL=http://localhost:3001/v1
LLM_API_KEY=replace-me
LLM_MODEL=replace-with-your-model-name
LLM_MODEL_CANDIDATES=
ENABLE_SEARCH_CONTEXT=true
```

If your freellmapi instance exposes many models, set `LLM_MODEL_CANDIDATES` to a comma-separated preference order. The app will try each model before failing the topic.

## Start the local model server

```powershell
freellmapi serve --port 3001
```

```bash
freellmapi serve --port 3001
```

## Run the pipeline automatically

```powershell
python run_all.py
```

```text
portfolio_data.json -> output/md/<topic-slug>.md -> output/pdf/<topic-slug>.pdf
```

`run_all.py` scrapes the portfolio, then generates notes and converts to PDF for each skill sequentially. Topics whose relevant portfolio content hasn't changed since last generation are skipped (use `--force` to override).

## One-topic run (no scrape / no PDF)

```powershell
python generate_notes.py "React.js"
```

```bash
python3 generate_notes.py "React.js"
```

## One-topic with PDF

```powershell
python run_all.py --force "React.js"
```

```bash
python3 run_all.py --force "React.js"
```

## Generate notes only (no scrape / no PDF)

```powershell
python generate_notes.py           # all scraped skills, skipped if up to date
python generate_notes.py --force   # all scraped skills, force regenerate
python generate_notes.py "Python"  # single ad-hoc topic
```

## Convert to PDF only

```powershell
python convert_to_pdf.py                    # all markdown files
python convert_to_pdf.py python.md          # single file
```

## Scrape only

```powershell
python portfolio_scraper.py                 # headless (default)
python portfolio_scraper.py --headed        # visible browser for debugging
```

## Notes

```text
If your server uses a different command or port, keep the same /v1 base URL in LLM_BASE_URL.
If Chromium is already installed globally, `playwright install chromium` is still safe to run.
The pipeline uses thread-pooled parallel LLM calls (5 workers) for ~3x speedup per topic.
Staleness is tracked per-topic via portfolio content hashes in output/md/.note_state.json
```