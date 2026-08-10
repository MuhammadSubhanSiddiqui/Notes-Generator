# File Map

The filename is kept as `files..md` for compatibility with the existing tree.

## Core Files

- `portfolio_scraper.py` - Scrapes the portfolio site and writes `portfolio_data.json`.
- `generate_notes.py` - Runs the multi-stage prompt pipeline and writes Markdown notes.
- `convert_to_pdf.py` - Turns Markdown notes into styled PDFs.
- `llm_client.py` - Talks to the local OpenAI-compatible server.
- `search_client.py` - Adds optional DuckDuckGo context.
- `config.py` - Central settings and environment variable reads.

## Prompt and Style Assets

- `prompts/templates.py` - Prompt templates for the generation stages.
- `convert_to_pdf.py` - PDF styling and rendering live here.

## Output Directories

- `output/md/` - Generated Markdown.
- `output/pdf/` - Final PDFs.

## Setup Files

- `.env.example` - Template for local environment values.
- `requirements.txt` - Python dependencies for a fresh install.
- `.gitignore` - Keeps secrets and generated output out of version control.