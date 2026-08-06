"""End-to-end orchestration tests: scrape → match → dedup → notify."""

from __future__ import annotations

from pathlib import Path

from sentinel.config import MatchConfig, ScraperConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.base import Notifier
from sentinel.persistence.state_store import JsonStateStore
from sentinel.scrapers.base import BaseScraper
from sentinel.services.monitor import MonitorService


class _StubScraper(BaseScraper):
    def __init__(self, jobs: list[JobPosting]) -> None:
        super().__init__(ScraperConfig(name="stub", company="C", url="https://x/y"))
        self._jobs = jobs

    def fetch_raw(self, *, session=None) -> str:  # pragma: no cover - unused
        return ""

    def parse(self, raw: str) -> list[JobPosting]:  # pragma: no cover - unused
        return self._jobs

    def scrape(self, *, session=None) -> list[JobPosting]:
        return self._jobs


class _RecordingNotifier(Notifier):
    def __init__(self) -> None:
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "recording"

    def notify(self, job: JobPosting, match: MatchResult) -> bool:
        self.sent.append(job.job_id)
        return True


def _job(job_id: str, title: str = "Software Engineer Intern") -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title=title,
        url=f"https://careers.publicissapient.com/job-details/{job_id}",
        job_id=job_id,
        source="stub",
        location="Bengaluru, India",
    )


def _matcher() -> KeywordMatcher:
    return KeywordMatcher(
        MatchConfig(include_keywords=["intern"], location_keywords=["india"])
    )


def test_only_matching_jobs_alerted(tmp_path: Path) -> None:
    scraper = _StubScraper([_job("1"), _job("2", title="Senior Engineer")])
    notifier = _RecordingNotifier()
    service = MonitorService(
        [scraper], _matcher(), JsonStateStore(tmp_path / "s.json"), [notifier]
    )
    summary = service.run()

    assert summary.new_alerts == 1
    assert notifier.sent == ["1"]


def test_no_duplicate_alerts_across_runs(tmp_path: Path) -> None:
    path = tmp_path / "s.json"
    scraper = _StubScraper([_job("1")])
    notifier = _RecordingNotifier()

    MonitorService([scraper], _matcher(), JsonStateStore(path), [notifier]).run()
    # Second run with the same posting must not re-alert.
    MonitorService([scraper], _matcher(), JsonStateStore(path), [notifier]).run()

    assert notifier.sent == ["1"]


def test_scraper_error_is_isolated(tmp_path: Path) -> None:
    class _BoomScraper(_StubScraper):
        def scrape(self, *, session=None):
            raise RuntimeError("network down")

    good = _StubScraper([_job("1")])
    bad = _BoomScraper([])
    notifier = _RecordingNotifier()
    service = MonitorService(
        [bad, good], _matcher(), JsonStateStore(tmp_path / "s.json"), [notifier]
    )
    summary = service.run()

    assert summary.new_alerts == 1
    assert len(summary.errors) == 1
