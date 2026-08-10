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
ENABLE_SEARCH_CONTEXT=true
```

## Start the local model server

```powershell
freellmapi serve --port 3001
```

```bash
freellmapi serve --port 3001
```

## Run the pipeline in order

```powershell
python portfolio_scraper.py
```

```text
portfolio_data.json
```

```powershell
python generate_notes.py
```

```text
output/md/<topic-slug>.md
```

```powershell
python convert_to_pdf.py
```

```text
output/pdf/<topic-slug>.pdf
```

## One-topic run

```powershell
python generate_notes.py "React.js"
```

```bash
python3 generate_notes.py "React.js"
```

## Notes

```text
If your server uses a different command or port, keep the same /v1 base URL in LLM_BASE_URL.
If Chromium is already installed globally, `playwright install chromium` is still safe to run.
```