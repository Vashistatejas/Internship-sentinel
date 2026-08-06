"""Tests for the Greenhouse ATS scraper."""

from __future__ import annotations

from pathlib import Path

from sentinel.config import MatchConfig, ScraperConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.scrapers.greenhouse import GreenhouseScraper

FIXTURES = Path(__file__).parent / "fixtures"


def _scraper(company: str = "Postman") -> GreenhouseScraper:
    return GreenhouseScraper(
        ScraperConfig(
            name="greenhouse",
            company=company,
            url=GreenhouseScraper.board_url("postman"),
        )
    )


def _raw() -> str:
    return (FIXTURES / "greenhouse_sample.json").read_text(encoding="utf-8")


def test_parses_all_jobs() -> None:
    jobs = _scraper().parse(_raw())
    assert len(jobs) == 3


def test_fields_mapped_correctly() -> None:
    jobs = _scraper().parse(_raw())
    intern = next(j for j in jobs if "Intern" in j.title and "Software" in j.title)
    assert intern.title == "Software Engineer Intern"
    assert intern.job_id == "7762097003"
    assert intern.location == "Bengaluru, India"
    assert "greenhouse.io" in str(intern.url)
    assert intern.company == "Postman"
    assert intern.source == "greenhouse"


def test_matching_selects_interns_only() -> None:
    matcher = KeywordMatcher(
        MatchConfig(
            include_keywords=["intern", "internship"],
            exclude_keywords=["senior", "staff"],
            location_keywords=["india", "remote", "bengaluru"],
        )
    )
    jobs = _scraper().parse(_raw())
    matched = [j for j in jobs if matcher.match(j).matched]
    titles = {j.title for j in matched}
    assert "Software Engineer Intern" in titles
    assert "Product Manager Intern" in titles
    assert "Senior Software Engineer" not in titles


def test_empty_response_is_safe() -> None:
    assert _scraper().parse("{}") == []
    assert _scraper().parse('{"jobs": []}') == []
