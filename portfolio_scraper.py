"""
Portfolio scraper using Playwright to extract skills and projects from the
React SPA portfolio at muhammadsubhansiddiqui.netlify.app.

Extracts:
- Skills list (all technical tools and languages)
- Projects (name, description, tech stack, links)

Results are written to portfolio_data.json for caching.
"""

import asyncio
import json
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright


class PortfolioScraper:
    """Scrapes the portfolio site and extracts skills/projects."""

    BASE_URL = "https://muhammadsubhansiddiqui.netlify.app/"

    # CSS selectors (discovered via Playwright discovery)
    SKILLS_SELECTOR = "div.grid.grid-cols-1.gap-5.sm\\:grid-cols-2.lg\\:grid-cols-3"
    SKILL_CATEGORY_HEADING = "h3.font-heading.text-base.font-semibold"
    SKILL_TAGS = "div.flex.flex-wrap.gap-2 > span"

    PROJECTS_SELECTOR = "article"
    PROJECT_TITLE = "h3.font-heading.text-xl.font-bold"
    PROJECT_DATE = "p.text-sm.text-text-secondary"
    PROJECT_DESCRIPTION = "ul.space-y-2 > li"
    PROJECT_TECH_TAGS = "div.flex.flex-wrap.gap-2 > span"

    def __init__(self, headless: bool = True, base_url: Optional[str] = None):
        self.headless = headless
        self.base_url = base_url or self.BASE_URL
        self._playwright = None
        self._browser = None
        self._page = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def scrape(self) -> Dict[str, Any]:
        """Run the full scrape and return structured data."""
        print(f"Fetching portfolio from {self.base_url}...")

        try:
            await self._page.goto(self.base_url, wait_until="networkidle", timeout=60000)
            await self._page.wait_for_timeout(3000)  # Wait for React hydration

            print("Extracting skills...")
            skills = await self._extract_skills()

            print("Extracting projects...")
            projects = await self._extract_projects()

            result = {
                "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "skills": skills,
                "projects": projects,
            }

            print(f"✓ Scraped {len(skills)} skills and {len(projects)} projects")
            return result

        except Exception as e:
            print(f"✗ Scraping failed: {e}", file=sys.stderr)
            raise

    async def _extract_skills(self) -> List[str]:
        """Extract all skills from the skills section."""
        skills = set()

        try:
            skills_section = await self._page.query_selector(self.SKILLS_SELECTOR)
            if not skills_section:
                print("  Warning: Skills section not found", file=sys.stderr)
                return []

            # Get all skill tags (all spans inside skill categories)
            skill_tags = await skills_section.query_selector_all(self.SKILL_TAGS)
            for tag in skill_tags:
                text = await tag.inner_text()
                text = text.strip()
                if text:
                    skills.add(text)

            return sorted(skills)

        except Exception as e:
            print(f"  Warning: Failed to extract skills: {e}", file=sys.stderr)
            return []

    async def _extract_projects(self) -> List[Dict[str, Any]]:
        """Extract all projects from the projects section."""
        projects = []

        try:
            articles = await self._page.query_selector_all(self.PROJECTS_SELECTOR)
            if not articles:
                print("  Warning: Projects section not found", file=sys.stderr)
                return []

            for article in articles:
                try:
                    project = await self._extract_single_project(article)
                    if project:
                        projects.append(project)
                except Exception as e:
                    print(f"  Warning: Failed to extract single project: {e}", file=sys.stderr)
                    continue

            return projects

        except Exception as e:
            print(f"  Warning: Failed to extract projects: {e}", file=sys.stderr)
            return []

    async def _extract_single_project(self, article) -> Dict[str, Any]:
        """Extract data from a single project article."""
        # Title
        title_elem = await article.query_selector(self.PROJECT_TITLE)
        title = await title_elem.inner_text() if title_elem else ""

        # Date
        date_elem = await article.query_selector(self.PROJECT_DATE)
        date = await date_elem.inner_text() if date_elem else ""

        # Description (first 3 bullets)
        desc_elems = await article.query_selector_all(self.PROJECT_DESCRIPTION)
        descriptions = []
        for elem in desc_elems[:3]:
            text = await elem.inner_text()
            if text:
                descriptions.append(text)
        description = "\n".join(descriptions)

        # Tech stack tags
        tech_tags = await article.query_selector_all(self.PROJECT_TECH_TAGS)
        tech_stack = []
        for tag in tech_tags:
            text = await tag.inner_text()
            if text:
                tech_stack.append(text.strip())

        # GitHub link (first link with github icon)
        github_link = ""
        links = await article.query_selector_all("a[href*='github']")
        for link in links:
            href = await link.get_attribute("href", "")
            if href and "github" in href.lower():
                github_link = href
                break

        return {
            "name": title.strip(),
            "date": date.strip(),
            "description": description.strip(),
            "tech_stack": tech_stack,
            "github_url": github_link,
        }


async def scrape_portfolio(
    output_path: str = "portfolio_data.json",
    headless: bool = True,
    url: Optional[str] = None,
) -> int:
    """
    Main entry point for scraping.

    Returns:
        0 on success, 1 on error
    """
    try:
        async with PortfolioScraper(headless=headless, base_url=url) as scraper:
            data = await scraper.scrape()

            # Write to JSON file
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved scraped data to {output_path}")
            return 0

    except Exception as e:
        print(f"✗ Scraping failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = ArgumentParser(description="Scrape a portfolio site and cache the results as JSON")
    parser.add_argument(
        "--url",
        default=PortfolioScraper.BASE_URL,
        help="Portfolio URL to scrape (default: muhammadsubhansiddiqui.netlify.app)",
    )
    parser.add_argument(
        "--output",
        default="portfolio_data.json",
        help="Output JSON file path (default: portfolio_data.json)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show browser window for debugging (default: headless)",
    )

    args = parser.parse_args()

    print("Portfolio Scraper")
    print(f"  URL: {args.url}")
    print(f"  Output: {args.output}")
    print(f"  Headless: {not args.headed}")
    print()

    return asyncio.run(
        scrape_portfolio(args.output, headless=not args.headed, url=args.url)
    )


if __name__ == "__main__":
    sys.exit(main())
