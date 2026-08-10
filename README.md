# Notes Generator — Portfolio Skills → PDF Study Notes

This repo has a single automatic flow: run one script to scrape the portfolio into `portfolio_data.json`, then generate one note per scraped skill, immediately convert that note to PDF, and move on to the next skill.

## Prerequisites

- Python 3.11 or newer
- Windows PowerShell, or macOS/Linux terminal
- A local OpenAI-compatible server such as `freellmapi`
- Chromium installed for Playwright after the Python packages are installed

## Quickstart

Full setup commands are in [doc/local-guide.md](doc/local-guide.md).

The short version is:

1. Create and activate a virtual environment.
2. Run `pip install -r requirements.txt`.
3. Run `playwright install chromium`.
4. Copy `.env.example` to `.env` and fill in the values.
5. Start your local OpenAI-compatible server and point `LLM_BASE_URL` at it.
6. Run `python run_all.py`.

Expected outputs:

- `portfolio_data.json`
- `output/md/<topic-slug>.md`
- `output/pdf/<topic-slug>.pdf`

## Project Layout

```text
run_all.py             # Full automated pipeline
portfolio_scraper.py   # Scrapes the portfolio site and caches JSON
generate_notes.py      # Main notes pipeline
convert_to_pdf.py      # Markdown to PDF conversion
search_client.py       # Optional DuckDuckGo context fetch
llm_client.py          # OpenAI-compatible client wrapper
config.py              # Environment and pipeline settings
prompts/templates.py   # Prompt templates for each generation stage
templates/notes_style.css   # legacy reference stylesheet; PDF styling is implemented in convert_to_pdf.py
output/md/
output/pdf/
```

## Project structure

```
notes-generator/
├── config.py              # topics, portfolio list, LLM + search settings
├── llm_client.py          # OpenAI-compatible client + retry logic
├── generate_notes.py      # main pipeline: 5-stage prompt loop
├── search_client.py       # DuckDuckGo search context (ddgs)
├── convert_to_pdf.py      # md -> styled PDF
├── prompts/
│   └── templates.py       # the 5 chained prompts (search/theory/ascii/portfolio/merge)
├── templates/
│   └── notes_style.css    # PDF styling (headers, code blocks, etc.)
├── .venv/                 # virtual environment (gitignored)
└── output/
    ├── md/
    └── pdf/
```

## Troubleshooting

- **Connection refused**: local server isn't running, or wrong port in
  `config.py` / `LLM_BASE_URL`.
- **Empty/garbage responses**: try a different `LLM_MODEL` name — some
  local proxies are picky about exact model strings.
- **Search errors in the log**: `ddgs` not installed or network blocked —
  the pipeline continues without search context, or set
  `ENABLE_SEARCH_CONTEXT=false`.
- **ASCII diagrams look broken in PDF**: don't edit `notes_style.css`'s
  `pre` block — `white-space: pre` is required to preserve alignment.
- **Rate limits / slow**: 6 calls per topic (5 LLM + 1 optional search);
  for many topics, consider adding a `time.sleep()` between topics in
  `generate_notes.py`'s main loop.
