"""Run the full automation pipeline: scrape -> one skill at a time -> PDF."""

import asyncio
import sys
from pathlib import Path

from config import OUTPUT_MD_DIR
from convert_to_pdf import convert_file
from generate_notes import (
    generate_notes_for_topic,
    load_portfolio_data,
    load_topics_from_portfolio_data,
    save_markdown,
)
from portfolio_scraper import scrape_portfolio


def main() -> int:
    print("Starting portfolio scrape...")
    scrape_exit = asyncio.run(scrape_portfolio())
    if scrape_exit != 0:
        return scrape_exit

    scraped_portfolio = load_portfolio_data()
    topics = load_topics_from_portfolio_data(scraped_portfolio)
    if not topics:
        print("No scraped skills found in portfolio_data.json.")
        return 1

    print(f"Generating {len(topics)} notes, converting each one immediately...")
    print(f"Markdown output directory: {OUTPUT_MD_DIR}")

    failures = 0
    for topic in topics:
        print(f"\n=== {topic} ===")
        try:
            final_doc = generate_notes_for_topic(topic)
            md_path = save_markdown(topic, final_doc)
            if not convert_file(Path(md_path).name):
                failures += 1
        except Exception as exc:
            failures += 1
            print(f"  FAILED: {topic} — {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())