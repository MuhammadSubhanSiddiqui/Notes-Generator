# Notes Generator — Portfolio Skills → PDF Study Notes

This repo has a single automatic flow: run one script to scrape the
portfolio into `portfolio_data.json`, then generate one note per scraped
skill, immediately convert that note to PDF, and move on to the next
skill. A topic is regenerated only if its note doesn't exist yet, or the
portfolio content relevant to that specific skill has changed since it
was last generated — unrelated portfolio edits don't trigger a
regeneration. Pass `--force` to regenerate everything regardless.

## Prerequisites

- Python 3.11 or newer
- Windows PowerShell, or macOS/Linux terminal
- A local OpenAI-compatible server (e.g. `freellmapi`, LM Studio, Ollama's
  OpenAI-compat endpoint, vLLM). The prompts in `prompts/templates.py`
  are written to be model-agnostic — no hardcoded word/question-count
  targets that would bias output toward whatever one model was tuned
  against — so any reasonably capable instruct model should work.
- Chromium installed for Playwright after the Python packages are installed

## Quickstart

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

## Usage

```bash
python run_all.py              # scrape + generate + convert what's stale
python run_all.py --force      # regenerate everything, even up-to-date notes

python generate_notes.py                    # generate what's stale (no scrape/PDF)
python generate_notes.py "React.js"         # ad-hoc: one topic, ignoring scraped skill list
python generate_notes.py --force            # regenerate all scraped topics regardless

python convert_to_pdf.py                    # convert every output/md/*.md to PDF
python convert_to_pdf.py react-js.md        # convert just one file

python portfolio_scraper.py                 # scrape only, refresh portfolio_data.json
python portfolio_scraper.py --headed        # scrape with a visible browser (debugging)
```

### How staleness is decided

Each generated note's dependency on the portfolio is tracked in
`output/md/.note_state.json` (slug → portfolio hash). A topic is
regenerated when:

- its `output/md/<slug>.md` doesn't exist yet, or
- the note exists but has no entry in `.note_state.json` (e.g. it
  predates this tracking — it's treated as stale once, to establish a
  baseline), or
- the portfolio content *relevant to that topic* — any scraped project
  or experience entry whose name, description, stack, or highlights
  mention the topic — has changed since the note was last generated.

Editing a project unrelated to a given skill does not mark that skill's
note stale. `--force` bypasses all of this and regenerates every queued
topic unconditionally.

## Project Layout

```text
notes-generator/
├── config.py              # LLM/search settings, portfolio fallback list, PDF themes
├── llm_client.py          # OpenAI-compatible client + retry logic
├── generate_notes.py      # main pipeline: chained prompt calls per topic
├── run_all.py             # scrape -> generate -> convert, end to end
├── search_client.py       # optional DuckDuckGo search context (ddgs)
├── portfolio_scraper.py   # Playwright scraper for the portfolio site
├── convert_to_pdf.py      # markdown -> styled PDF
├── prompts/
│   └── templates.py       # the chained prompt templates
├── .env.example            # copy to .env and fill in
├── portfolio_data.json     # scraper output (gitignored, generated)
└── output/
    ├── md/                 # generated notes, one .md per topic
    └── pdf/                # converted PDFs
```

## What each note contains

Per topic, `generate_notes.py` chains these calls:

1. Fundamentals & mental model (uses search context if enabled)
2. Internals & real-world patterns (uses search context if enabled)
3. ASCII architecture diagrams
4. Common pitfalls & debugging
5. Quick reference cheat sheet
6. Portfolio relevance — matches the topic against your real scraped
   projects/experience; says so plainly if nothing matches
7. Interview questions (beginner/intermediate/advanced/scenario)

Sections are stitched together directly (no extra LLM "merge" pass) to
avoid a merge call silently truncating or dropping a section.

## Troubleshooting

- **Connection refused**: local server isn't running, or wrong port in
  `.env` / `LLM_BASE_URL`.
- **Empty/garbage responses**: try a different `LLM_MODEL` name — some
  local proxies are picky about exact model strings. `LLM_MODEL_CANDIDATES`
  in `.env` lets you list fallbacks to try in order.
- **Search errors in the log**: `ddgs` not installed or network blocked —
  the pipeline continues without search context, or set
  `ENABLE_SEARCH_CONTEXT=false`.
- **ASCII diagrams look broken in PDF**: the converter scales code blocks
  automatically, so if a diagram looks clipped, widen the ASCII box or
  shorten the line length.
- **Scraper says "Skills/Projects/Experience section not found" or
  extracted 0 of something**: the scraper reads `<section>` elements by
  fixed position (`SKILLS_SECTION_INDEX`, `PROJECT_SECTION_INDEX`,
  `EXPERIENCE_SECTION_INDEX` in `portfolio_scraper.py`), since the site is
  a client-rendered SPA and matching by heading text requires the browser
  to actually finish hydrating first, which is fragile to get right
  without watching it render. If the homepage's section order changes,
  update those three constants to match. Run with `--headed` to watch it
  load and count sections manually if you're not sure.
- **A topic won't regenerate but you think the portfolio changed**: check
  that the change actually touches that topic (see "How staleness is
  decided" above) — an edit to an unrelated project won't trigger it.
  To force it anyway: delete `output/md/<slug>.md`, delete its entry in
  `output/md/.note_state.json`, or just pass `--force`.
- **Rate limits / slow**: 6 LLM calls + up to 2 search calls per topic;
  for many topics, consider adding a `time.sleep()` between topics in
  `generate_notes.py`'s main loop.
