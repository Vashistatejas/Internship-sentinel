"""Tests for the Lever ATS scraper."""

from __future__ import annotations

from pathlib import Path

from sentinel.config import MatchConfig, ScraperConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.scrapers.lever import LeverScraper

FIXTURES = Path(__file__).parent / "fixtures"


def _scraper(company: str = "CRED") -> LeverScraper:
    return LeverScraper(
        ScraperConfig(
            name="lever",
            company=company,
            url=LeverScraper.postings_url("cred"),
        )
    )


def _raw() -> str:
    return (FIXTURES / "lever_sample.json").read_text(encoding="utf-8")


def test_parses_all_jobs() -> None:
    jobs = _scraper().parse(_raw())
    assert len(jobs) == 3


def test_fields_mapped_correctly() -> None:
    jobs = _scraper().parse(_raw())
    intern = next(j for j in jobs if j.title == "Software Engineer Intern")
    assert intern.job_id == "09022710-e79a-4cf0-8060-df0e1cd64263"
    assert intern.location == "bengaluru"
    assert "lever.co" in str(intern.url)
    assert intern.description == "engineering"
    assert intern.date_posted is not None  # parsed from ms timestamp


def test_timestamp_to_iso() -> None:
    jobs = _scraper().parse(_raw())
    intern = next(j for j in jobs if j.title == "Software Engineer Intern")
    assert "2025" in intern.date_posted or "2026" in intern.date_posted


def test_matching_selects_interns_only() -> None:
    matcher = KeywordMatcher(
        MatchConfig(
            include_keywords=["intern", "internship"],
            exclude_keywords=["senior", "staff"],
            location_keywords=["india", "bengaluru", "mumbai", "remote"],
        )
    )
    jobs = _scraper().parse(_raw())
    matched = [j for j in jobs if matcher.match(j).matched]
    titles = {j.title for j in matched}
    assert "Software Engineer Intern" in titles
    assert "Data Science Intern" in titles
    assert "Senior Backend Engineer" not in titles


def test_empty_response_is_safe() -> None:
    assert _scraper().parse("[]") == []
