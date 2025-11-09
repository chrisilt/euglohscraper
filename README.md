# euglohscraper```markdown
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
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt

3. Run the script locally:
   TITLE_SELECTOR="h5.headline" DATE_SELECTOR="time, .date" python check_events.py

   - The script will print found events and create/update:
     - seen.json (stores seen ids)
     - feed.xml (RSS feed with new items prepended)

Configuration notes
- To change the selector that finds registration links, set REG_LINK_SELECTOR (env or edit the workflow).
- To change how titles are found, set TITLE_SELECTOR (defaults to "h5.headline").
- To change how dates are found, set DATE_SELECTOR (defaults to "time, .date").
- To send new events to a webhook, set the repository secret WEBHOOK_URL (or export WEBHOOK_URL locally).

Delivery options
- RSS feed (recommended): host feed.xml via GitHub Pages or S3 and point your newsletter tool at the RSS feed (many tools support RSS-to-email).
- Webhook: set WEBHOOK_URL to a Zapier/Make webhook to create drafts or push events into your newsletter workflow.
- Manual: feed.xml is committed to the repo so an editor can review before sending.

Testing & verification steps
1. Install requirements (see above).
2. Run the script locally and verify output:
   TITLE_SELECTOR="h5.headline" DATE_SELECTOR="time, .date" python check_events.py
3. Confirm seen.json and feed.xml are created and contain expected data.
4. Push files to GitHub and enable Actions; the workflow runs hourly and will commit updated seen.json/feed.xml when new events are found.
5. (Optional) Serve feed.xml using GitHub Pages (enable Pages for the repository) or copy feed.xml to S3/public host.

If extraction misses title or date
- Copy the outerHTML of a course card from the site (Inspect → copy outerHTML) and paste it here; I will update TITLE_SELECTOR or DATE_SELECTOR for exact matching.
- Alternatively, tune TITLE_SELECTOR / DATE_SELECTOR to the closest CSS selector.

Security & politeness
- Keep WEBHOOK_URL and any other secrets in repository secrets.
- Be conservative with polling frequency; hourly is a reasonable default for events.
```