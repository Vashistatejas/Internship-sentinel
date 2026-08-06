"""Notifier interface.

Every channel (Telegram now; email, Discord, Slack later) implements the same
small contract so the service layer can fan out to any number of channels
without special-casing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sentinel.models import JobPosting, MatchResult


class Notifier(ABC):
    """Abstract alert channel."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short channel identifier used in logs."""

    @abstractmethod
    def notify(self, job: JobPosting, match: MatchResult) -> bool:
        """Send an alert for a single posting.

        Returns:
            True if the alert was accepted by the channel, else False.
        """
