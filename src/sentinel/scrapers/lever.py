"""Lever ATS scraper.

Lever exposes a fully public, zero-auth JSON API at:
    https://api.lever.co/v0/postings/{company}?mode=json

The response is a flat JSON array of postings (no wrapper object).  Each item
contains the role text (title), a hosted apply URL, and a ``categories`` object
with location and team information.

Every company on Lever uses the same shape, so this one class covers them all.
Adding a new Lever company = one config entry.

To find the company identifier: open the careers page, look at the network
request, or try ``https://api.lever.co/v0/postings/<identifier>?mode=json``
in a browser.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sentinel.models import JobPosting
from sentinel.scrapers.base import BaseScraper

_BASE = "https://api.lever.co/v0/postings"


class LeverScraper(BaseScraper):
    """Scraper for any company whose careers page is hosted on Lever."""

    def parse(self, raw: str) -> list[JobPosting]:
        """Parse the Lever postings JSON array."""
        payload = json.loads(raw)
        # Lever returns a bare list; also handle error objects gracefully.
        jobs = payload if isinstance(payload, list) else []

        postings: list[JobPosting] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = (job.get("text") or "").strip()
            url = (job.get("hostedUrl") or "").strip()
            if not title or not url:
                continue

            categories = job.get("categories") or {}
            location = (
                categories.get("location") or categories.get("allLocations")
            )
            if isinstance(location, list):
                location = ", ".join(location)

            # createdAt is a Unix timestamp in milliseconds.
            created_ms = job.get("createdAt")
            date_posted: str | None = None
            if isinstance(created_ms, (int, float)):
                date_posted = datetime.fromtimestamp(
                    created_ms / 1000, tz=timezone.utc
                ).isoformat()

            postings.append(
                JobPosting(
                    company=self.config.company,
                    title=title,
                    url=url,
                    job_id=str(job.get("id") or url),
                    source=self.source,
                    location=location or None,
                    date_posted=date_posted,
                    description=categories.get("team") or categories.get("department"),
                )
            )
        return postings

    @staticmethod
    def postings_url(company: str) -> str:
        """Return the canonical Lever postings URL for ``company``."""
        return f"{_BASE}/{company}?mode=json"
