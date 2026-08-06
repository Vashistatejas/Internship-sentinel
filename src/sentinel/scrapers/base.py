"""Base scraper interface.

A scraper has two responsibilities that are intentionally kept separate:

* :meth:`fetch_raw` — perform network I/O and return the raw payload.
* :meth:`parse` — turn a raw payload into :class:`JobPosting` objects.

Keeping ``parse`` free of network access is what makes scrapers testable with
saved fixtures. :meth:`scrape` simply composes the two.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from sentinel.config import ScraperConfig
from sentinel.models import JobPosting

# Realistic browser headers. Many career sites sit behind CDNs (e.g.
# CloudFront) that reject obviously non-browser requests.
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BaseScraper(ABC):
    """Abstract base for all company scrapers."""

    def __init__(self, config: ScraperConfig, *, timeout: int = 20) -> None:
        self.config = config
        self.timeout = timeout

    @property
    def source(self) -> str:
        """Identifier stored on every posting this scraper produces."""
        return self.config.name

    def fetch_raw(self, *, session: requests.Session | None = None) -> str:
        """Fetch the raw response body from the configured URL.

        Args:
            session: Optional shared session (allows connection reuse/testing).

        Returns:
            The response body as text.

        Raises:
            requests.HTTPError: If the server responds with an error status.
        """
        headers = {**DEFAULT_HEADERS, **self.config.headers}
        client = session or requests
        response = client.get(
            self.config.url,
            params=self.config.params or None,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    @abstractmethod
    def parse(self, raw: str) -> list[JobPosting]:
        """Parse a raw payload into postings. Must not perform network I/O."""

    def scrape(self, *, session: requests.Session | None = None) -> list[JobPosting]:
        """Fetch then parse. Convenience composition of the two steps."""
        return self.parse(self.fetch_raw(session=session))
