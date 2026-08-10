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

`generate_notes.py` reads the `skills` list from `portfolio_data.json` and writes one markdown file per skill automatically.

`run_all.py` converts each markdown file to PDF immediately after it is generated, before moving to the next skill.

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