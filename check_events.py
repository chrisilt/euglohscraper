#!/usr/bin/env python3
"""
Eugloh course watcher

- Scrapes TARGET_URL for registration links matching REG_LINK_SELECTOR.
- Extracts title using TITLE_SELECTOR (default: "h5.headline") and date using DATE_SELECTOR (default: "time, .date").
- Deduplicates using seen.json (STATE_FILE).
- Prepends new items to feed.xml (FEED_FILE) in simple RSS 2.0 format (newest items at top).
- Optionally POSTs new events to WEBHOOK_URL (Zapier/Make/etc).

Configuration (via environment variables):
- TARGET_URL (default set to the Eugloh open registrations URL)
- REG_LINK_SELECTOR (default the selector you provided)
- TITLE_SELECTOR (default "h5.headline")
- DATE_SELECTOR (default "time, .date")
- STATE_FILE (default "./seen.json")
- FEED_FILE (default "./feed.xml")
- WEBHOOK_URL (optional - generic webhook)
- EMAIL_ENABLED (set to "true" to enable email notifications)
- EMAIL_FROM, EMAIL_TO, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD
- TEAMS_WEBHOOK_URL (optional - Microsoft Teams webhook)
- USER_AGENT, REQUEST_TIMEOUT

Notes:
- Edit REG_LINK_SELECTOR, TITLE_SELECTOR, DATE_SELECTOR if extraction needs tuning.
- The script is idempotent: seen.json ensures events are only processed once.
- Run locally to test before enabling scheduled runs in Actions.
"""
from __future__ import annotations
import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup, Tag

# ---- Configuration ----
TARGET_URL = os.environ.get(
    "TARGET_URL",
    "https://www.eugloh.eu/courses-trainings/?openRegistrations=%5Byes%5D",
)
REG_LINK_SELECTOR = os.environ.get(
    "REG_LINK_SELECTOR",
    # More robust default: match the registration button inside buttons-wrap or p.formUrl,
    # or any anchor whose href contains "register"/"registration"/"intranet".
    # This is deliberately broad to avoid brittle :nth-child selectors used previously.
    "div.buttons-wrap a.button, p.formUrl a, div.buttons-wrap a[href*='register'], a[href*='register'], a[href*='intranet.eugloh.eu']",
)
TITLE_SELECTOR = os.environ.get("TITLE_SELECTOR", "h5.headline")
DATE_SELECTOR = os.environ.get("DATE_SELECTOR", "time, .date")
STATE_FILE = os.environ.get("STATE_FILE", "./seen.json")
FEED_FILE = os.environ.get("FEED_FILE", "./feed.xml")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # optional: Zapier/Make webhook
USER_AGENT = os.environ.get("USER_AGENT", "eugloh-event-checker/1.0")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))

# Email notification configuration
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "").lower() == "true"
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "")

# Microsoft Teams webhook configuration
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")

# ---- Helpers ----
def load_state(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"seen_ids": [], "last_checked": None}
    except Exception as e:
        print("Failed to load state:", e)
        return {"seen_ids": [], "last_checked": None}

def save_state(path: str, state: Dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def fetch_page(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text

def normalize_url(u: str) -> str:
    # make absolute and drop query/fragment for stable id
    abs_url = urljoin(TARGET_URL, u)
    p = urlparse(abs_url)
    p = p._replace(query="", fragment="")
    return urlunparse(p)

def _find_in_ancestors(el: Tag, css_selector: str, max_levels: int = 6) -> Optional[Tag]:
    """
    Search up the DOM from the given element through ancestors and try to select css_selector
    inside each ancestor. Return the first matching Tag or None.
    """
    parent = el
    for _ in range(max_levels):
        if parent is None or getattr(parent, "name", None) in ("html", "body"):
            break
        try:
            found = parent.select_one(css_selector)
            if isinstance(found, Tag):
                return found
        except Exception:
            # malformed selector or other error; continue gracefully
            pass
        parent = parent.parent
    return None

# ---- Extraction logic ----
def extract_event_from_anchor(a_tag: Tag) -> Optional[Dict]:
    """
    Given an <a> tag (registration link), construct an event dict:
    { id, title, date, link, description }
    - Uses normalize_url for stable id
    - Uses TITLE_SELECTOR and DATE_SELECTOR searching in ancestors first
    - Falls back to nearby headings / previous <time> / previous <p> if needed
    """
    href = a_tag.get("href")
    if not href:
        return None

    link = normalize_url(href)
    eid = link

    # Title extraction: use TITLE_SELECTOR in ancestors first, then fallback heuristics
    title = None
    title_el = _find_in_ancestors(a_tag, TITLE_SELECTOR)
    if title_el and title_el.get_text(strip=True):
        title = title_el.get_text(strip=True)

    if not title:
        # fallback: look for nearby headings h1..h5 within ancestors
        parent = a_tag.parent
        depth = 0
        while parent and parent.name not in ("body", "html") and depth < 6:
            for hd in parent.find_all(["h1", "h2", "h3", "h4", "h5"], recursive=False):
                txt = hd.get_text(strip=True)
                if txt:
                    title = txt
                    break
            if title:
                break
            parent = parent.parent
            depth += 1

    if not title:
        # fallback: previous heading in document
        prev_hd = a_tag.find_previous(["h1", "h2", "h3", "h4", "h5"])
        if prev_hd and prev_hd.get_text(strip=True):
            title = prev_hd.get_text(strip=True)

    # Date extraction: try DATE_SELECTOR inside ancestors, then previous <time>, then previous .date
    date = None
    date_el = _find_in_ancestors(a_tag, DATE_SELECTOR)
    if date_el and date_el.get_text(strip=True):
        date = date_el.get_text(strip=True)

    if not date:
        prev_time = a_tag.find_previous("time")
        if prev_time and prev_time.get_text(strip=True):
            date = prev_time.get_text(strip=True)

    if not date:
        prev_date_class = a_tag.find_previous(class_="date")
        if prev_date_class and getattr(prev_date_class, "get_text", None):
            d = prev_date_class.get_text(strip=True)
            if d:
                date = d

    # Description: try first <p> in same block or previous <p>
    description = None
    pparent = a_tag.parent
    if pparent:
        # prefer direct child <p> with content
        p = None
        for candidate in pparent.find_all("p", recursive=False):
            if candidate.get_text(strip=True):
                p = candidate
                break
        if p:
            description = p.get_text(strip=True)
        else:
            pprev = a_tag.find_previous("p")
            if pprev and pprev.get_text(strip=True):
                description = pprev.get_text(strip=True)

    # final fallbacks
    if not title:
        title = link

    return {
        "id": eid,
        "title": title,
        "date": date,
        "link": link,
        "description": description,
    }

def find_events(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select(REG_LINK_SELECTOR)
    events: List[Dict] = []
    for a in anchors:
        ev = extract_event_from_anchor(a)
        if ev:
            events.append(ev)
    return events

# ---- Delivery helpers ----
def post_to_webhook(ev: Dict):
    if not WEBHOOK_URL:
        return
    try:
        r = requests.post(WEBHOOK_URL, json=ev, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        print(f"Posted event {ev['id']} -> {r.status_code}")
    except Exception as e:
        print("Failed to post webhook:", e)

def send_email_notification(ev: Dict):
    """Send email notification for a new event."""
    if not EMAIL_ENABLED or not all([EMAIL_FROM, EMAIL_TO, EMAIL_SMTP_HOST, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD]):
        return
    
    try:
        from html import escape
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New EUGLOH Event: {ev.get('title', 'Untitled')}"
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        
        # Create plain text and HTML versions
        text_content = f"""
New EUGLOH Event Detected!

Title: {ev.get('title', 'N/A')}
Date: {ev.get('date', 'N/A')}
Link: {ev.get('link', 'N/A')}

Description: {ev.get('description', 'N/A')}

---
This is an automated notification from the EUGLOH Course Watcher.
"""
        
        # Escape HTML entities to prevent XSS
        title = escape(ev.get('title', 'N/A'))
        date = escape(ev.get('date', 'N/A'))
        link = escape(ev.get('link', 'N/A'))
        description = escape(ev.get('description', 'N/A'))
        
        html_content = f"""
<html>
  <head></head>
  <body>
    <h2>New EUGLOH Event Detected!</h2>
    <p><strong>Title:</strong> {title}</p>
    <p><strong>Date:</strong> {date}</p>
    <p><strong>Link:</strong> <a href="{link}">{link}</a></p>
    <p><strong>Description:</strong> {description}</p>
    <hr>
    <p><em>This is an automated notification from the EUGLOH Course Watcher.</em></p>
  </body>
</html>
"""
        
        # Attach both versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent for event: {ev['id']}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_teams_notification(ev: Dict):
    """Send Microsoft Teams notification for a new event."""
    if not TEAMS_WEBHOOK_URL:
        return
    
    try:
        # Create Teams message card format
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"New EUGLOH Event: {ev.get('title', 'Untitled')}",
            "themeColor": "0078D7",
            "title": "New EUGLOH Event Detected!",
            "sections": [
                {
                    "activityTitle": ev.get('title', 'Untitled'),
                    "activitySubtitle": ev.get('date', 'Date not available'),
                    "facts": [
                        {
                            "name": "Description:",
                            "value": ev.get('description', 'No description available')
                        }
                    ],
                    "markdown": True
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View Event",
                    "targets": [
                        {
                            "os": "default",
                            "uri": ev.get('link', '#')
                        }
                    ]
                }
            ]
        }
        
        r = requests.post(TEAMS_WEBHOOK_URL, json=card, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        print(f"Teams notification sent for event: {ev['id']}")
    except Exception as e:
        print(f"Failed to send Teams notification: {e}")

def append_to_feed(feed_file: str, new_events: List[Dict]):
    """
    Prepend new items to feed_file so newest items are at the top.
    Uses a minimal RSS 2.0 structure.
    """
    from xml.sax.saxutils import escape

    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    items_xml = ""
    # Expect new_events in newest-first order; we'll prepend them
    for ev in new_events:
        title = escape(ev.get("title") or ev["id"])
        link = escape(ev.get("link") or "")
        desc = escape(ev.get("description") or "")
        pubdate = escape(ev.get("date") or now)
        items_xml += f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <description>{desc}</description>
    <pubDate>{pubdate}</pubDate>
    <guid isPermaLink="false">{escape(ev["id"])}</guid>
    <category>new</category>
  </item>\n"""

    if os.path.exists(feed_file):
        with open(feed_file, "r", encoding="utf-8") as f:
            existing = f.read()
        # naive prepend after <channel> line
        insert_after = existing.find("<channel>")
        if insert_after != -1:
            after_idx = existing.find("\n", insert_after)
            if after_idx != -1:
                new_feed = existing[:after_idx+1] + items_xml + existing[after_idx+1:]
            else:
                new_feed = items_xml + existing
        else:
            new_feed = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<rss version=\"2.0\">\n<channel>\n"
            new_feed += f"  <title>New events from {TARGET_URL}</title>\n  <link>{TARGET_URL}</link>\n  <description>Auto-generated feed of new events</description>\n"
            new_feed += items_xml
            new_feed += "</channel>\n</rss>"
    else:
        new_feed = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<rss version=\"2.0\">\n<channel>\n"
        new_feed += f"  <title>New events from {TARGET_URL}</title>\n  <link>{TARGET_URL}</link>\n  <description>Auto-generated feed of new events</description>\n"
        new_feed += items_xml
        new_feed += "</channel>\n</rss>"

    with open(feed_file + ".tmp", "w", encoding="utf-8") as f:
        f.write(new_feed)
    os.replace(feed_file + ".tmp", feed_file)
    print(f"Wrote feed to {feed_file}")

# ---- Main ----
def main():
    state = load_state(STATE_FILE)
    seen = set(state.get("seen_ids", []))

    try:
        html = fetch_page(TARGET_URL)
    except Exception as e:
        print("Error fetching page:", e)
        return

    events = find_events(html)
    print(f"Found {len(events)} candidate events via selector: {REG_LINK_SELECTOR}")

    # Deduplicate: only events whose id (normalized link) not in seen
    new_events = [e for e in events if e["id"] not in seen]
    if not new_events:
        print("No new events")
        state["last_checked"] = int(time.time())
        save_state(STATE_FILE, state)
        return

    # Process each new event
    for ev in new_events:
        print("New:", ev["id"], "| title:", ev.get("title"), "| date:", ev.get("date"))
        post_to_webhook(ev)
        send_email_notification(ev)
        send_teams_notification(ev)
        seen.add(ev["id"])

    # Prepend newest first (so feed top is newest)
    append_to_feed(FEED_FILE, new_events[::-1])

    state["seen_ids"] = list(seen)
    state["last_checked"] = int(time.time())
    save_state(STATE_FILE, state)
    print(f"Saved state: {len(state['seen_ids'])} seen ids")

if __name__ == "__main__":
    main()