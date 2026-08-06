"""Telegram notification channel.

Sends alerts via the Telegram Bot API. Message formatting is a standalone,
pure function (:func:`format_job_alert`) so it can be unit tested without any
network access or credentials.
"""

from __future__ import annotations

import html

import requests

from sentinel.models import JobPosting, MatchResult
from sentinel.notifiers.base import Notifier

_API_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"


def format_job_alert(job: JobPosting, match: MatchResult) -> str:
    """Build an HTML-formatted Telegram message for a posting.

    Includes title, company, location, a "why this matched" note, and the link.
    """
    title = html.escape(job.title)
    company = html.escape(job.company)
    location = html.escape(job.location or "Location not specified")
    why = html.escape(match.why())

    lines = [
        "🚨 <b>New internship match</b>",
        "",
        f"<b>{title}</b>",
        f"🏢 {company}",
        f"📍 {location}",
        f"✅ Why: {why}",
        "",
        f'🔗 <a href="{html.escape(str(job.url))}">View & apply</a>',
    ]
    return "\n".join(lines)


class TelegramNotifier(Notifier):
    """Deliver alerts to a Telegram chat via a bot."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        *,
        timeout: int = 15,
        session: requests.Session | None = None,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout
        self._session = session or requests

    @property
    def name(self) -> str:
        return "telegram"

    def notify(self, job: JobPosting, match: MatchResult) -> bool:
        """Send a formatted alert. Returns True on HTTP success."""
        message = format_job_alert(job, match)
        response = self._session.post(
            _API_TEMPLATE.format(token=self._token),
            json={
                "chat_id": self._chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=self._timeout,
        )
        return response.ok
