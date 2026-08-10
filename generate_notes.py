"""
Main entry point.

Usage:
    python generate_notes.py                  # runs all TOPICS from config.py
    python generate_notes.py "React.js"        # runs just one topic (ad-hoc)

For each topic runs:
    0. (optional) DuckDuckGo search context fetch — see search_client.py
    1. Theory (beginner -> advanced), informed by the search context
    2. ASCII architecture diagrams
    2.5 Portfolio relevance — which real projects (config.PORTFOLIO_PROJECTS)
        genuinely use this topic
    3. Interview questions
    4. Merge + polish into one final .md

Saves to output/md/<topic-slug>.md
"""

import os
import re
import sys
import time

from config import (
    TOPICS,
    OUTPUT_MD_DIR,
    LLM_MODEL,
    LLM_BASE_URL,
    ENABLE_SEARCH_CONTEXT,
    PORTFOLIO_PROJECTS,
)
from llm_client import call_llm
from prompts.templates import (
    STAGE_1_THEORY,
    STAGE_2_ASCII_ARCHITECTURE,
    STAGE_2_5_PORTFOLIO_RELEVANCE,
    STAGE_3_INTERVIEW_QUESTIONS,
    STAGE_4_MERGE_POLISH,
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


def format_portfolio_context(projects: list) -> str:
    if not projects:
        return "(no portfolio projects configured yet — PORTFOLIO_PROJECTS is empty in config.py)"
    lines = []
    for p in projects:
        stack = ", ".join(p.get("stack", []))
        lines.append(f"- {p['name']}: {p.get('description', '')} [Stack: {stack}]")
    return "\n".join(lines)


def get_search_context(topic: str) -> str:
    if not ENABLE_SEARCH_CONTEXT:
        return "(search disabled — ENABLE_SEARCH_CONTEXT is false in config.py)"
    try:
        from search_client import build_search_context
        return build_search_context(topic)
    except ImportError:
        print(
            "  [search] `ddgs` not installed — run `pip install ddgs` or set "
            "ENABLE_SEARCH_CONTEXT=false. Continuing without search context.",
            file=sys.stderr,
        )
        return "(search unavailable — ddgs not installed)"


def generate_notes_for_topic(topic: str) -> str:
    """Runs the full pipeline for one topic. Returns the final markdown."""
    print(f"\n=== {topic} ===")

    print("  [1/5] Fetching search context...")
    search_context = get_search_context(topic)

    print("  [2/5] Generating theory (beginner -> advanced)...")
    stage1 = call_llm(
        STAGE_1_THEORY.format(topic=topic, search_context=search_context),
        stage_name="theory",
    )

    print("  [3/5] Generating ASCII architecture diagrams...")
    stage2 = call_llm(
        STAGE_2_ASCII_ARCHITECTURE.format(topic=topic, stage1_output=stage1),
        stage_name="ascii-diagrams",
    )

    print("  [4/5] Matching against portfolio projects...")
    portfolio_context = format_portfolio_context(PORTFOLIO_PROJECTS)
    stage2_5 = call_llm(
        STAGE_2_5_PORTFOLIO_RELEVANCE.format(
            topic=topic, portfolio_context=portfolio_context
        ),
        stage_name="portfolio-relevance",
    )

    print("  [5/5] Generating interview questions + merging final document...")
    stage3 = call_llm(
        STAGE_3_INTERVIEW_QUESTIONS.format(topic=topic, stage1_output=stage1),
        stage_name="interview-questions",
    )

    final_doc = call_llm(
        STAGE_4_MERGE_POLISH.format(
            topic=topic,
            stage1_output=stage1,
            stage2_output=stage2,
            stage2_5_output=stage2_5,
            stage3_output=stage3,
        ),
        stage_name="merge-polish",
    )

    return final_doc


def save_markdown(topic: str, content: str) -> str:
    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
    filename = f"{slugify(topic)}.md"
    filepath = os.path.join(OUTPUT_MD_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def main():
    topics = sys.argv[1:] if len(sys.argv) > 1 else TOPICS

    if not topics:
        print("No topics configured. Add topics to config.py TOPICS list, "
              "or pass one as an argument: python generate_notes.py \"React.js\"")
        return

    print(f"LLM endpoint: {LLM_BASE_URL} | model: {LLM_MODEL}")
    print(f"Search context: {'enabled' if ENABLE_SEARCH_CONTEXT else 'disabled'}")
    print(f"Portfolio projects configured: {len(PORTFOLIO_PROJECTS)}")
    print(f"Topics queued: {topics}")

    results = []
    for topic in topics:
        start = time.time()
        try:
            final_doc = generate_notes_for_topic(topic)
            filepath = save_markdown(topic, final_doc)
            elapsed = time.time() - start
            print(f"  Saved: {filepath} ({elapsed:.1f}s)")
            results.append((topic, filepath, True))
        except Exception as e:
            print(f"  FAILED: {topic} — {e}", file=sys.stderr)
            results.append((topic, None, False))

    print("\n=== Summary ===")
    for topic, filepath, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {topic}" + (f" -> {filepath}" if filepath else ""))


if __name__ == "__main__":
    main()
