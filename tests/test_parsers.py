"""Tests for the pure parsing functions (job parsing)."""

from __future__ import annotations

from sentinel.scrapers.parsers import parse_html_jobs, parse_json_jobs

BASE = "https://careers.publicissapient.com"


def test_parse_html_extracts_job_cards(sample_html: str) -> None:
    jobs = parse_html_jobs(
        sample_html, company="Publicis Sapient", source="ps", base_url=BASE
    )
    titles = {j.title for j in jobs}

    # Four job-details links; nav links (early-career/internships) excluded.
    assert len(jobs) == 4
    assert "Associate Software Engineer Intern" in titles
    assert "Early Career" not in titles


def test_parse_html_absolutises_urls_and_ids(sample_html: str) -> None:
    jobs = parse_html_jobs(
        sample_html, company="Publicis Sapient", source="ps", base_url=BASE
    )
    first = next(j for j in jobs if "Associate" in j.title)
    assert str(first.url).startswith(BASE)
    assert first.job_id  # slug-derived id
    assert first.location == "Bengaluru, India"


def test_parse_json_reads_nested_location(sample_json: str) -> None:
    jobs = parse_json_jobs(
        sample_json, company="Publicis Sapient", source="ps", base_url=BASE
    )
    assert len(jobs) == 3
    intern = next(j for j in jobs if j.job_id == "2026-100001")
    assert intern.location == "Bengaluru"
    assert intern.date_posted == "2026-07-28"
    assert str(intern.url).startswith(BASE)


def test_parse_json_skips_entries_missing_required_fields() -> None:
    raw = '{"jobs": [{"title": "No URL Here"}, {"url": "/x"}]}'
    jobs = parse_json_jobs(raw, company="C", source="s", base_url=BASE)
    assert jobs == []


def test_parse_html_handles_empty_input() -> None:
    assert parse_html_jobs("", company="C", source="s") == []
