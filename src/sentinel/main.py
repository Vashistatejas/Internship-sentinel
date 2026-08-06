"""Entry point: build the monitor from configuration and run one cycle.

Usage:
    python -m sentinel.main [--config config/config.json] [--dry-run]

``--dry-run`` scrapes and matches but sends nothing, which is handy for local
testing and for the manual GitHub Actions trigger.
"""

from __future__ import annotations

import argparse
import logging
import sys

from sentinel.config import AppConfig, load_config
from sentinel.matchers.keyword_matcher import KeywordMatcher
from sentinel.notifiers.base import Notifier
from sentinel.notifiers.email import EmailNotifier
from sentinel.notifiers.telegram import TelegramNotifier
from sentinel.persistence.state_store import JsonStateStore
from sentinel.scrapers import SCRAPER_REGISTRY
from sentinel.scrapers.base import BaseScraper
from sentinel.services.monitor import MonitorService, RunSummary


def build_scrapers(config: AppConfig) -> list[BaseScraper]:
    """Instantiate enabled scrapers from config using the registry."""
    scrapers: list[BaseScraper] = []
    for spec in config.scrapers:
        if not spec.enabled:
            continue
        scraper_cls = SCRAPER_REGISTRY.get(spec.name)
        if scraper_cls is None:
            logging.warning("no scraper registered for '%s' — skipping", spec.name)
            continue
        scrapers.append(scraper_cls(spec, timeout=config.request_timeout))
    return scrapers


def build_notifiers(config: AppConfig, *, dry_run: bool) -> list[Notifier]:
    """Instantiate enabled notifiers. Empty in dry-run mode."""
    if dry_run:
        return []
    notifiers: list[Notifier] = []

    if config.email.enabled:
        if config.email.is_ready:
            notifiers.append(
                EmailNotifier(
                    host=config.email.host,  # type: ignore[arg-type]
                    port=config.email.port,
                    username=config.email.username,  # type: ignore[arg-type]
                    password=config.email.password,  # type: ignore[arg-type]
                    from_addr=config.email.sender,  # type: ignore[arg-type]
                    to_addrs=config.email.to_addrs,
                    use_tls=config.email.use_tls,
                    subject_prefix=config.email.subject_prefix,
                    timeout=config.request_timeout,
                )
            )
        else:
            logging.warning(
                "Email enabled but configuration incomplete "
                "(need SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD env vars and "
                "email.to_addrs in config) — no alerts will send"
            )

    if config.telegram.enabled:
        if config.telegram.is_ready:
            notifiers.append(
                TelegramNotifier(
                    bot_token=config.telegram.bot_token,  # type: ignore[arg-type]
                    chat_id=config.telegram.chat_id,  # type: ignore[arg-type]
                )
            )
        else:
            logging.warning(
                "Telegram enabled but credentials missing "
                "(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) — no alerts will send"
            )

    if not notifiers:
        logging.warning("no notification channels are active")
    return notifiers


def run(config_path: str, *, dry_run: bool) -> RunSummary:
    """Build and execute a single monitoring cycle."""
    config = load_config(config_path)
    service = MonitorService(
        scrapers=build_scrapers(config),
        matcher=KeywordMatcher(config.matching),
        state=JsonStateStore(config.state_path),
        notifiers=build_notifiers(config, dry_run=dry_run),
    )
    return service.run()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Internship Sentinel monitor")
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="scrape and match but do not send notifications",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    summary = run(args.config, dry_run=args.dry_run)
    print(
        f"scraped={summary.scraped} matched={summary.matched} "
        f"new_alerts={summary.new_alerts} errors={len(summary.errors)}"
    )
    for err in summary.errors:
        print(f"  error: {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
