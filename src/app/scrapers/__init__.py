"""Job scrapers module."""

from app.scrapers.base import BaseScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.github_jobs import GitHubJobsScraper

__all__ = ["BaseScraper", "RemoteOKScraper", "GitHubJobsScraper"]
