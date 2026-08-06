"""Tests for the Publicis Sapient careers-API JSON parser."""

from __future__ import annotations

from pathlib import Path

from sentinel.config import MatchConfig
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.scrapers.parsers import parse_publicis_json

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://careers.publicissapient.com"


def _raw() -> str:
    return (FIXTURES / "publicis_api_sample.json").read_text(encoding="utf-8")


def test_parses_nested_response_docs() -> None:
    jobs = parse_publicis_json(
        _raw(), company="Publicis Sapient", source="publicis_sapient", base_url=BASE
    )
    assert len(jobs) == 3
    intern = next(j for j in jobs if j.job_id == "2026-145010")
    assert intern.title == "Software Engineer Intern"
    assert str(intern.url) == (
        BASE + "/job-details/2026-145010-software-engineer-intern-bengaluru"
    )
    assert intern.location == "Bengaluru, Karnataka, India"
    assert intern.description == "Entry Level"  # experienceLevel folded in


def test_matching_selects_india_internships_only() -> None:
    jobs = parse_publicis_json(
        _raw(), company="Publicis Sapient", source="publicis_sapient", base_url=BASE
    )
    matcher = KeywordMatcher(
        MatchConfig(
            include_keywords=["intern", "internship"],
            exclude_keywords=["manager", "senior"],
            location_keywords=["india", "bengaluru"],
        )
    )
    matched = [j for j in jobs if matcher.match(j).matched]

    # Only the Bengaluru intern qualifies: the manager is excluded, and the
    # London intern fails the location gate.
    assert [j.job_id for j in matched] == ["2026-145010"]


def test_empty_or_missing_response_is_safe() -> None:
    assert parse_publicis_json("{}", company="C", source="s") == []
    assert parse_publicis_json(
        '{"response": {"docs": []}}', company="C", source="s"
    ) == []
