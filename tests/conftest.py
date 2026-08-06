"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.models import JobPosting

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_html() -> str:
    return (FIXTURES / "publicis_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_json() -> str:
    return (FIXTURES / "publicis_sample.json").read_text(encoding="utf-8")


@pytest.fixture
def sample_job() -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title="Associate Software Engineer Intern",
        url="https://careers.publicissapient.com/job-details/2026-100001",
        job_id="2026-100001",
        source="publicis_sapient",
        location="Bengaluru, India",
    )
