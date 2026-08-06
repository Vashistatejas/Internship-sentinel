"""Scrapers: fetch and parse career pages into :class:`JobPosting` objects."""

from sentinel.scrapers.ashby import AshbyScraper
from sentinel.scrapers.base import BaseScraper
from sentinel.scrapers.greenhouse import GreenhouseScraper
from sentinel.scrapers.lever import LeverScraper
from sentinel.scrapers.publicis_sapient import PublicisSapientScraper

# Registry maps a config ``name`` to a scraper class.
# Adding a new company on an existing ATS = add a config entry only.
# Adding a new ATS platform = add a scraper class + one line here.
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "publicis_sapient": PublicisSapientScraper,
    "greenhouse": GreenhouseScraper,
    "lever": LeverScraper,
    "ashby": AshbyScraper,
}

__all__ = [
    "BaseScraper",
    "PublicisSapientScraper",
    "GreenhouseScraper",
    "LeverScraper",
    "AshbyScraper",
    "SCRAPER_REGISTRY",
]
