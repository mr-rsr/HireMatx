"""Base scraper class."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Base class for job scrapers."""

    source_name: str = "unknown"
    base_url: str = ""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": self.settings.scraper_user_agent,
                "Accept": "text/html,application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        """Fetch URL with retry logic."""
        await asyncio.sleep(self.settings.scraper_request_delay)

        logger.debug("scraper_fetch", url=url, source=self.source_name)
        response = await self.client.get(url, **kwargs)
        response.raise_for_status()

        return response

    @abstractmethod
    async def scrape(self, **kwargs) -> list[dict[str, Any]]:
        """Scrape jobs from source. Returns list of job dictionaries."""
        pass

    @abstractmethod
    def parse_job(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse raw job data into standardized format."""
        pass

    def normalize_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize job data to standard schema."""
        return {
            "external_id": str(job_data.get("external_id", "")),
            "title": job_data.get("title", "").strip(),
            "company": job_data.get("company", "").strip(),
            "company_logo_url": job_data.get("company_logo_url"),
            "location": job_data.get("location"),
            "is_remote": job_data.get("is_remote", False),
            "remote_type": job_data.get("remote_type"),
            "description": job_data.get("description"),
            "description_html": job_data.get("description_html"),
            "requirements": job_data.get("requirements"),
            "benefits": job_data.get("benefits"),
            "job_type": job_data.get("job_type"),
            "experience_level": job_data.get("experience_level"),
            "industry": job_data.get("industry"),
            "required_skills": job_data.get("required_skills", []),
            "preferred_skills": job_data.get("preferred_skills", []),
            "tags": job_data.get("tags", []),
            "salary_min": job_data.get("salary_min"),
            "salary_max": job_data.get("salary_max"),
            "salary_currency": job_data.get("salary_currency"),
            "salary_text": job_data.get("salary_text"),
            "url": job_data.get("url", ""),
            "apply_url": job_data.get("apply_url"),
            "posted_at": job_data.get("posted_at"),
            "raw_data": job_data.get("raw_data"),
        }

    def extract_skills(self, text: str) -> list[str]:
        """Extract skills from job description text."""
        if not text:
            return []

        # Common tech skills to look for
        skill_keywords = [
            "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
            "ruby", "php", "swift", "kotlin", "scala", "r",
            "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
            "spring", "rails", "laravel", "express",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "git", "linux", "ci/cd", "agile", "scrum",
            "machine learning", "deep learning", "nlp", "computer vision",
            "data science", "data engineering", "analytics",
            "sql", "nosql", "graphql", "rest api",
            "html", "css", "sass", "webpack",
        ]

        text_lower = text.lower()
        found_skills = []

        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title() if len(skill) > 3 else skill.upper())

        return list(set(found_skills))[:15]  # Limit to 15 skills

    def parse_salary(self, salary_text: str) -> tuple[int | None, int | None, str]:
        """Parse salary string into min, max, currency."""
        if not salary_text:
            return None, None, "USD"

        import re

        # Clean up text
        text = salary_text.upper().replace(",", "").replace(" ", "")

        # Try to find currency
        currency = "USD"
        if "EUR" in text or "€" in text:
            currency = "EUR"
        elif "GBP" in text or "£" in text:
            currency = "GBP"

        # Find numbers
        numbers = re.findall(r"\d+", text)
        numbers = [int(n) for n in numbers if len(n) >= 4]  # At least 4 digits for salary

        # Handle K notation (e.g., 100K)
        k_numbers = re.findall(r"(\d+)K", text)
        if k_numbers:
            numbers.extend([int(n) * 1000 for n in k_numbers])

        if not numbers:
            return None, None, currency

        numbers = sorted(set(numbers))

        if len(numbers) == 1:
            return numbers[0], numbers[0], currency
        elif len(numbers) >= 2:
            return numbers[0], numbers[-1], currency

        return None, None, currency
