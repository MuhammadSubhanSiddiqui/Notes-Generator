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
import re
import sys
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright


class PortfolioScraper:
    """Scrapes the portfolio site and extracts skills/projects."""

    BASE_URL = "https://muhammadsubhansiddiqui.netlify.app/"
    SKILLS_SECTION_INDEX = 2
    PROJECT_SECTION_INDEX = 3
    EXPERIENCE_SECTION_INDEX = 4

    DATE_PATTERN = re.compile(
        r"^(?:"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
        r"(?:\s*[–-]\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\s*[–-]\s*Present)?"
        r"|\d{4}"
        r"|(?:Spring|Summer|Fall|Winter)\s+\d{4}"
        r")$",
        re.IGNORECASE,
    )
    LINK_LABELS = {"GitHub", "Live Demo", "Dataset", "Resume"}

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

            print("Extracting experience...")
            experience = await self._extract_experience()

            result = {
                "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "skills": skills,
                "projects": projects,
                "experience": experience,
            }

            print(f"✓ Scraped {len(skills)} skills and {len(projects)} projects")
            return result

        except Exception as e:
            print(f"✗ Scraping failed: {e}", file=sys.stderr)
            raise

    async def _extract_skills(self) -> List[str]:
        """Extract all skills from the skills section."""
        try:
            section = self._page.locator("section").nth(self.SKILLS_SECTION_INDEX)
            text = (await section.inner_text()).strip()
            lines = self._split_lines(text)
            if len(lines) < 4:
                print("  Warning: Skills section not found", file=sys.stderr)
                return []
            category_headers = {
                "All",
                "AI & ML",
                "Full-Stack",
                "Tools",
                "Languages",
                "AI/ML & Data",
                "Full-Stack & Frameworks",
                "Databases",
                "Networking & Security",
                "Realtime & Voice AI",
                "Tools & DevOps",
            }
            skills = []
            for line in lines:
                if line in {"SKILLS", "Technical toolkit"}:
                    continue
                if line.startswith("From ") or line in category_headers:
                    continue
                if line not in skills:
                    skills.append(line)
            return skills

        except Exception as e:
            print(f"  Warning: Failed to extract skills: {e}", file=sys.stderr)
            return []

    async def _extract_projects(self) -> List[Dict[str, Any]]:
        """Extract all projects from the projects section."""
        try:
            section = self._page.locator("section").nth(self.PROJECT_SECTION_INDEX)
            articles = section.locator("article")
            count = await articles.count()
            if not count:
                print("  Warning: Projects section not found", file=sys.stderr)
                return []

            projects = []
            for index in range(count):
                text = (await articles.nth(index).inner_text()).strip()
                project = self._parse_project_card(text)
                if project:
                    projects.append(project)
            return projects

        except Exception as e:
            print(f"  Warning: Failed to extract projects: {e}", file=sys.stderr)
            return []

    async def _extract_experience(self) -> Dict[str, Any]:
        try:
            section = self._page.locator("section").nth(self.EXPERIENCE_SECTION_INDEX)
            text = (await section.inner_text()).strip()
            return self._parse_experience_section(text)
        except Exception as e:
            print(f"  Warning: Failed to extract experience: {e}", file=sys.stderr)
            return {"overview": "", "roles": [], "community_roles": [], "raw_text": ""}

    def _split_lines(self, text: str) -> List[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _is_date_line(self, line: str) -> bool:
        return bool(self.DATE_PATTERN.match(line))

    def _is_label_line(self, line: str) -> bool:
        return line in {"Featured", "PROJECTS", "EXPERIENCE", "ABOUT", "SKILLS"}

    def _looks_like_tag(self, line: str) -> bool:
        return (
            line in self.LINK_LABELS
            or len(line) <= 40
            and len(line.split()) <= 4
            and not line.endswith(".")
            and not self._is_date_line(line)
            and not self._is_label_line(line)
        )

    def _parse_project_card(self, text: str) -> Optional[Dict[str, Any]]:
        lines = self._split_lines(text)
        if not lines:
            return None

        date_index = next((index for index, line in enumerate(lines) if self._is_date_line(line)), None)
        if date_index is None:
            return None

        title = ""
        for index in range(date_index - 1, -1, -1):
            candidate = lines[index]
            if not self._is_label_line(candidate) and not candidate.startswith("+"):
                title = candidate
                break

        tail_index = len(lines)
        for index in range(len(lines) - 1, date_index, -1):
            if self._looks_like_tag(lines[index]):
                tail_index = index
            else:
                break

        description_lines = lines[date_index + 1 : tail_index]
        tag_lines = lines[tail_index:]

        return {
            "name": title,
            "period": lines[date_index],
            "description": "\n".join(description_lines),
            "tech_stack": [line for line in tag_lines if line not in self.LINK_LABELS],
            "links": [line for line in tag_lines if line in self.LINK_LABELS],
            "raw_text": text,
        }

    def _parse_experience_section(self, text: str) -> Dict[str, Any]:
        lines = self._split_lines(text)
        if not lines:
            return {"overview": "", "roles": [], "community_roles": [], "raw_text": ""}

        overview = []
        roles = []
        community_roles = []

        date_indices = [index for index, line in enumerate(lines) if self._is_date_line(line)]
        community_index = next((index for index, line in enumerate(lines) if line == "COMMUNITY ROLES"), None)

        if date_indices:
            overview = lines[2:date_indices[0]] if len(lines) > 2 else []

        for position, date_index in enumerate(date_indices):
            next_boundary = date_indices[position + 1] if position + 1 < len(date_indices) else (
                community_index if community_index is not None else len(lines)
            )
            roles.append(
                {
                    "period": lines[date_index],
                    "location": lines[date_index + 1] if date_index + 1 < next_boundary else "",
                    "title": lines[date_index + 2] if date_index + 2 < next_boundary else "",
                    "company": lines[date_index + 3] if date_index + 3 < next_boundary else "",
                    "highlights": lines[date_index + 4 : next_boundary],
                }
            )

        if community_index is not None:
            community_roles = lines[community_index + 1 :]

        return {
            "overview": "\n".join(overview),
            "roles": roles,
            "community_roles": community_roles,
            "raw_text": text,
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
