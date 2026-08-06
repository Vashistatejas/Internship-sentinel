"""Tests for JSON state read/write and duplicate detection."""

from __future__ import annotations

from pathlib import Path

from sentinel.models import JobPosting
from sentinel.persistence.state_store import JsonStateStore


def _job(job_id: str = "2026-100001") -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title="Software Engineer Intern",
        url=f"https://careers.publicissapient.com/job-details/{job_id}",
        job_id=job_id,
        source="ps",
    )


def test_new_job_is_not_seen(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    assert store.is_seen(_job()) is False


def test_mark_and_persist_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = JsonStateStore(path)
    store.mark_seen(_job())
    store.save()

    # Fresh store loading the same file must remember the job.
    reloaded = JsonStateStore(path)
    assert reloaded.is_seen(_job()) is True
    assert reloaded.seen_count == 1


def test_duplicate_marking_is_idempotent(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    store.mark_seen(_job())
    store.mark_seen(_job())
    assert store.seen_count == 1


def test_corrupt_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = JsonStateStore(path)
    store.load()
    assert store.seen_count == 0


def test_different_jobs_tracked_separately(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    store.mark_seen(_job("A"))
    store.mark_seen(_job("B"))
    assert store.seen_count == 2
