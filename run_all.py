"""Run the full automation pipeline: scrape -> one skill at a time -> PDF.

Usage:
    python run_all.py            # skip topics whose relevant portfolio
                                  # content hasn't changed since their
                                  # last generation
    python run_all.py --force    # regenerate every topic regardless
"""

import argparse
import asyncio
import sys
from pathlib import Path

from config import OUTPUT_MD_DIR
from convert_to_pdf import convert_file
from generate_notes import (
    existing_markdown_path,
    generate_notes_for_topic,
    is_topic_stale,
    load_note_state,
    load_portfolio_data,
    load_topics_from_portfolio_data,
    portfolio_hash_for_topic,
    save_markdown,
    save_note_state,
    slugify,
)
from portfolio_scraper import scrape_portfolio


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape portfolio, then generate + convert notes for each skill.")
    parser.add_argument("--force", action="store_true", help="Regenerate every topic regardless of existing file or portfolio hash.")
    args = parser.parse_args()

    print("Starting portfolio scrape...")
    scrape_exit = asyncio.run(scrape_portfolio())
    if scrape_exit != 0:
        return scrape_exit

    # Re-load right after scraping so staleness is checked against the
    # portfolio data as it stands *now*, not a possibly-older cached copy.
    scraped_portfolio = load_portfolio_data()
    topics = load_topics_from_portfolio_data(scraped_portfolio)
    if not topics:
        print("No scraped skills found in portfolio_data.json.")
        return 1

    note_state = load_note_state()

    print(f"Processing {len(topics)} topic(s), converting each one immediately...")
    print(f"Markdown output directory: {OUTPUT_MD_DIR}")
    if not args.force:
        print("(topics whose relevant portfolio content hasn't changed since their last "
              "generation will be skipped — use --force to regenerate anyway)")

    failures = 0
    for topic in topics:
        print(f"\n=== {topic} ===")
        stale = args.force or is_topic_stale(topic, scraped_portfolio, note_state)
        if not stale:
            existing = existing_markdown_path(topic)
            print(f"  Skipping generation — {existing} is up to date with the portfolio")
            if not convert_file(existing.name):
                failures += 1
            continue

        try:
            final_doc = generate_notes_for_topic(topic)
            md_path = save_markdown(topic, final_doc)
            note_state[slugify(topic)] = {
                "topic": topic,
                "portfolio_hash": portfolio_hash_for_topic(topic, scraped_portfolio),
            }
            save_note_state(note_state)
            if not convert_file(Path(md_path).name):
                failures += 1
        except Exception as exc:
            failures += 1
            print(f"  FAILED: {topic} — {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
