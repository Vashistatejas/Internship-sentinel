"""Email (SMTP) notification channel.

Sends alerts as multipart plain-text + HTML email using Python's built-in
``smtplib`` and ``email`` libraries (no extra dependency). Message building is
split into pure functions (:func:`format_email_subject`, :func:`format_email_body`)
so formatting is unit tested without any network or credentials.

The SMTP connection is created through an injectable factory, which lets tests
substitute a fake transport and verify behaviour offline.
"""

from __future__ import annotations

import html
import smtplib
from email.message import EmailMessage
from typing import Callable

from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.base import Notifier

# Factory: (host, port, timeout) -> object behaving like smtplib.SMTP.
SmtpFactory = Callable[[str, int, int], smtplib.SMTP]


def _default_smtp_factory(host: str, port: int, timeout: int) -> smtplib.SMTP:
    return smtplib.SMTP(host, port, timeout=timeout)


def format_email_subject(job: JobPosting, prefix: str = "[Internship Sentinel]") -> str:
    """Build the email subject line."""
    return f"{prefix} {job.title} — {job.company}".strip()


def format_email_body(job: JobPosting, match: MatchResult) -> tuple[str, str]:
    """Build ``(plain_text, html)`` bodies for a posting.

    Returns both so email clients can pick the richest one they support.
    """
    location = job.location or "Location not specified"
    why = match.why()
    url = str(job.url)

    text = "\n".join(
        [
            "New internship match",
            "",
            f"Title:    {job.title}",
            f"Company:  {job.company}",
            f"Location: {location}",
            f"Why:      {why}",
            "",
            f"Apply:    {url}",
        ]
    )

    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #222;">
    <h2 style="margin-bottom: 4px;">🚨 New internship match</h2>
    <table cellpadding="4" style="border-collapse: collapse;">
      <tr><td><b>Title</b></td><td>{html.escape(job.title)}</td></tr>
      <tr><td><b>Company</b></td><td>{html.escape(job.company)}</td></tr>
      <tr><td><b>Location</b></td><td>{html.escape(location)}</td></tr>
      <tr><td><b>Why</b></td><td>{html.escape(why)}</td></tr>
    </table>
    <p style="margin-top: 16px;">
      <a href="{html.escape(url)}"
         style="background:#2563eb;color:#fff;padding:10px 16px;
                text-decoration:none;border-radius:6px;">View &amp; apply</a>
    </p>
  </body>
</html>"""
    return text, html_body


class EmailNotifier(Notifier):
    """Deliver alerts by email over SMTP."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
        subject_prefix: str = "[Internship Sentinel]",
        timeout: int = 20,
        smtp_factory: SmtpFactory = _default_smtp_factory,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._to_addrs = to_addrs
        self._use_tls = use_tls
        self._subject_prefix = subject_prefix
        self._timeout = timeout
        self._smtp_factory = smtp_factory

    @property
    def name(self) -> str:
        return "email"

    def build_message(self, job: JobPosting, match: MatchResult) -> EmailMessage:
        """Assemble the multipart email message (no sending)."""
        subject = format_email_subject(job, self._subject_prefix)
        text_body, html_body = format_email_body(job, match)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._from_addr
        message["To"] = ", ".join(self._to_addrs)
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
        return message

    def notify(self, job: JobPosting, match: MatchResult) -> bool:
        """Send an alert email. Returns True once the message is handed off."""
        message = self.build_message(job, match)
        with self._smtp_factory(self._host, self._port, self._timeout) as server:
            if self._use_tls:
                server.starttls()
            server.login(self._username, self._password)
            server.send_message(message)
        return True
