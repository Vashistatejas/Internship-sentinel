"""Tests for notification formatting and Telegram delivery."""

from __future__ import annotations

from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.telegram import TelegramNotifier, format_job_alert


def _job() -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title="Software Engineer Intern",
        url="https://careers.publicissapient.com/job-details/2026-100001",
        job_id="2026-100001",
        source="ps",
        location="Bengaluru, India",
    )


def test_format_includes_key_fields() -> None:
    message = format_job_alert(_job(), MatchResult(matched=True, reasons=["intern"]))
    assert "Software Engineer Intern" in message
    assert "Publicis Sapient" in message
    assert "Bengaluru, India" in message
    assert "careers.publicissapient.com" in message
    assert "intern" in message  # the "why matched" note


def test_format_escapes_html() -> None:
    job = _job()
    job.title = "Intern <script> & Co"
    message = format_job_alert(job, MatchResult(matched=True))
    assert "<script>" not in message
    assert "&lt;script&gt;" in message


class _FakeResponse:
    def __init__(self, ok: bool) -> None:
        self.ok = ok


class _FakeSession:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[dict] = []

    def post(self, url: str, json: dict, timeout: int) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(self.ok)


def test_telegram_posts_to_bot_api() -> None:
    session = _FakeSession(ok=True)
    notifier = TelegramNotifier("TOKEN", "CHAT", session=session)
    ok = notifier.notify(_job(), MatchResult(matched=True))

    assert ok is True
    assert len(session.calls) == 1
    call = session.calls[0]
    assert "botTOKEN/sendMessage" in call["url"]
    assert call["json"]["chat_id"] == "CHAT"
    assert call["json"]["parse_mode"] == "HTML"


def test_telegram_reports_failure() -> None:
    notifier = TelegramNotifier("T", "C", session=_FakeSession(ok=False))
    assert notifier.notify(_job(), MatchResult(matched=True)) is False
