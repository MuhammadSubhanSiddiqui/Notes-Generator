# File Map

The filename is kept as `files..md` for compatibility with the existing tree.

## Core Files

- `config.py` - Central settings, environment variable reads, model discovery, topic themes, output paths.
- `portfolio_scraper.py` - Scrapes the portfolio site (Playwright, fixed section indices) and writes `portfolio_data.json`.
- `generate_notes.py` - Runs the multi-stage prompt pipeline with thread-pooled parallel LLM calls; writes Markdown notes.
- `convert_to_pdf.py` - Turns Markdown notes into styled PDFs with per-topic themes, adaptive code sizing, cover pages.
- `llm_client.py` - Talks to the local OpenAI-compatible server; handles retries and model candidate fallback.
- `search_client.py` - Adds optional DuckDuckGo context (lazy import, safe if `ddgs` not installed).
- `run_all.py` - Orchestrates end-to-end: scrape → generate + convert per topic (sequential, skips stale).
- `prompts/templates.py` - Prompt templates for the 7 generation stages.

## Prompt Stages (templates.py)

1. `STAGE_1A_FUNDAMENTALS` - Core motivation, mental model, essential theory, primitives, realistic example.
2. `STAGE_1B_DEEP_DIVE` - Internals, architectural patterns, production failure modes.
3. `STAGE_2_ASCII_ARCHITECTURE` - 5-8 ASCII diagrams for core mechanics.
4. `STAGE_2_5_PORTFOLIO_RELEVANCE` - Match topic against scraped projects/experience.
5. `STAGE_2_7_PITFALLS` - Common pitfalls, why they happen, short fixes.
6. `STAGE_2_8_CHEATSHEET` - Dense quick-reference: bullets, mini tables, grouped lists.
7. `STAGE_3_INTERVIEW_QUESTIONS` - Beginner/Intermediate/Advanced/Scenario with Q&A.

## Output Directories

- `output/md/` - Generated Markdown notes (one per topic).
- `output/pdf/` - Final PDFs.
- `output/md/.note_state.json` - Per-topic portfolio hashes for staleness detection.

## Setup Files

- `.env.example` - Template for local environment values.
- `requirements.txt` - Python dependencies: openai, ddgs, playwright, reportlab.
- `.gitignore` - Keeps secrets and generated output out of version control.