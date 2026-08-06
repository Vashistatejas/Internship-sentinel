"""Ashby ATS scraper.

Ashby exposes a fully public, zero-auth JSON API at:
    https://api.ashbyhq.com/posting-api/job-board/{board-id}

The response has a top-level ``"jobs"`` array.  Each item contains a title,
apply URL, location, team, employment type, and a published-at timestamp.
``isRemote`` is a boolean flag available at the top level.

Every company on Ashby uses the same shape.  Adding a new Ashby company is a
config-only change.

To find the board-id: open the careers page in DevTools → Network → XHR.
You will see a request to ``api.ashbyhq.com/posting-api/job-board/<board-id>``.
"""

from __future__ import annotations

import json

from sentinel.models import JobPosting
from sentinel.scrapers.base import BaseScraper

_BASE = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyScraper(BaseScraper):
    """Scraper for any company whose careers page is hosted on Ashby."""

    def parse(self, raw: str) -> list[JobPosting]:
        """Parse the Ashby job-board API response."""
        payload = json.loads(raw)
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

        postings: list[JobPosting] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = (job.get("title") or "").strip()
            # Prefer the direct apply URL; fall back to the job listing URL.
            url = (job.get("applyUrl") or job.get("jobUrl") or "").strip()
            if not title or not url:
                continue

            # Build a human-readable location string.
            raw_location = (job.get("location") or "").strip()
            if job.get("isRemote") and not raw_location:
                raw_location = "Remote"
            elif job.get("isRemote"):
                raw_location = f"{raw_location} (Remote)"

            postings.append(
                JobPosting(
                    company=self.config.company,
                    title=title,
                    url=url,
                    job_id=str(job.get("id") or url),
                    source=self.source,
                    location=raw_location or None,
                    date_posted=job.get("publishedAt"),
                    description=job.get("team") or job.get("department"),
                )
            )
        return postings

    @staticmethod
    def board_url(board_id: str) -> str:
        """Return the canonical Ashby job-board URL for ``board_id``."""
        return f"{_BASE}/{board_id}"
