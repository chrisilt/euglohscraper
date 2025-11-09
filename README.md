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
   # Eugloh course watcher

   This repo contains a small scraper that polls EUGLOH's course listings and detects new open registration links. New items are added to an RSS feed (`feed.xml`) and — optionally — POSTed to a webhook (Zapier/Make/etc).

   Key files
   - `check_events.py` — scraper + deduplication + feed writer
   - `requirements.txt` — Python dependencies
   - `.github/workflows/check-events.yml` — (optional) scheduled GitHub Action (hourly)
   - `feed.xml` — generated RSS feed (public-facing)
   - `seen.json` — scraper state (internal deduplication)

   What's the difference between `seen.json` and `feed.xml`?
   - `seen.json` is an internal state file used by the script to remember which event IDs it has already processed. It prevents posting/adding the same event multiple times. This file is not meant to be consumed as a public feed.
   - `feed.xml` is the public artifact: an RSS 2.0 feed containing the (new) events discovered by the scraper. This is what you should link to from newsletters or a website. The script prepends new items to `feed.xml` so the newest items are at the top.

   Contract (inputs / outputs)
   - Inputs: `TARGET_URL`, CSS selectors (via `REG_LINK_SELECTOR`, `TITLE_SELECTOR`, `DATE_SELECTOR`), optional `WEBHOOK_URL`.
   - Outputs: `feed.xml` (RSS), `seen.json` (internal state).
   - Error modes: network errors (fetch fails), parsing misses (selectors need tuning); script prints errors and exits without corrupting state.

   Run locally (quick)
   1. Clone the repo and create a venv:
       python -m venv .venv
       source .venv/bin/activate
       python -m pip install --upgrade pip
       python -m pip install -r requirements.txt

   2. Run the script (defaults are reasonable):
       python check_events.py

   3. Override selectors if needed (example):
       REG_LINK_SELECTOR="div.buttons-wrap a.button, p.formUrl a" TITLE_SELECTOR="h5.headline" DATE_SELECTOR=".info_start-end span:nth-of-type(2)" python check_events.py

   Notes:
   - After a successful run the script writes/updates `seen.json` and `feed.xml` in the repo root.
   - `seen.json` is required for idempotence; do not delete it unless you want the script to treat all items as new.

   Publishing `feed.xml` via GitHub Pages (recommended)
   You can serve `feed.xml` from GitHub Pages so newsletter tools can fetch it. Two common options:

   1) Manual / repo-root Pages
       - Enable GitHub Pages for this repo (Settings → Pages) and choose the `gh-pages` branch or the `docs/` folder on `main`.
       - If you prefer the `docs/` approach: copy `feed.xml` to `docs/feed.xml` and push; Pages will serve it at `https://<user>.github.io/<repo>/feed.xml`.

   2) Automatic (recommended) — GitHub Action that generates `feed.xml` and publishes it to `gh-pages`.
       - Add the included workflow `.github/workflows/publish_feed.yml` (already in this repo). It:
          - checks out the code
          - sets up Python
          - installs dependencies
          - runs `check_events.py` to generate `feed.xml`
          - publishes the generated `feed.xml` to the `gh-pages` branch using `actions-gh-pages`
       - Enable GitHub Pages to serve from the `gh-pages` branch (Settings → Pages → Branch: `gh-pages`, folder: `/`). The feed will then be available at `https://<user>.github.io/<repo>/feed.xml`.

   Sample GitHub Action (already added at `.github/workflows/publish_feed.yml`)
   ```yaml
   name: Generate and publish feed.xml

   on:
      schedule:
         - cron: '0 * * * *'   # hourly
      workflow_dispatch: {}

   jobs:
      build-and-publish:
         runs-on: ubuntu-latest
         steps:
            - uses: actions/checkout@v4
            - uses: actions/setup-python@v4
               with:
                  python-version: '3.x'
            - name: Install dependencies
               run: |
                  python -m pip install --upgrade pip
                  python -m pip install -r requirements.txt
            - name: Generate feed.xml
               run: python check_events.py
            - name: Prepare publish directory
               run: |
                  mkdir out
                  mv feed.xml out/feed.xml || true
            - name: Publish to gh-pages
               uses: peaceiris/actions-gh-pages@v4
               with:
                  github_token: ${{ secrets.GITHUB_TOKEN }}
                  publish_dir: ./out

   ```

   After enabling Pages on the `gh-pages` branch the feed will be available at:
   `https://<github-username>.github.io/<repository>/feed.xml` — replace the placeholders accordingly.

   Tweaks and debugging
   - If titles or dates are missing for some events, tweak `TITLE_SELECTOR` and `DATE_SELECTOR`. The page uses a pattern like:
      - title: `h5.headline`
      - date: an `.info_start-end` container where the date appears in the second `<span>`.
   - If you want more stable IDs, edit `normalize_url` in `check_events.py` to include/exclude query parameters differently.

   Privacy / secrets
   - Keep `WEBHOOK_URL` (if used) as a repository secret and reference it in Actions via `secrets.WEBHOOK_URL`.

   If you'd like, I can also add a small test fixture and pytest checks for the extraction logic (title/date/link) so future selector changes are safer.
   ```