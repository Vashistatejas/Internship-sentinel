"""Tests for keyword matching."""

from __future__ import annotations

from sentinel.config import MatchConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.models import JobPosting


def _job(title: str, location: str = "Bengaluru, India") -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title=title,
        url="https://careers.publicissapient.com/job-details/x",
        job_id="x",
        source="ps",
        location=location,
    )


def _matcher() -> KeywordMatcher:
    return KeywordMatcher(
        MatchConfig(
            include_keywords=["intern", "internship"],
            exclude_keywords=["senior", "manager"],
            location_keywords=["india", "remote"],
        )
    )


def test_matches_intern_in_india() -> None:
    result = _matcher().match(_job("Software Engineer Intern"))
    assert result.matched is True
    assert result.why()


def test_excludes_senior_roles() -> None:
    result = _matcher().match(_job("Senior Software Engineer Intern"))
    assert result.matched is False
    assert "excluded" in result.why()


def test_rejects_when_no_include_keyword() -> None:
    result = _matcher().match(_job("Software Engineer"))
    assert result.matched is False


def test_rejects_wrong_location() -> None:
    result = _matcher().match(_job("Engineering Intern", location="London, UK"))
    assert result.matched is False
    assert "location" in result.why()


def test_require_keywords_enforced() -> None:
    matcher = KeywordMatcher(
        MatchConfig(require_keywords=["software"], include_keywords=["intern"])
    )
    assert matcher.match(_job("Marketing Intern")).matched is False
    assert matcher.match(_job("Software Intern")).matched is True
