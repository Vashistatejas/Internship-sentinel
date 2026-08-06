"""JSON-backed state store for deduplication.

The store remembers every posting the system has already alerted on, keyed by
:attr:`JobPosting.dedup_key`. This lets scheduled runs repeat safely without
sending duplicate alerts. The JSON format keeps state human-readable and easy
to commit back from CI.

The storage backend is deliberately isolated behind a small class so it can be
replaced later (SQLite, Redis, DynamoDB) without changing callers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sentinel.models import JobPosting


class JsonStateStore:
    """Track seen postings in a JSON file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._seen: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> None:
        """Load state from disk. Missing/corrupt files start from empty state."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._seen = data.get("seen", {})
            except (json.JSONDecodeError, OSError):
                self._seen = {}
        else:
            self._seen = {}
        self._loaded = True

    def is_seen(self, job: JobPosting) -> bool:
        """Return True if this posting was already recorded."""
        self._ensure_loaded()
        return job.dedup_key in self._seen

    def mark_seen(self, job: JobPosting) -> None:
        """Record a posting as seen (idempotent for repeat keys)."""
        self._ensure_loaded()
        if job.dedup_key not in self._seen:
            self._seen[job.dedup_key] = {
                "title": job.title,
                "url": str(job.url),
                "company": job.company,
                "first_seen": datetime.now(timezone.utc).isoformat(),
            }

    def save(self) -> None:
        """Persist state to disk, creating parent directories as needed."""
        self._ensure_loaded()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "seen": self._seen,
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @property
    def seen_count(self) -> int:
        """Number of postings currently recorded."""
        self._ensure_loaded()
        return len(self._seen)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
