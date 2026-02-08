"""GitHub/Arbeitnow Jobs API scraper (GitHub Jobs replacement)."""

from datetime import datetime, timezone
from typing import Any

import structlog

from app.scrapers.base import BaseScraper

logger = structlog.get_logger()


class GitHubJobsScraper(BaseScraper):
    """
    Scraper for Arbeitnow.com - a free job board with API.

    This serves as a replacement for the deprecated GitHub Jobs API.
    """

    source_name = "arbeitnow"
    base_url = "https://www.arbeitnow.com/api"

    async def scrape(
        self,
        page: int = 1,
        location: str | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Scrape jobs from Arbeitnow.

        Args:
            page: Page number for pagination
            location: Filter by location

        Returns:
            List of normalized job dictionaries
        """
        jobs = []

        try:
            url = f"{self.base_url}/job-board-api"
            params = {"page": page}

            response = await self.fetch(url, params=params)
            data = response.json()

            job_list = data.get("data", [])

            for raw_job in job_list:
                try:
                    # Filter by location if specified
                    if location:
                        job_location = (raw_job.get("location") or "").lower()
                        if location.lower() not in job_location:
                            continue

                    parsed = self.parse_job(raw_job)
                    normalized = self.normalize_job(parsed)
                    jobs.append(normalized)

                except Exception as e:
                    logger.warning(
                        "job_parse_error",
                        source=self.source_name,
                        error=str(e),
                        job_slug=raw_job.get("slug"),
                    )
                    continue

            logger.info(
                "scrape_complete",
                source=self.source_name,
                jobs_found=len(jobs),
                page=page,
            )

        except Exception as e:
            logger.error(
                "scrape_error",
                source=self.source_name,
                error=str(e),
            )

        return jobs

    def parse_job(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Arbeitnow job data into standardized format."""
        # Parse posted date
        posted_at = None
        if raw_data.get("created_at"):
            try:
                posted_at = datetime.fromisoformat(
                    raw_data["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Determine if remote
        is_remote = raw_data.get("remote", False)
        location = raw_data.get("location", "")

        if "remote" in location.lower():
            is_remote = True

        # Extract skills from description
        description = raw_data.get("description", "")
        skills = self.extract_skills(description)

        # Build tags from various fields
        tags = raw_data.get("tags", [])
        if raw_data.get("job_types"):
            tags.extend(raw_data["job_types"])

        return {
            "external_id": raw_data.get("slug", str(raw_data.get("id", ""))),
            "title": raw_data.get("title", ""),
            "company": raw_data.get("company_name", ""),
            "company_logo_url": raw_data.get("company_logo"),
            "location": location,
            "is_remote": is_remote,
            "remote_type": "fully_remote" if is_remote else None,
            "description": self._strip_html(description),
            "description_html": description,
            "required_skills": skills,
            "tags": tags,
            "url": raw_data.get("url", ""),
            "apply_url": raw_data.get("url"),
            "posted_at": posted_at,
            "raw_data": raw_data,
        }

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from text."""
        if not html:
            return ""

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)
