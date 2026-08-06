"""Pure parsing functions for career-page payloads.

These functions take a raw string (HTML or JSON text) and return a list of
:class:`JobPosting`. They perform **no** network access, so they can be unit
tested against saved fixtures. Parsing is resilient: malformed or missing
fields are skipped rather than crashing the whole run.
"""

from __future__ import annotations

import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sentinel.models import JobPosting

# Field-name candidates seen across Radancy/Phenom-style JSON job feeds.
_TITLE_KEYS = ("title", "name", "jobTitle", "positionTitle")
_URL_KEYS = ("url", "applyUrl", "jobUrl", "canonicalUrl", "link")
_ID_KEYS = ("id", "jobId", "reqId", "requisitionId", "slug")
_LOCATION_KEYS = ("location", "city", "primaryLocation", "jobLocation")
_DATE_KEYS = ("postedDate", "datePosted", "date", "createDate")
_DESC_KEYS = ("description", "summary", "shortDescription")


def _first(data: dict, keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty value among ``keys`` in ``data``."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
        if isinstance(value, dict):
            # Nested location objects like {"city": "...", "country": "..."}.
            nested = _first(value, _LOCATION_KEYS + ("country", "state"))
            if nested:
                return nested
    return None


def _job_id_from_url(url: str) -> str:
    """Derive a stable id from a job-details URL slug."""
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return slug or url


def parse_json_jobs(
    raw: str,
    *,
    company: str,
    source: str,
    base_url: str = "",
    results_key: str | None = None,
) -> list[JobPosting]:
    """Parse a JSON payload containing a list of jobs.

    Args:
        raw: JSON text.
        company: Company name to stamp on each posting.
        source: Scraper identifier to stamp on each posting.
        base_url: Base used to absolutise relative URLs.
        results_key: Optional key holding the job list (e.g. ``"jobs"``).
            When omitted, the parser looks for the first list-of-dicts it finds.

    Returns:
        Parsed postings; entries missing a title or URL are skipped.
    """
    payload = json.loads(raw)
    jobs = _locate_job_list(payload, results_key)

    postings: list[JobPosting] = []
    for item in jobs:
        if not isinstance(item, dict):
            continue
        title = _first(item, _TITLE_KEYS)
        url = _first(item, _URL_KEYS)
        if not title or not url:
            continue
        url = urljoin(base_url, url)
        job_id = _first(item, _ID_KEYS) or _job_id_from_url(url)
        postings.append(
            JobPosting(
                company=company,
                title=title,
                url=url,
                job_id=job_id,
                source=source,
                location=_first(item, _LOCATION_KEYS),
                date_posted=_first(item, _DATE_KEYS),
                description=_first(item, _DESC_KEYS),
            )
        )
    return postings


def _locate_job_list(payload: object, results_key: str | None) -> list:
    """Find the job list inside a JSON payload of varying shapes."""
    if results_key is not None and isinstance(payload, dict):
        return payload.get(results_key, []) or []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
    return []


def parse_html_jobs(
    raw: str,
    *,
    company: str,
    source: str,
    base_url: str = "",
    link_contains: str = "job-details",
) -> list[JobPosting]:
    """Parse an HTML career listing into postings.

    The parser looks for anchor tags whose ``href`` contains ``link_contains``
    (the job-detail path) and treats each as one posting. Location is read from
    a sibling/nearby element when present. This is deliberately tolerant of
    layout changes: it keys off links rather than brittle CSS class names.

    Args:
        raw: HTML text.
        company: Company name to stamp on each posting.
        source: Scraper identifier to stamp on each posting.
        base_url: Base used to absolutise relative hrefs.
        link_contains: Substring identifying job-detail links.

    Returns:
        Parsed postings, de-duplicated by URL, in document order.
    """
    soup = BeautifulSoup(raw, "lxml")
    postings: list[JobPosting] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if link_contains not in href:
            continue
        title = anchor.get_text(strip=True)
        if not title:
            continue
        url = urljoin(base_url, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        postings.append(
            JobPosting(
                company=company,
                title=title,
                url=url,
                job_id=_job_id_from_url(url),
                source=source,
                location=_nearby_location(anchor),
            )
        )
    return postings


def _nearby_location(anchor) -> str | None:
    """Best-effort extraction of a location near a job link."""
    container = anchor.find_parent(["li", "article", "div"]) or anchor.parent
    if container is None:
        return None
    for element in container.find_all(["span", "p", "div"]):
        text = element.get_text(strip=True)
        classes = " ".join(element.get("class", [])).lower()
        if "location" in classes and text:
            return text
    return None


def parse_publicis_json(
    raw: str,
    *,
    company: str,
    source: str,
    base_url: str = "",
) -> list[JobPosting]:
    """Parse the Publicis Sapient careers search API response.

    The endpoint (``/bin/ps-redesign/careersJobsearch``) returns a Solr-style
    payload where postings live at ``response.docs``. Field names are specific
    to this site, so they are mapped explicitly here rather than guessed.

    ``experienceLevel`` is folded into the description so relevance rules (e.g.
    excluding "senior") can act on it in addition to the title.

    Args:
        raw: JSON text from the search endpoint.
        company: Company name to stamp on each posting.
        source: Scraper identifier to stamp on each posting.
        base_url: Origin used to absolutise the relative ``jobDetailUrl``.

    Returns:
        Parsed postings; entries missing a title or any URL are skipped.
    """
    payload = json.loads(raw)
    docs = []
    if isinstance(payload, dict):
        response = payload.get("response")
        if isinstance(response, dict):
            docs = response.get("docs", []) or []

    postings: list[JobPosting] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        title = (doc.get("name") or "").strip()
        relative = doc.get("jobDetailUrl") or ""
        absolute = doc.get("jobUrl") or ""
        url = urljoin(base_url, relative) if relative else absolute
        if not title or not url:
            continue

        job_id = str(doc.get("jobId") or doc.get("id") or "").strip()
        experience = (doc.get("experienceLevel") or "").strip()

        postings.append(
            JobPosting(
                company=company,
                title=title,
                url=url,
                job_id=job_id or _job_id_from_url(url),
                source=source,
                location=doc.get("displayLocation") or doc.get("city"),
                date_posted=doc.get("releasedDate"),
                description=experience or None,
            )
        )
    return postings
