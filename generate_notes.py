"""
Main entry point.

Usage:
    python generate_notes.py                  # runs one note per scraped skill
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

import json
import os
import re
import sys
import time
from pathlib import Path

from config import (
    PORTFOLIO_DATA_PATH,
    OUTPUT_MD_DIR,
    LLM_MODEL,
    LLM_BASE_URL,
    ENABLE_SEARCH_CONTEXT,
    PORTFOLIO_PROJECTS,
)
from llm_client import call_llm
from prompts.templates import (
    STAGE_1A_FUNDAMENTALS,
    STAGE_1B_DEEP_DIVE,
    STAGE_1C_SECURITY_PERFORMANCE,
    STAGE_2_ASCII_ARCHITECTURE,
    STAGE_2_5_PORTFOLIO_RELEVANCE,
    STAGE_2_7_PITFALLS,
    STAGE_2_8_CHEATSHEET,
    STAGE_3_INTERVIEW_QUESTIONS,
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


def load_portfolio_data() -> dict:
    path = Path(PORTFOLIO_DATA_PATH)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def format_portfolio_context_from_data(data: dict) -> str:
    if not data:
        return format_portfolio_context(PORTFOLIO_PROJECTS)

    lines = []
    for project in data.get("projects", []):
        stack = ", ".join(project.get("tech_stack", []))
        links = ", ".join(project.get("links", []))
        lines.append(
            f"- Project: {project.get('name', '')} | Period: {project.get('period', '')} | "
            f"Description: {project.get('description', '').strip()} | Stack: {stack} | Links: {links}"
        )

    experience = data.get("experience", {})
    overview = experience.get("overview", "").strip()
    if overview:
        lines.append(f"- Experience overview: {overview}")
    for role in experience.get("roles", []):
        highlights = " / ".join(role.get("highlights", []))
        lines.append(
            f"- Experience: {role.get('title', '')} at {role.get('company', '')} | "
            f"Period: {role.get('period', '')} | Location: {role.get('location', '')} | Highlights: {highlights}"
        )
    community_roles = experience.get("community_roles", [])
    if community_roles:
        lines.append(f"- Community roles: {', '.join(community_roles)}")

    return "\n".join(lines) if lines else format_portfolio_context(PORTFOLIO_PROJECTS)


def load_topics_from_portfolio_data(data: dict) -> list[str]:
    skills = data.get("skills", []) if data else []
    topics = []
    for skill in skills:
        skill = str(skill).strip()
        if skill and skill not in topics:
            topics.append(skill)
    return topics


def load_reference_notes(current_topic: str, limit: int = 2) -> str:
    output_dir = Path(OUTPUT_MD_DIR)
    if not output_dir.exists():
        return "(no earlier markdown files yet)"

    candidates = []
    current_filename = f"{slugify(current_topic)}.md"
    for path in sorted(output_dir.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.name == current_filename:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if content.strip():
            candidates.append(f"File: {path.name}\n{content[:5000]}")
        if len(candidates) >= limit:
            break

    return "\n\n---\n\n".join(candidates) if candidates else "(no earlier markdown files yet)"


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

# generate_notes.py
def generate_notes_for_topic(topic: str) -> str:
    """Runs the modular multi-stage pipeline for a topic and returns full Markdown."""
    print(f"\n=== {topic} ===")

    print("  [1/8] Fetching search context...")
    search_context = get_search_context(topic)

    print("  [2/8] Generating fundamentals & mental model...")
    part_fundamentals = call_llm(
        STAGE_1A_FUNDAMENTALS.format(topic=topic, search_context=search_context),
        stage_name="fundamentals",
    )

    print("  [3/8] Generating internals & advanced architecture...")
    part_internals = call_llm(
        STAGE_1B_DEEP_DIVE.format(topic=topic),
        stage_name="internals",
    )

    print("  [4/8] Generating enterprise performance & security...")
    part_sec_perf = call_llm(
        STAGE_1C_SECURITY_PERFORMANCE.format(topic=topic),
        stage_name="sec-perf",
    )

    print("  [5/8] Generating ASCII architecture diagrams...")
    part_diagrams = call_llm(
        STAGE_2_ASCII_ARCHITECTURE.format(topic=topic, stage1_output=part_fundamentals),
        stage_name="ascii-diagrams",
    )

    print("  [6/8] Generating common pitfalls & debugging traps...")
    part_pitfalls = call_llm(
        STAGE_2_7_PITFALLS.format(topic=topic, stage1_output=part_internals),
        stage_name="pitfalls",
    )

    print("  [7/8] Generating quick reference cheat sheet...")
    part_cheatsheet = call_llm(
        STAGE_2_8_CHEATSHEET.format(topic=topic, stage1_output=part_fundamentals),
        stage_name="cheatsheet",
    )

    print("  [8/8] Matching portfolio & generating interview questions...")
    portfolio_context = format_portfolio_context_from_data(load_portfolio_data())
    part_portfolio = call_llm(
        STAGE_2_5_PORTFOLIO_RELEVANCE.format(
            topic=topic, portfolio_context=portfolio_context
        ),
        stage_name="portfolio-relevance",
    )

    part_interviews = call_llm(
        STAGE_3_INTERVIEW_QUESTIONS.format(topic=topic, stage1_output=part_internals),
        stage_name="interview-questions",
    )

    # Stitch directly to avoid LLM merge/truncation bottlenecks
    final_doc = f"""# {topic} — Comprehensive Engineering Reference

{part_portfolio}

---

## 1. Core Architecture & Fundamentals
{part_fundamentals}

---

## 2. Deep Dive & Production Internals
{part_internals}

---

## 3. Architecture Diagrams
{part_diagrams}

---

## 4. Performance, Hardening & Security
{part_sec_perf}

---

## 5. Common Pitfalls, Edge Cases & Debugging
{part_pitfalls}

---

## 6. Quick Reference Cheat Sheet & API Matrix
{part_cheatsheet}

---

## 7. Comprehensive Technical Interview Guide
{part_interviews}
"""
    return final_doc

def save_markdown(topic: str, content: str) -> str:
    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
    filename = f"{slugify(topic)}.md"
    filepath = os.path.join(OUTPUT_MD_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def main():
    scraped_portfolio = load_portfolio_data()
    topics = sys.argv[1:] if len(sys.argv) > 1 else load_topics_from_portfolio_data(scraped_portfolio)

    if not topics:
        print("No scraped skills found. Run portfolio_scraper.py first, "
              "or pass one as an argument: python generate_notes.py \"React.js\"")
        return

    print(f"LLM endpoint: {LLM_BASE_URL} | model: {LLM_MODEL}")
    print(f"Search context: {'enabled' if ENABLE_SEARCH_CONTEXT else 'disabled'}")
    print(f"Scraped portfolio loaded: {'yes' if scraped_portfolio else 'no'}")
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
