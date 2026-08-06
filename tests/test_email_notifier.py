"""Tests for email formatting and SMTP delivery (offline via a fake transport)."""

from __future__ import annotations

from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.email import (
    EmailNotifier,
    format_email_body,
    format_email_subject,
)


def _job() -> JobPosting:
    return JobPosting(
        company="Publicis Sapient",
        title="Software Engineer Intern",
        url="https://careers.publicissapient.com/job-details/2026-100001",
        job_id="2026-100001",
        source="ps",
        location="Bengaluru, India",
    )


def test_subject_contains_title_and_company() -> None:
    subject = format_email_subject(_job(), prefix="[Sentinel]")
    assert subject.startswith("[Sentinel]")
    assert "Software Engineer Intern" in subject
    assert "Publicis Sapient" in subject


def test_body_has_plain_and_html_with_key_fields() -> None:
    text, html_body = format_email_body(
        _job(), MatchResult(matched=True, reasons=["intern"])
    )
    for fragment in ("Software Engineer Intern", "Publicis Sapient", "Bengaluru"):
        assert fragment in text
        assert fragment in html_body
    assert "careers.publicissapient.com" in html_body
    assert "<html" in html_body


def test_html_body_escapes_markup() -> None:
    job = _job()
    job.title = "Intern <script> & Co"
    _text, html_body = format_email_body(job, MatchResult(matched=True))
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body


class _FakeSMTP:
    """Minimal stand-in for smtplib.SMTP supporting the context-manager API."""

    def __init__(self) -> None:
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent_messages: list = []

    def __enter__(self) -> "_FakeSMTP":
        return self

    def __exit__(self, *exc) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message) -> None:
        self.sent_messages.append(message)


def _notifier(fake: _FakeSMTP, *, use_tls: bool = True) -> EmailNotifier:
    return EmailNotifier(
        host="smtp.example.com",
        port=587,
        username="bot@example.com",
        password="secret",
        from_addr="bot@example.com",
        to_addrs=["me@example.com"],
        use_tls=use_tls,
        smtp_factory=lambda host, port, timeout: fake,
    )


def test_notify_sends_over_smtp() -> None:
    fake = _FakeSMTP()
    ok = _notifier(fake).notify(_job(), MatchResult(matched=True, reasons=["intern"]))

    assert ok is True
    assert fake.started_tls is True
    assert fake.logged_in == ("bot@example.com", "secret")
    assert len(fake.sent_messages) == 1

    message = fake.sent_messages[0]
    assert message["To"] == "me@example.com"
    assert message["From"] == "bot@example.com"
    assert "Software Engineer Intern" in message["Subject"]


def test_notify_skips_tls_when_disabled() -> None:
    fake = _FakeSMTP()
    _notifier(fake, use_tls=False).notify(_job(), MatchResult(matched=True))
    assert fake.started_tls is False
