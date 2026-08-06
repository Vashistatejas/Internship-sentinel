"""Typed configuration loading.

Configuration is split into two sources so that secrets never live in code or
in version control:

* ``config/config.json`` — non-secret targets: which companies to scrape,
  which keywords count as a match, and channel toggles.
* Environment variables (loaded from ``.env`` locally, or GitHub secrets in
  CI) — credentials such as the Telegram bot token and chat id.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration for a single company scraper.

    Attributes:
        name: Unique scraper identifier, matched to a registered scraper class.
        company: Display name used on postings and alerts.
        enabled: Whether this scraper runs.
        url: Endpoint to fetch (HTML page or JSON API).
        mode: ``"json"`` or ``"html"`` — how to parse the response.
        params: Query-string parameters sent with the request.
        headers: Extra HTTP headers (merged over sensible browser defaults).
    """

    name: str
    company: str
    enabled: bool = True
    url: str
    mode: str = "html"
    params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)


class MatchConfig(BaseModel):
    """Keyword rules that decide whether a posting is relevant.

    All keyword comparisons are case-insensitive.
    """

    include_keywords: list[str] = Field(default_factory=list)
    require_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    location_keywords: list[str] = Field(default_factory=list)


class TelegramConfig(BaseModel):
    """Telegram channel settings and resolved credentials."""

    enabled: bool = True
    bot_token: str | None = None
    chat_id: str | None = None

    @property
    def is_ready(self) -> bool:
        """True when both credentials are present."""
        return bool(self.bot_token and self.chat_id)


class EmailConfig(BaseModel):
    """Email (SMTP) channel settings and resolved credentials.

    Connection credentials (``host``/``port``/``username``/``password``) are
    resolved from environment variables so they never live in the repo. The
    non-secret bits (recipients, subject prefix, TLS toggle) come from the
    JSON config file.
    """

    enabled: bool = False
    host: str | None = None
    port: int = 587
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    from_addr: str | None = None
    to_addrs: list[str] = Field(default_factory=list)
    subject_prefix: str = "[Internship Sentinel]"

    @property
    def sender(self) -> str | None:
        """Effective From address (defaults to the SMTP username)."""
        return self.from_addr or self.username

    @property
    def is_ready(self) -> bool:
        """True when everything needed to send is present."""
        return bool(self.host and self.username and self.password and self.to_addrs)


class AppConfig(BaseModel):
    """Top-level application configuration."""

    scrapers: list[ScraperConfig]
    matching: MatchConfig
    telegram: TelegramConfig
    email: EmailConfig
    state_path: str = "data/state.json"
    request_timeout: int = 20


def load_config(
    config_path: str | Path = "config/config.json",
    *,
    load_env: bool = True,
) -> AppConfig:
    """Load and validate application configuration.

    Args:
        config_path: Path to the JSON config file.
        load_env: When True, load a local ``.env`` file before reading secrets.

    Returns:
        A fully populated :class:`AppConfig`.
    """
    if load_env:
        load_dotenv()

    path = Path(config_path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    telegram_raw = raw.get("telegram", {})
    telegram = TelegramConfig(
        enabled=telegram_raw.get("enabled", False),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )

    email_raw = raw.get("email", {})
    email = EmailConfig(
        enabled=email_raw.get("enabled", False),
        host=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USERNAME"),
        password=os.getenv("SMTP_PASSWORD"),
        use_tls=email_raw.get("use_tls", True),
        from_addr=email_raw.get("from_addr"),
        to_addrs=email_raw.get("to_addrs", []),
        subject_prefix=email_raw.get("subject_prefix", "[Internship Sentinel]"),
    )

    return AppConfig(
        scrapers=[ScraperConfig(**s) for s in raw.get("scrapers", [])],
        matching=MatchConfig(**raw.get("matching", {})),
        telegram=telegram,
        email=email,
        state_path=raw.get("state_path", "data/state.json"),
        request_timeout=raw.get("request_timeout", 20),
    )
