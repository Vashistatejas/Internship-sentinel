"""Tests for the Ashby ATS scraper."""

from __future__ import annotations

from pathlib import Path

from sentinel.config import MatchConfig, ScraperConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.scrapers.ashby import AshbyScraper

FIXTURES = Path(__file__).parent / "fixtures"


def _scraper(company: str = "Linear") -> AshbyScraper:
    return AshbyScraper(
        ScraperConfig(
            name="ashby",
            company=company,
            url=AshbyScraper.board_url("linear"),
        )
    )


def _raw() -> str:
    return (FIXTURES / "ashby_sample.json").read_text(encoding="utf-8")


def test_parses_all_jobs() -> None:
    jobs = _scraper().parse(_raw())
    assert len(jobs) == 3


def test_fields_mapped_correctly() -> None:
    jobs = _scraper().parse(_raw())
    intern = next(j for j in jobs if j.title == "Software Engineer Intern")
    assert intern.job_id == "d3bc1ced-3ce4-4086-a050-555055dbb1ff"
    assert "Remote" in intern.location
    assert "ashbyhq.com" in str(intern.url)
    assert intern.description == "Engineering"
    assert intern.company == "Linear"
    assert intern.source == "ashby"


def test_remote_flag_appended_to_location() -> None:
    jobs = _scraper().parse(_raw())
    # "Product Design Intern" has empty location + isRemote=true
    design = next(j for j in jobs if "Design" in j.title)
    assert design.location == "Remote"


def test_matching_selects_interns_only() -> None:
    matcher = KeywordMatcher(
        MatchConfig(
            include_keywords=["intern", "internship"],
            exclude_keywords=["senior", "staff"],
            location_keywords=["remote", "india"],
        )
    )
    jobs = _scraper().parse(_raw())
    matched = [j for j in jobs if matcher.match(j).matched]
    titles = {j.title for j in matched}
    assert "Software Engineer Intern" in titles
    assert "Product Design Intern" in titles
    assert "Staff Infrastructure Engineer" not in titles


def test_empty_response_is_safe() -> None:
    assert _scraper().parse("{}") == []
    assert _scraper().parse('{"jobs": []}') == []
