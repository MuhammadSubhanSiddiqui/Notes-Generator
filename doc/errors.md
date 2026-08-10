# Errors

## Common Failures

- `Connection refused` from `llm_client.py`: the local OpenAI-compatible server is not running, or `LLM_BASE_URL` is wrong.
- Empty or low-quality model output: verify `LLM_MODEL` matches a model name your local server actually exposes.
- `ModuleNotFoundError: ddgs`: install the dependencies from `requirements.txt`, or set `ENABLE_SEARCH_CONTEXT=false`.
- Playwright launch errors: run `playwright install chromium` after installing the Python packages.
- PDF conversion errors: reinstall the Python dependencies from `requirements.txt`; the PDF step now uses `reportlab`, so it should not need system libraries.

## Scraper Issues

- No skills or projects found: the portfolio layout changed, so the CSS selectors in `portfolio_scraper.py` need to be refreshed.
- Scraper returns an empty JSON file: confirm the page loads in a browser and that the base URL is reachable.
- Browser timeout during scraping: rerun with `--headed` to inspect what the page is doing.

## Notes Pipeline Issues

- Missing Markdown output: verify `config.TOPICS` is not empty, or pass a topic name directly to `generate_notes.py`.
- PDF conversion skips a file: confirm the matching `.md` file exists in `output/md/`.
- Broken ASCII alignment in PDFs: shorten the widest line in the diagram, or reduce the number of columns in the cheat sheet. The PDF converter now auto-scales code blocks, so the issue is usually the diagram width.

## Recovery Steps

1. Reinstall dependencies with `pip install -r requirements.txt`.
2. Reinstall Chromium with `playwright install chromium`.
3. Check `.env` against `.env.example`.
4. Regenerate the scraper output, notes, and PDFs in that order.