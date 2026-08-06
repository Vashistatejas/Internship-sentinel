# Internship Sentinel

Modular job-monitoring system that watches company career pages for new
internship postings and sends instant alerts. The MVP monitors **Publicis
Sapient India** and notifies by **email**, running on a **GitHub Actions**
schedule every 5 minutes. (Telegram is included as an optional, disabled
channel.)

It is built as a real product, not a one-off scraper: each concern is its own
module, so you can add companies, notification channels, and smarter matching
later without rewriting the core.

## How it works

```
scrape → match → deduplicate → notify → persist state
```

Every scraper returns the same `JobPosting` model, so matchers, state, and
notifiers never care where a job came from.

## Architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Models | `sentinel.models` | Shared `JobPosting` / `MatchResult` |
| Config | `sentinel.config` | Typed config from JSON + secrets from env |
| Scrapers | `sentinel.scrapers` | Fetch pages; parse to `JobPosting` |
| Matchers | `sentinel.matchers` | Decide relevance + explain why |
| Persistence | `sentinel.persistence` | JSON seen-state, deduplication |
| Notifiers | `sentinel.notifiers` | Deliver alerts (email now; Telegram optional) |
| Services | `sentinel.services` | Orchestrate the full cycle |

Design choices worth knowing:

- **Fetching is separated from parsing.** `scrapers/parsers.py` holds pure
  functions (raw payload → postings) with no network access, so they are unit
  tested against saved fixtures — even when the live site is unavailable.
- **Composition over inheritance.** `MonitorService` takes lists of scrapers
  and notifiers. Adding a company or channel means adding to a list/registry,
  not editing the flow.
- **Config-driven targets.** Companies, keywords, and locations live in
  `config/config.json`; secrets live only in env vars / GitHub secrets.

## Project layout

```
config/config.json              # targets, keywords, channel toggles (no secrets)
src/sentinel/
  models.py  config.py  main.py
  scrapers/  matchers/  persistence/  notifiers/  services/
tests/                          # fixtures + parser/matcher/state/notifier/model/e2e
.github/workflows/monitor.yml   # 5-minute cron + manual trigger
data/state.json                 # seen-jobs state (committed back by the Action)
```

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -r requirements.txt
pip install -e .            # makes `python -m sentinel.main` importable
```

### Configure email (Gmail example)

1. Turn on 2-Step Verification for your Google account.
2. Create a 16-character **App Password**
   (Google Account → Security → App passwords). Use this, not your login password.
3. Copy `.env.example` to `.env` and fill in the SMTP credentials:

   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=you@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   ```

4. Set the recipient in `config/config.json` under `email.to_addrs`
   (and optionally `from_addr`, which defaults to `SMTP_USERNAME`).

`.env` is git-ignored and must never be committed. Any SMTP provider works
(Gmail, Outlook, SendGrid, Mailgun, Amazon SES) — only the host/port change.

## Usage

```bash
# One monitoring cycle (sends alerts if credentials are set):
python -m sentinel.main --config config/config.json

# Scrape & match but send nothing — safe for testing:
python -m sentinel.main --dry-run --verbose
```

Summary line: `scraped=N matched=N new_alerts=N errors=N`.

## Configuration reference (`config/config.json`)

- `scrapers[]` — `name` (registered scraper), `company`, `url`, `mode`
  (`"html"` or `"json"`), `params`, `headers`, `enabled`.
- `matching` — `include_keywords`, `require_keywords`, `exclude_keywords`,
  `location_keywords` (all case-insensitive).
- `email` — `enabled`, `to_addrs` (list), `from_addr`, `subject_prefix`,
  `use_tls`. SMTP host/port/username/password come from env vars.
- `telegram.enabled` — optional secondary channel, disabled by default
  (credentials from env: `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`).
- `state_path`, `request_timeout`.

## Scraping note (Publicis Sapient)

The Publicis Sapient careers site runs on Radancy TalentBrew, is JavaScript-
rendered, and sits behind CloudFront (which rejects non-browser requests). A
plain HTTP GET returns the app shell with no job data, so the default config
may yield `scraped=0` until pointed at the real data source. Two supported
paths, in order of preference:

1. **JSON API (preferred).** Find the jobs endpoint the page calls (browser
   DevTools → Network → XHR), then set the scraper `url` to it and
   `"mode": "json"`. `parse_json_jobs` already handles common Radancy/Phenom
   field shapes — no code change needed.
2. **Browser automation fallback.** If no usable API exists, render the page
   with Playwright and feed the rendered HTML into `parse_html_jobs`. This is
   the documented fallback; keep it isolated inside the scraper.

Because parsing is fixture-tested and independent of fetching, switching data
sources is a config/fetch change only.

## GitHub Actions

`.github/workflows/monitor.yml`:

- Runs every 5 minutes (`workflow_dispatch` for manual/dry-run testing).
- Installs deps, runs the monitor, and **commits `data/state.json` back** so
  deduplication persists across runs.
- Reads `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` from
  repository secrets (Settings → Secrets and variables → Actions).

GitHub's shortest cron interval is 5 minutes and scheduled runs can be delayed
under platform load.

## Testing

```bash
pytest
```

Covers job parsing (HTML + JSON), keyword matching, duplicate detection, state
read/write, notification formatting/delivery, models, and end-to-end
orchestration — all without network access.

## Extending

- **New company:** add a scraper in `src/sentinel/scrapers/`, register it in
  `scrapers/__init__.py`, add a `scrapers[]` entry in config.
- **New channel:** implement `Notifier` (see `notifiers/email.py`) and add
  it in `main.build_notifiers`.
- **Smarter matching:** implement the same `match(job) -> MatchResult` shape
  and swap it into `MonitorService`.

## Roadmap

Multiple companies · multiple channels (email/Discord/Slack) · relevance
scoring · resume matching · referral tracking · dashboard UI · application
tracker.
