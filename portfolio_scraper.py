"""
Portfolio scraper using Playwright to extract skills and projects from the
React SPA portfolio at muhammadsubhansiddiqui.me.

Extracts:
- Skills list (all technical tools and languages)
- Projects (name, description, tech stack, links)
- Experience & Certifications

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
    """Scrapes the portfolio site and extracts skills/projects/experience."""

    BASE_URL = "https://muhammadsubhansiddiqui.me/"
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
        """Extract clean technical skills from the skills section."""
        try:
            # Try finding section by heading or fallback to index
            section = self._page.locator("section").filter(has_text="Technical toolkit").first
            if not await section.count():
                section = self._page.locator("section").nth(self.SKILLS_SECTION_INDEX)
                
            text = (await section.inner_text()).strip()
            lines = self._split_lines(text)
            
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
                "SKILLS",
                "Technical toolkit",
                "Systems I've shipped",
                "Featured",
            }
            
            skills = []
            for line in lines:
                if line in category_headers or line.startswith("From ") or line.isdigit() or len(line) > 35:
                    continue
                if line not in skills:
                    skills.append(line)
            return skills

        except Exception as e:
            print(f"  Warning: Failed to extract skills: {e}", file=sys.stderr)
            return []

    async def _extract_projects(self) -> List[Dict[str, Any]]:
        """Extract all projects from the projects section robustly."""
        try:
            # Target section containing project articles directly
            section = self._page.locator("section").filter(has_text="Systems I've shipped").first
            if not await section.count():
                section = self._page.locator("section").nth(self.PROJECT_SECTION_INDEX)

            articles = section.locator("article")
            count = await articles.count()
            
            if not count:
                # Fallback: find any articles on the entire page if section query is out of sync
                articles = self._page.locator("article")
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
        """Extract experience items by clicking through tabs and cleaning duplicates."""
        try:
            sections = self._page.locator("section")
            count = await sections.count()
            
            experience_section = None
            for i in range(count):
                sec_text = await sections.nth(i).inner_text()
                if "EXPERIENCE" in sec_text.upper() and "Where I've built momentum" in sec_text:
                    experience_section = sections.nth(i)
                    break
            
            if not experience_section:
                experience_section = sections.nth(self.EXPERIENCE_SECTION_INDEX)

            tab_buttons = experience_section.locator("button, [role='tab']")
            tab_count = await tab_buttons.count()
            
            collected_chunks = []
            
            if tab_count > 0:
                for t in range(tab_count):
                    btn = tab_buttons.nth(t)
                    await btn.click()
                    await self._page.wait_for_timeout(400)
                    
                    # Extract the active content panel specifically if available, else section text
                    panel = experience_section.locator(".tab-content, [role='tabpanel'], article, div").nth(0)
                    chunk_text = await panel.inner_text() if await panel.count() > 0 else await experience_section.inner_text()
                    collected_chunks.append(chunk_text.strip())
            else:
                collected_chunks.append(await experience_section.inner_text())

            # Clean and deduplicate text chunks
            unique_text = "\n\n".join(dict.fromkeys(collected_chunks))
            
            return {
                "overview": unique_text,
                "certifications": [],
                "raw_text": unique_text
            }
            
        except Exception as e:
            print(f"  Warning: Failed to extract experience: {e}", file=sys.stderr)
            return {"overview": "", "certifications": [], "raw_text": ""}     
        
    def _parse_experience_section(self, text: str) -> Dict[str, Any]:
        lines = self._split_lines(text)
        if not lines:
            return {"work_experience": [], "education": {}, "certifications": [], "raw_text": text}

        # Structure your education foundation
        education = {
            "degree": "BS Computer Science",
            "institution": "Air University Islamabad",
            "period": "2023 – 2027 · Expected",
        }

        work_experience = []
        certifications = []

        # Parse through lines to dynamically separate Work Experience/Fellowships and Certifications
        # (Aapke portfolio par jo Data X ya fellowships hain, unhein yahan capture kiya jayega)
        
        # Let's cleanly separate sections based on known headers in your portfolio text
        current_section = "education"
        i = 0
        while i < len(lines):
            line = lines[i]
            if "EXPERIENCE" in line.upper() or "FELLOWSHIP" in line.upper():
                current_section = "work"
                i += 1
                continue
            elif "CERTIFICATIONS" in line.upper():
                current_section = "certifications"
                i += 1
                continue
            elif "RELEVANT COURSEWORK" in line.upper():
                current_section = "coursework"
                i += 1
                continue

            if current_section == "work":
                # Capture work experience / fellowship items
                work_experience.append(line)
            elif current_section == "certifications":
                certifications.append(line)
            
            i += 1

        return {
            "work_experience": work_experience,
            "education": education,
            "certifications": certifications,
            "raw_text": text,
        }
    
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

        overview_lines = []
        certifications = []
        
        # Parse through lines to cleanly separate education and certifications
        capturing_certs = False
        for line in lines:
            if "CERTIFICATIONS" in line:
                capturing_certs = True
                continue
            if not capturing_certs:
                overview_lines.append(line)
            else:
                certifications.append(line)

        return {
            "overview": "\n".join(overview_lines),
            "certifications": certifications,
            "raw_text": text,
        }


async def scrape_portfolio(
    output_path: str = "portfolio_data.json",
    headless: bool = True,
    url: Optional[str] = None,
) -> int:
    """Main entry point for scraping."""
    try:
        async with PortfolioScraper(headless=headless, base_url=url) as scraper:
            data = await scraper.scrape()

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved scraped data to {output_path}")
            return 0

    except Exception as e:
        print(f"✗ Scraping failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = ArgumentParser(description="Scrape portfolio site and cache as JSON")
    parser.add_argument("--url", default=PortfolioScraper.BASE_URL)
    parser.add_argument("--output", default="portfolio_data.json")
    parser.add_argument("--headed", action="store_true")

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
