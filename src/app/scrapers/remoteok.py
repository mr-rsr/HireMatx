"""RemoteOK job board scraper."""

from datetime import datetime, timezone
from typing import Any

import structlog

from app.scrapers.base import BaseScraper

logger = structlog.get_logger()


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK.com - a remote-friendly job board."""

    source_name = "remoteok"
    base_url = "https://remoteok.com"

    async def scrape(self, tags: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        """
        Scrape jobs from RemoteOK.

        Args:
            tags: Optional list of tags to filter by (e.g., ['python', 'react'])

        Returns:
            List of normalized job dictionaries
        """
        jobs = []

        try:
            # RemoteOK provides a JSON API
            url = f"{self.base_url}/api"

            response = await self.fetch(url)
            data = response.json()

            # First item is usually metadata, skip it
            job_list = data[1:] if len(data) > 1 else data

            for raw_job in job_list[:100]:  # Limit to 100 jobs per scrape
                try:
                    if not raw_job.get("slug"):
                        continue

                    # Filter by tags if specified
                    if tags:
                        job_tags = [t.lower() for t in raw_job.get("tags", [])]
                        if not any(tag.lower() in job_tags for tag in tags):
                            continue

                    parsed = self.parse_job(raw_job)
                    normalized = self.normalize_job(parsed)
                    jobs.append(normalized)

                except Exception as e:
                    logger.warning(
                        "job_parse_error",
                        source=self.source_name,
                        error=str(e),
                        job_id=raw_job.get("id"),
                    )
                    continue

            logger.info(
                "scrape_complete",
                source=self.source_name,
                jobs_found=len(jobs),
            )

        except Exception as e:
            logger.error(
                "scrape_error",
                source=self.source_name,
                error=str(e),
            )

        return jobs

    def parse_job(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse RemoteOK job data into standardized format."""
        # Parse posted date
        posted_at = None
        if raw_data.get("date"):
            try:
                # RemoteOK uses Unix timestamp
                posted_at = datetime.fromtimestamp(
                    int(raw_data["date"]), tz=timezone.utc
                )
            except (ValueError, TypeError):
                pass

        # Parse salary
        salary_min, salary_max, currency = self.parse_salary(
            raw_data.get("salary") or raw_data.get("salary_text") or ""
        )

        # Build job URL
        slug = raw_data.get("slug", raw_data.get("id", ""))
        job_url = f"{self.base_url}/l/{slug}" if slug else self.base_url

        # Extract skills from tags
        tags = raw_data.get("tags", [])
        skills = [tag for tag in tags if len(tag) > 1]

        # Parse description - RemoteOK provides HTML
        description_html = raw_data.get("description", "")
        description = self._strip_html(description_html)

        return {
            "external_id": str(raw_data.get("id", slug)),
            "title": raw_data.get("position", ""),
            "company": raw_data.get("company", ""),
            "company_logo_url": raw_data.get("company_logo") or raw_data.get("logo"),
            "location": raw_data.get("location") or "Remote",
            "is_remote": True,  # All RemoteOK jobs are remote
            "remote_type": "fully_remote",
            "description": description,
            "description_html": description_html,
            "required_skills": skills[:10],
            "tags": tags,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": currency,
            "salary_text": raw_data.get("salary"),
            "url": job_url,
            "apply_url": raw_data.get("apply_url") or raw_data.get("url") or job_url,
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
