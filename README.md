# EUGLOH Course Watcher

A tiny scraper that watches EUGLOH course & event pages and builds a public RSS feed of open registrations. Designed to be simple, robust, and easy to host via GitHub Pages.

## Live Demo
- Feed (RSS): https://chrisilt.github.io/euglohscraper/feed.xml (when Pages is enabled)
- Web viewer: https://chrisilt.github.io/euglohscraper/ (simple page that shows the feed)

## Why This Project
- Keep an eye on new course registrations without visiting the site
- Feed-based delivery is great for newsletter integrations, email-to-RSS tools, or personal monitoring
- Optional webhook support for automated pipelines (Zapier, Make, Teams, Email)

## Quick Links
- Scraper: `check_events.py`
- Generated feed: `feed.xml`
- Scraper state (dedupe): `seen.json`

## Features
- Robust selector defaults (less brittle than :nth-child)
- Writes a human-friendly `feed.xml` RSS file you can publish via Pages
- Optional webhook support (Zapier / Make) for automated pipelines
- Email notifications for new events (SMTP)
- Microsoft Teams notifications via webhook
- Deduplication to avoid duplicate notifications
- **Expired event handling** — Automatically marks expired events with `<category>expired</category>` in RSS feed
- **Historical tracking** — Tracks event lifecycle (when added, when expired, registration duration)
- **Statistics dashboard** — View event statistics at `/docs/stats.html` with JSON API at `/docs/stats.json`

## Run Locally (2 minutes)
```bash
git clone https://github.com/chrisilt/euglohscraper.git
cd euglohscraper
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python check_events.py
```

## What the Script Creates
- `seen.json` — internal state used to avoid reposting the same event
- `feed.xml` — RSS feed with newly discovered events (new items are prepended)
- `history.json` — historical tracking of all events (when discovered, expired, duration)
- `docs/stats.json` — event statistics in JSON format
- `docs/stats.html` — interactive statistics dashboard

## Configuration

All configuration is done via environment variables. You can set them directly in your shell, or create a `.env` file (see `.env.example` for a template).

### Basic Configuration
- `TARGET_URL` — URL to scrape (defaults to EUGLOH open registrations page)
- `REG_LINK_SELECTOR` — CSS selector(s) that match registration anchors
- `TITLE_SELECTOR` — defaults to `h5.headline`
- `DATE_SELECTOR` — defaults to `time, .date`
- `STATE_FILE` — defaults to `./seen.json`
- `FEED_FILE` — defaults to `./feed.xml`

### Notification Configuration
- `WEBHOOK_URL` — optional: a generic webhook to POST new events to
- `EMAIL_ENABLED` — set to `true` to enable email notifications
- `EMAIL_FROM` — sender email address
- `EMAIL_TO` — recipient email address(es), comma-separated
- `EMAIL_SMTP_HOST` — SMTP server hostname (e.g., `smtp.gmail.com`)
- `EMAIL_SMTP_PORT` — SMTP server port (defaults to 587 for TLS)
- `EMAIL_SMTP_USER` — SMTP username
- `EMAIL_SMTP_PASSWORD` — SMTP password
- `TEAMS_WEBHOOK_URL` — Microsoft Teams incoming webhook URL

### Expired Event Handling
- `EXPIRED_DAYS_BUFFER` — Grace period in days after deadline before marking as expired (defaults to 0)

### Historical Tracking & Statistics
- `HISTORY_FILE` — Path to historical tracking JSON (defaults to `./history.json`)
- `STATS_FILE` — Path to statistics JSON output (defaults to `./docs/stats.json`)
- `STATS_HTML_FILE` — Path to statistics HTML dashboard (defaults to `./docs/stats.html`)

## Publish via GitHub Pages (Recommended)
1. Use the included workflow to automatically generate and commit `docs/feed.xml` (or push the file manually)
2. Enable Pages: Settings → Pages → Branch: `main`, Folder: `/docs`
3. The feed will be available at `https://<your>.github.io/euglohscraper/feed.xml` and the viewer at `https://<your>.github.io/euglohscraper/`

## Notification Setup

### Email Notifications
To enable email notifications, set the following environment variables:
```bash
export EMAIL_ENABLED=true
export EMAIL_FROM=your-email@gmail.com
export EMAIL_TO=recipient@example.com
export EMAIL_SMTP_HOST=smtp.gmail.com
export EMAIL_SMTP_PORT=587
export EMAIL_SMTP_USER=your-email@gmail.com
export EMAIL_SMTP_PASSWORD=your-app-password
```

For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

### Microsoft Teams Notifications
To enable Teams notifications:
1. In your Teams channel, click the three dots (⋯) → Connectors → Incoming Webhook
2. Create a new webhook and copy the URL
3. Set the environment variable:
```bash
export TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/...
```

### GitHub Actions Setup
To use notifications in GitHub Actions, add the secrets to your repository:
1. Go to Settings → Secrets and variables → Actions
2. Add the necessary secrets (e.g., `EMAIL_SMTP_PASSWORD`, `TEAMS_WEBHOOK_URL`)
3. Update `.github/workflows/scrape-and-publish.yml` to include the environment variables

## Web Viewer
A lightweight viewer is provided in the `docs/` folder. It fetches `feed.xml` and renders a simple, mobile-friendly list of items.

## Event Statistics Dashboard
The scraper automatically generates a comprehensive statistics dashboard with interactive visualizations showing:

### Core Metrics
- **Total events tracked** — All events discovered since tracking began
- **Currently active** — Events with registration still open
- **Total expired** — Events past their deadline
- **New this week** — Events discovered in the last 7 days
- **New this month** — Events discovered in the last 30 days
- **Expired this week** — Events that expired in the last 7 days
- **Expired this month** — Events that expired in the last 30 days

### Registration Duration Analysis
- **Average duration** — How long registrations typically remain open
- **Min/Max/Median** — Range of registration periods
- **Distribution stats** — Detailed breakdown of registration windows

### Event Velocity Metrics
- **Events per week** — Rate of new event discovery
- **Events per month** — Monthly event discovery rate
- **Tracking period** — Total days of data collection

### Active Event Insights
- **Average age** — How long current events have been active
- **Age distribution** — Min/Max/Median age of active events
- **Long-running events** — Events active for more than 60 days

### Timeline Features
- **Upcoming deadlines** — Events expiring in the next 30 days
- **Recently expired** — Events that expired in the last 7 days (with duration)
- **Monthly trends** — Interactive chart showing event discovery rate by month (last 12 months)

### Dashboard Access
- **HTML**: `https://<your>.github.io/euglohscraper/stats.html` — Interactive dashboard with Chart.js visualizations
- **JSON API**: `https://<your>.github.io/euglohscraper/stats.json` — Raw data for custom analysis

The statistics are automatically updated each time the scraper runs.

## Expired Event Handling
Events are automatically checked against their deadlines. When an event expires:
- It's marked with `<category>expired</category>` in the RSS feed
- Historical data records the expiration time and calculates registration duration
- The event remains in the feed but is visually distinguished as expired

You can configure a grace period with `EXPIRED_DAYS_BUFFER` to keep events active for a few days after their deadline (e.g., set to `7` to keep events for a week after expiration).

## Historical Tracking
The scraper maintains a complete history of all events in `history.json`:
- **First seen**: When the event was first discovered
- **Last seen**: Last time the event was observed on the source page
- **Expired at**: When the event's deadline passed
- **Registration duration**: How long registration was open (in days)

This data powers the statistics dashboard and provides insights into EUGLOH event patterns.

## Troubleshooting
- If the Action doesn't publish, check Actions → the run logs for errors
- If the feed is missing fields, copy a single course card (Inspect → copy outerHTML) and paste it in an issue — I can tune selectors
- For email issues, verify SMTP credentials and check that less secure apps or app passwords are configured

## Contributing & License
- Pull requests welcome for small improvements (better parsing, tests, styling)
- MIT-style: feel free to reuse

## Files
- `check_events.py` — scraper + deduplication + feed writer + notifications
- `requirements.txt` — Python dependencies
- `.github/workflows/scrape-and-publish.yml` — scheduled GitHub Action (hourly)
- `README.md` — this file