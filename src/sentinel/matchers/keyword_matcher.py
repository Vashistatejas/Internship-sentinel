"""Keyword-based relevance matching.

The matcher is intentionally simple and rule-driven so its behaviour is fully
configurable (see :class:`sentinel.config.MatchConfig`). A future smarter
matcher (embeddings, resume similarity, scoring) can implement the same
``match`` shape and be swapped in without touching the service layer.
"""

from __future__ import annotations

from sentinel.config import MatchConfig
from sentinel.models import JobPosting, MatchResult


class KeywordMatcher:
    """Match postings against include/require/exclude/location keyword rules.

    Rules (all case-insensitive), evaluated against title + location + text:

    * ``exclude_keywords``: any hit → immediately not a match.
    * ``require_keywords``: every listed keyword must be present.
    * ``include_keywords``: at least one must be present (if any are configured).
    * ``location_keywords``: at least one must be present (if any are configured).
    """

    def __init__(self, config: MatchConfig) -> None:
        self._config = config

    def match(self, job: JobPosting) -> MatchResult:
        """Evaluate a posting and return the decision plus reasons."""
        haystack = self._haystack(job)
        location_text = (job.location or "").lower()
        reasons: list[str] = []

        for word in self._config.exclude_keywords:
            if word.lower() in haystack:
                return MatchResult(
                    matched=False, reasons=[f"excluded by keyword '{word}'"]
                )

        for word in self._config.require_keywords:
            if word.lower() not in haystack:
                return MatchResult(
                    matched=False, reasons=[f"missing required keyword '{word}'"]
                )
            reasons.append(f"has required keyword '{word}'")

        if self._config.include_keywords:
            hits = [w for w in self._config.include_keywords if w.lower() in haystack]
            if not hits:
                return MatchResult(
                    matched=False, reasons=["no target keyword present"]
                )
            reasons.append(f"matched keyword(s): {', '.join(hits)}")

        if self._config.location_keywords:
            loc_hits = [
                w
                for w in self._config.location_keywords
                if w.lower() in location_text or w.lower() in haystack
            ]
            if not loc_hits:
                return MatchResult(
                    matched=False, reasons=["location not in target region"]
                )
            reasons.append(f"location matched: {', '.join(loc_hits)}")

        return MatchResult(matched=True, reasons=reasons)

    @staticmethod
    def _haystack(job: JobPosting) -> str:
        """Concatenate searchable fields into a single lowercased string."""
        parts = [job.title, job.location or "", job.description or ""]
        return " ".join(parts).lower()
