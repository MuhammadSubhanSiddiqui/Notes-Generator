"""
Web search client — injects current context into the notes pipeline so
theory notes reflect recent versions/features instead of only the LLM's
training data.

Uses DuckDuckGo via the `ddgs` package. No API key required.

Install:
    pip install ddgs
"""

import sys
import time
from datetime import datetime, timezone

from config import (
    SEARCH_MAX_RETRIES,
    SEARCH_RETRY_BACKOFF_SECONDS,
    SEARCH_RESULTS_PER_QUERY,
)


def search_web(query: str, max_results: int = None) -> list:
    """
    Runs a single DuckDuckGo search. Returns a list of
    {"title": ..., "body": ..., "href": ...} dicts.

    Search is a nice-to-have context boost, not a hard pipeline requirement —
    on repeated failure this returns [] instead of raising, so one flaky
    search doesn't kill a topic's whole generation run.
    """
    from ddgs import DDGS  # imported lazily so the rest of the pipeline
    # still works if `ddgs` isn't installed and ENABLE_SEARCH_CONTEXT=false

    max_results = max_results or SEARCH_RESULTS_PER_QUERY
    last_error = None

    for attempt in range(1, SEARCH_MAX_RETRIES + 1):
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            last_error = e
            print(
                f"  [search] attempt {attempt}/{SEARCH_MAX_RETRIES} failed "
                f"for '{query}': {e}",
                file=sys.stderr,
            )
            if attempt < SEARCH_MAX_RETRIES:
                time.sleep(SEARCH_RETRY_BACKOFF_SECONDS * attempt)

    print(
        f"  [search] giving up on '{query}' after {SEARCH_MAX_RETRIES} "
        f"attempts: {last_error}. Continuing without this query's results.",
        file=sys.stderr,
    )
    return []


def build_search_context(topic: str) -> str:
    """
    Runs a couple of targeted queries for a topic and formats the results
    into a compact text block for injection into STAGE_1_THEORY as
    {search_context}.
    """
    current_year = datetime.now(timezone.utc).year
    queries = [
        f"{topic} best practices {current_year}",
        f"{topic} latest features updates",
    ]

    blocks = []
    for q in queries:
        results = search_web(q)
        if not results:
            continue
        lines = [f"Query: {q}"]
        for r in results:
            title = (r.get("title") or "").strip()
            body = (r.get("body") or "").strip()
            if title or body:
                lines.append(f"- {title}: {body}")
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    if not blocks:
        return "(no search results available — proceed from training knowledge)"

    return "\n\n".join(blocks)
