"""Publicis Sapient career-page scraper.

The Publicis Sapient careers site (``careers.publicissapient.com``) runs on the
Radancy TalentBrew platform and sits behind a CDN that rejects non-browser
requests. This scraper therefore:

* sends realistic browser headers (handled by :class:`BaseScraper`), and
* delegates all parsing to the pure functions in :mod:`sentinel.scrapers.parsers`
  so behaviour can be verified against saved fixtures regardless of the live
  site's availability.

The response ``mode`` (``"json"`` vs ``"html"``) and the request URL/params are
configuration-driven, so adapting to endpoint changes needs no code edits.
"""

from __future__ import annotations

from urllib.parse import urlparse

from sentinel.models import JobPosting
from sentinel.scrapers.base import BaseScraper
from sentinel.scrapers.parsers import parse_html_jobs, parse_publicis_json


class PublicisSapientScraper(BaseScraper):
    """Scraper for Publicis Sapient internship listings."""

    def _base_url(self) -> str:
        """Origin used to absolutise relative links found in the payload."""
        parsed = urlparse(self.config.url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def parse(self, raw: str) -> list[JobPosting]:
        """Parse the fetched payload according to the configured mode."""
        company = self.config.company
        base_url = self._base_url()

        if self.config.mode == "json":
            return parse_publicis_json(
                raw,
                company=company,
                source=self.source,
                base_url=base_url,
            )
        return parse_html_jobs(
            raw,
            company=company,
            source=self.source,
            base_url=base_url,
        )
