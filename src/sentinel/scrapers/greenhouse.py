"""Greenhouse ATS scraper.

Greenhouse exposes a fully public, zero-auth JSON API at:
    https://boards-api.greenhouse.io/v1/boards/{slug}/jobs

Every company on Greenhouse uses the exact same response shape, so this one
scraper class covers all of them.  Adding a new Greenhouse company is a
config-only change: add a ``"name": "greenhouse"`` entry with the company
slug in the ``url`` and that's it.

To find the slug for a company: open their careers page, look at the XHR
requests, or try ``https://boards-api.greenhouse.io/v1/boards/<slug>/jobs``
directly in a browser.  If it returns JSON with a ``"jobs"`` key, that's the
slug.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sentinel.models import JobPosting
from sentinel.scrapers.base import BaseScraper

_BASE = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseScraper(BaseScraper):
    """Scraper for any company whose careers page is hosted on Greenhouse."""

    def parse(self, raw: str) -> list[JobPosting]:
        """Parse the Greenhouse ``/jobs`` endpoint response."""
        payload = json.loads(raw)
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []

        postings: list[JobPosting] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = (job.get("title") or "").strip()
            url = (job.get("absolute_url") or "").strip()
            if not title or not url:
                continue

            location_obj = job.get("location") or {}
            location = (
                location_obj.get("name") if isinstance(location_obj, dict) else None
            )

            postings.append(
                JobPosting(
                    company=self.config.company,
                    title=title,
                    url=url,
                    job_id=str(job.get("id") or url),
                    source=self.source,
                    location=location or None,
                    date_posted=job.get("updated_at"),
                )
            )
        return postings

    @staticmethod
    def board_url(slug: str) -> str:
        """Return the canonical Greenhouse board URL for ``slug``."""
        return f"{_BASE}/{slug}/jobs"
