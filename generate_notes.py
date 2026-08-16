"""
Main entry point.

Usage:
    python generate_notes.py                  # one note per scraped skill
    python generate_notes.py "React.js"       # just one topic (ad-hoc)
    python generate_notes.py --force          # regenerate every topic
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import concurrent.futures
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
    STAGE_2_ASCII_ARCHITECTURE,
    STAGE_2_5_PORTFOLIO_RELEVANCE,
    STAGE_2_7_PITFALLS,
    STAGE_2_8_CHEATSHEET,
    STAGE_3_INTERVIEW_QUESTIONS,
)

NOTE_STATE_FILENAME = ".note_state.json"

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
    return "\n".join(lines) if lines else format_portfolio_context(PORTFOLIO_PROJECTS)

def load_topics_from_portfolio_data(data: dict) -> list[str]:
    skills = data.get("skills", []) if data else []
    topics = []
    for skill in skills:
        skill = str(skill).strip()
        if skill and skill not in topics:
            topics.append(skill)
    return topics

def _text_mentions_topic(text: str, topic_lower: str) -> bool:
    return bool(text) and topic_lower in text.lower()

def _portfolio_snapshot_for_topic(topic: str, data: dict) -> dict:
    topic_lower = topic.lower()
    if not data:
        return {"fallback_projects": PORTFOLIO_PROJECTS}

    matched_projects = []
    for project in data.get("projects", []):
        haystack = " ".join([
            str(project.get("name", "")),
            str(project.get("description", "")),
            " ".join(project.get("tech_stack", []) or []),
        ])
        if _text_mentions_topic(haystack, topic_lower):
            matched_projects.append(project)

    experience = data.get("experience", {})
    matched_roles = []
    for role in experience.get("roles", []) or []:
        haystack = " ".join([
            str(role.get("title", "")),
            str(role.get("company", "")),
            " ".join(role.get("highlights", []) or []),
        ])
        if _text_mentions_topic(haystack, topic_lower):
            matched_roles.append(role)

    return {
        "projects": matched_projects,
        "experience_roles": matched_roles,
    }

def portfolio_hash_for_topic(topic: str, data: dict) -> str:
    snapshot = _portfolio_snapshot_for_topic(topic, data)
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _note_state_path() -> Path:
    return Path(OUTPUT_MD_DIR) / NOTE_STATE_FILENAME

def load_note_state() -> dict:
    path = _note_state_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}

def save_note_state(state: dict) -> None:
    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
    with open(_note_state_path(), "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)

def existing_markdown_path(topic: str) -> Path:
    return Path(OUTPUT_MD_DIR) / f"{slugify(topic)}.md"

def is_topic_stale(topic: str, portfolio_data: dict, note_state: dict) -> bool:
    if not existing_markdown_path(topic).exists():
        return True
    slug = slugify(topic)
    recorded = note_state.get(slug)
    if not recorded:
        return True
    current_hash = portfolio_hash_for_topic(topic, portfolio_data)
    return recorded.get("portfolio_hash") != current_hash

def get_search_context(topic: str) -> str:
    if not ENABLE_SEARCH_CONTEXT:
        return "(search disabled)"
    try:
        from search_client import build_search_context
        return build_search_context(topic)
    except ImportError:
        return "(search unavailable — ddgs not installed)"

def save_markdown(topic: str, content: str) -> str:
    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
    filepath = existing_markdown_path(topic)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return str(filepath)

def generate_notes_for_topic(topic: str) -> str:
    """Runs the multi-stage pipeline utilizing Threading for extreme speedups."""
    print(f"\n=== {topic} ===")

    print("  [1/3] Fetching context...")
    search_context = get_search_context(topic)
    portfolio_context = format_portfolio_context_from_data(load_portfolio_data())

    # Step 1: Base Generation (Blocking, as others depend on it)
    print("  [2/3] Generating Core Theory & Fundamentals...")
    part_fundamentals = call_llm(
        STAGE_1A_FUNDAMENTALS.format(topic=topic, search_context=search_context),
        stage_name="fundamentals",
    )

    # Step 2: Parallel Generation (The Speedup Engine)
    print("  [3/3] Generating Diagrams, Internals, Interviews, & Portfolios concurrently...")
    
    # We execute 5 LLM calls simultaneously. 
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        f_internals = executor.submit(call_llm, STAGE_1B_DEEP_DIVE.format(topic=topic, search_context=search_context, stage1_output=part_fundamentals), "internals")
        f_diagrams = executor.submit(call_llm, STAGE_2_ASCII_ARCHITECTURE.format(topic=topic, stage1_output=part_fundamentals), "ascii-diagrams")
        f_pitfalls = executor.submit(call_llm, STAGE_2_7_PITFALLS.format(topic=topic, stage1_output=part_fundamentals), "pitfalls")
        f_cheatsheet = executor.submit(call_llm, STAGE_2_8_CHEATSHEET.format(topic=topic, stage1_output=part_fundamentals), "cheatsheet")
        f_portfolio = executor.submit(call_llm, STAGE_2_5_PORTFOLIO_RELEVANCE.format(topic=topic, portfolio_context=portfolio_context), "portfolio-relevance")
        f_interviews = executor.submit(call_llm, STAGE_3_INTERVIEW_QUESTIONS.format(topic=topic, stage1_output=part_fundamentals), "interview-questions")

        # Wait for all parallel responses to resolve
        part_internals = f_internals.result()
        part_diagrams = f_diagrams.result()
        part_pitfalls = f_pitfalls.result()
        part_cheatsheet = f_cheatsheet.result()
        part_portfolio = f_portfolio.result()
        part_interviews = f_interviews.result()

    # Stitch directly
    final_doc = f"""# {topic} — Study Notes

{part_portfolio}

---

## 1. Fundamentals & Mental Model
{part_fundamentals}

---

## 2. Internals & Real-World Patterns
{part_internals}

---

## 3. Architecture Diagrams
{part_diagrams}

---

## 4. Common Pitfalls & Debugging
{part_pitfalls}

---

## 5. Quick Reference Cheat Sheet
{part_cheatsheet}

---

## 6. Interview Questions
{part_interviews}
"""
    return final_doc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("topics", nargs="*", help="Specific topic(s) to generate.")
    parser.add_argument("--force", action="store_true", help="Regenerate every topic.")
    args = parser.parse_args()

    scraped_portfolio = load_portfolio_data()
    topics = args.topics or load_topics_from_portfolio_data(scraped_portfolio)

    if not topics:
        print("No scraped skills found.")
        return

    note_state = load_note_state()

    results = []
    for topic in topics:
        stale = args.force or is_topic_stale(topic, scraped_portfolio, note_state)
        if not stale:
            print(f"Skipping {topic} — Up to date.")
            continue

        start = time.time()
        try:
            final_doc = generate_notes_for_topic(topic)
            filepath = save_markdown(topic, final_doc)
            note_state[slugify(topic)] = {
                "topic": topic,
                "portfolio_hash": portfolio_hash_for_topic(topic, scraped_portfolio),
            }
            save_note_state(note_state)
            elapsed = time.time() - start
            print(f"  Saved: {filepath} ({elapsed:.1f}s)")
            results.append((topic, filepath, "ok"))
        except Exception as e:
            print(f"  FAILED: {topic} — {e}", file=sys.stderr)

if __name__ == "__main__":
    main()