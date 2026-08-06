"""Monitoring orchestration.

:class:`MonitorService` wires the pieces together via composition: it receives
a list of scrapers, a matcher, a state store, and a list of notifiers. This is
the only place the end-to-end flow lives:

    scrape → match → deduplicate → notify → persist state

Adding a company (new scraper) or channel (new notifier) means passing a longer
list here — the flow itself does not change.
"""

from __future__ import annotations

import logging

import requests
from pydantic import BaseModel, Field

from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.base import Notifier
from sentinel.persistence.state_store import JsonStateStore
from sentinel.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RunSummary(BaseModel):
    """Aggregate result of a single monitoring run (useful for logs/tests)."""

    scraped: int = 0
    matched: int = 0
    new_alerts: int = 0
    errors: list[str] = Field(default_factory=list)


class MonitorService:
    """Coordinate the full monitor cycle across scrapers and notifiers."""

    def __init__(
        self,
        scrapers: list[BaseScraper],
        matcher: KeywordMatcher,
        state: JsonStateStore,
        notifiers: list[Notifier],
        *,
        session: requests.Session | None = None,
    ) -> None:
        self._scrapers = scrapers
        self._matcher = matcher
        self._state = state
        self._notifiers = notifiers
        self._session = session

    def run(self) -> RunSummary:
        """Execute one monitoring cycle and return a summary."""
        self._state.load()
        summary = RunSummary()

        for scraper in self._scrapers:
            jobs = self._safe_scrape(scraper, summary)
            summary.scraped += len(jobs)
            for job in jobs:
                self._process_job(job, summary)

        self._state.save()
        logger.info(
            "run complete: scraped=%d matched=%d new_alerts=%d errors=%d",
            summary.scraped,
            summary.matched,
            summary.new_alerts,
            len(summary.errors),
        )
        return summary

    def _safe_scrape(
        self, scraper: BaseScraper, summary: RunSummary
    ) -> list[JobPosting]:
        """Scrape one source, isolating failures so others still run."""
        try:
            return scraper.scrape(session=self._session)
        except Exception as exc:  # noqa: BLE001 — one bad source must not stop all
            message = f"{scraper.source}: {exc}"
            logger.warning("scrape failed for %s", message)
            summary.errors.append(message)
            return []

    def _process_job(self, job: JobPosting, summary: RunSummary) -> None:
        """Match, deduplicate, and notify for a single posting."""
        result = self._matcher.match(job)
        if not result.matched:
            return
        summary.matched += 1

        if self._state.is_seen(job):
            return  # Already alerted in a previous run.

        # Only record a job as seen once it has actually been delivered. This
        # keeps --dry-run (no notifiers) from consuming alerts, and lets failed
        # sends retry on the next run instead of being silently swallowed.
        if self._dispatch(job, result):
            summary.new_alerts += 1
            self._state.mark_seen(job)
        else:
            logger.warning(
                "no channel delivered alert for %s; will retry next run",
                job.dedup_key,
            )

    def _dispatch(self, job: JobPosting, result: MatchResult) -> bool:
        """Send an alert to every notifier. Returns True if any succeeded."""
        delivered = False
        for notifier in self._notifiers:
            try:
                if notifier.notify(job, result):
                    delivered = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("notify failed on %s: %s", notifier.name, exc)
        return delivered
