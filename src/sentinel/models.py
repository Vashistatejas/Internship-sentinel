"""Shared data models.

Every scraper, regardless of the site or format it reads, returns the same
:class:`JobPosting` structure. The rest of the application (matchers,
persistence, notifiers) therefore never needs to know where a job came from.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobPosting(BaseModel):
    """A single job posting in a source-agnostic shape.

    Attributes:
        company: Employer name, e.g. ``"Publicis Sapient"``.
        title: Job title as advertised.
        url: Canonical link to the posting.
        job_id: Stable identifier for the posting. Used for deduplication.
        source: Identifier of the scraper/site that produced this posting.
        location: Human-readable location, if known.
        date_posted: Posting date as reported by the source (raw string).
        description: Optional description or snippet, if available.
    """

    company: str
    title: str
    url: HttpUrl
    job_id: str
    source: str
    location: str | None = None
    date_posted: str | None = None
    description: str | None = None

    @field_validator("title", "company", "job_id", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject blank required strings early so bad data never reaches state."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field must not be blank")
        return cleaned

    @property
    def dedup_key(self) -> str:
        """Return a stable key used to detect whether a job was already seen.

        Prefers ``job_id`` (scoped by company to avoid cross-company clashes).
        Falls back to a hash of the URL when no id is available.
        """
        if self.job_id:
            return f"{self.company.lower()}:{self.job_id}"
        digest = hashlib.sha256(str(self.url).encode("utf-8")).hexdigest()[:16]
        return f"{self.company.lower()}:{digest}"


class MatchResult(BaseModel):
    """Outcome of evaluating a posting against the matching rules.

    ``reasons`` powers the "why this matched" note in notifications.
    """

    matched: bool
    reasons: list[str] = Field(default_factory=list)

    def why(self) -> str:
        """Return a short human-readable explanation of the match."""
        return "; ".join(self.reasons) if self.reasons else "matched configured rules"
