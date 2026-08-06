"""Tests for the shared data models and dedup key behaviour."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentinel.models import JobPosting, MatchResult


def _job(**overrides) -> JobPosting:
    base = dict(
        company="Publicis Sapient",
        title="Software Engineer Intern",
        url="https://careers.publicissapient.com/job-details/2026-100001",
        job_id="2026-100001",
        source="ps",
    )
    base.update(overrides)
    return JobPosting(**base)


def test_dedup_key_uses_job_id_scoped_by_company() -> None:
    assert _job().dedup_key == "publicis sapient:2026-100001"


def test_dedup_key_stable_across_instances() -> None:
    assert _job().dedup_key == _job().dedup_key


def test_blank_required_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _job(title="   ")


def test_invalid_url_rejected() -> None:
    with pytest.raises(ValidationError):
        _job(url="not-a-url")


def test_match_result_why_default() -> None:
    assert MatchResult(matched=True).why()
    assert "intern" in MatchResult(matched=True, reasons=["intern"]).why()
