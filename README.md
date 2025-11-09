# Eugloh course watcher

This repository contains a simple scraper that polls Eugloh's course listings and detects new course registrations. New items are appended to an RSS feed (feed.xml) and optionally POSTed to a webhook (e.g., Zapier/Make).

Files created
- check_events.py : scraper + deduplication + feed writer
- requirements.txt : Python dependencies
- .github/workflows/check-events.yml : scheduled GitHub Action (hourly)
- README.md : this file

Quick start (local)
1. Clone the repo.
2. Create a virtualenv and install deps:
   ````markdown
   # EUGLOH Course Watcher

   A tiny scraper that watches EUGLOH course & event pages and builds a public RSS feed of open registrations. Designed to be simple, robust, and easy to host via GitHub Pages.

   Live demo
   - Feed (RSS): https://chrisilt.github.io/euglohscraper/feed.xml  (when Pages is enabled)
   - Web viewer: https://chrisilt.github.io/euglohscraper/  (simple page that shows the feed)

   Why this project
   - Keep an eye on new course registrations without visiting the site.
   - Feed-based delivery is great for newsletter integrations, email-to-RSS tools, or personal monitoring.

   Quick links
   - Scraper: `check_events.py`
   - Generated feed: `feed.xml`
   - Scraper state (dedupe): `seen.json`

   Nice features
   - Robust selector defaults (less brittle than :nth-child)
   - Writes a human-friendly `feed.xml` RSS file you can publish via Pages
   - Optional webhook support (Zapier / Make) for automated pipelines

   Run locally (2 minutes)
   ```bash
   git clone https://github.com/chrisilt/euglohscraper.git
   cd euglohscraper
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python check_events.py
   ```

   What the script creates
   - `seen.json` — internal state used to avoid reposting the same event
   - `feed.xml` — RSS feed with newly discovered events (new items are prepended)

   Configuration hints
   - REG_LINK_SELECTOR — CSS selector(s) that match registration anchors (defaults are robust heuristics)
   - TITLE_SELECTOR — defaults to `h5.headline`
   - DATE_SELECTOR — tweak if the script misses dates (page often puts date text inside `.info_start-end span`)
   - WEBHOOK_URL — optional: a webhook to POST new events to (store as a repo secret for Actions)

   Publish via GitHub Pages (recommended)
   1) Use the included workflow to automatically generate and commit `docs/feed.xml` (or push the file manually).
   2) Enable Pages: Settings → Pages → Branch: `main`, Folder: `/docs`.
   3) The feed will be available at `https://<your>.github.io/euglohscraper/feed.xml` and the viewer at `https://<your>.github.io/euglohscraper/`.

   Web viewer
   - A lightweight viewer is provided in the `docs/` folder. It fetches `feed.xml` and renders a simple, mobile-friendly list of items.

   Troubleshooting
   - If the Action doesn't publish, check Actions → the run logs for errors.
   - If the feed is missing fields, copy a single course card (Inspect → copy outerHTML) and paste it in an issue — I can tune selectors.

   Contributing & license
   - Pull requests welcome for small improvements (better parsing, tests, styling)
   - MIT-style: feel free to reuse

   Want more?
   - I can add tests for extraction logic, improve date parsing, or wire a webhook integration.
   ```