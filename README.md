# Notes Generator — Portfolio Skills → PDF Study Notes

Generates beginner→advanced study notes (theory + ASCII architecture
diagrams + portfolio relevance + interview Q&A) per skill, using a
5-stage chained-prompt loop against your local OpenAI-compatible
freellmapi server, then converts to styled PDFs.

A DuckDuckGo search pass (`search_client.py`) pulls recent context before
the theory stage, so notes reflect current versions and best practices
instead of only the LLM's training data.

## 1. Set up the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell (Windows)
# or: source .venv/bin/activate # macOS / Linux
```

## 2. Install dependencies

```bash
pip install openai markdown weasyprint ddgs
```

`weasyprint` needs system libraries for font/CSS rendering:
- **Windows**: see https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
- **Mac**: `brew install pango`
- **Linux**: `sudo apt install libpango-1.0-0 libpangocairo-1.0-0`

If weasyprint gives you trouble, alternative: `pip install pdfkit` +
install `wkhtmltopdf` binary, and swap `convert_to_pdf.py`'s HTML(...)
call for pdfkit — ask me if you want that version instead.

`ddgs` is the DuckDuckGo search package for the optional search-context
pass. If you don't want the extra network calls, set
`ENABLE_SEARCH_CONTEXT=false` in `config.py` and skip installing it.

## 3. Confirm your freellmapi server is running

```bash
curl http://localhost:3001/v1/models
```

Should return a model list. If not, start your local freellmapi server first.

## 4. Configure

Edit `config.py`:
- `LLM_MODEL` — set to whatever model name your local proxy expects
- `TOPICS` — add your skills (uncomment/add lines). Start with 1-2 to
  confirm quality before scaling to your full portfolio list.
- `PORTFOLIO_PROJECTS` — optional: add your real portfolio projects
  (name, description, stack) so each topic gets a "Where I've Used This"
  section tied to projects that genuinely use it.
- `ENABLE_SEARCH_CONTEXT` — set to `false` to skip the DuckDuckGo pass.

## 5. Generate notes

```bash
python generate_notes.py                # runs everything in TOPICS
python generate_notes.py "Docker"        # or just one topic ad-hoc
```

Markdown files land in `output/md/<topic-slug>.md`.

## 6. Convert to PDF

```bash
python convert_to_pdf.py                 # converts all .md files
python convert_to_pdf.py reactjs.md       # or just one
```

Styled PDFs land in `output/pdf/`.

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

## Why chained LLM calls instead of 1 big prompt?

Loop-engineering: chaining focused prompts (search context → theory →
diagrams → portfolio relevance → Q&A → merge) gets more reliable depth
per section than one mega-prompt, which tends to shortchange the ASCII
diagrams and interview questions to save room. The search pass keeps
version numbers and best practices current; the portfolio pass
personalizes the notes to your actual projects; the merge pass stitches
everything into one polished doc.

## Next step: Phase 2 — auto-extract skills from portfolio

Once this pipeline is confirmed on a few manual topics, we can add a
scraper (Playwright/Selenium, since your portfolio is a React SPA and
needs JS rendering) that pulls your skills list automatically and feeds
it into `TOPICS`. Say the word when you're ready for that piece.

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
