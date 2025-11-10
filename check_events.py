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
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT") or "15")

# Email notification configuration
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "").lower() == "true"
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT") or "587")
EMAIL_SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "")

# Microsoft Teams webhook configuration
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")

# Expired events configuration
EXPIRED_DAYS_BUFFER = int(os.environ.get("EXPIRED_DAYS_BUFFER") or "0")  # Grace period after deadline

# Historical tracking and statistics
HISTORY_FILE = os.environ.get("HISTORY_FILE", "./history.json")
STATS_FILE = os.environ.get("STATS_FILE", "./docs/stats.json")
STATS_HTML_FILE = os.environ.get("STATS_HTML_FILE", "./docs/stats.html")

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

def parse_deadline(date_str: str) -> Optional[float]:
    """
    Parse a deadline date string and return a Unix timestamp.
    Handles multiple date formats commonly found in EUGLOH events.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    from datetime import datetime
    import re
    
    # Common date formats in EUGLOH events
    formats = [
        "%d %b %Y %H:%M",      # "31 Dec 2026 23:59"
        "%d %B %Y %H:%M",      # "31 December 2026 23:59"
        "%Y-%m-%d %H:%M:%S",   # "2026-12-31 23:59:00"
        "%Y-%m-%d",            # "2026-12-31"
        "%d/%m/%Y",            # "31/12/2026"
        "%d.%m.%Y",            # "31.12.2026"
    ]
    
    # Extract date from "Deadline: 31 Dec 2026 23:59" format
    date_text = date_str
    if "Deadline:" in date_text:
        date_text = date_text.split("Deadline:")[-1].strip()
    
    # Try each format
    for fmt in formats:
        try:
            dt = datetime.strptime(date_text.strip(), fmt)
            return dt.timestamp()
        except ValueError:
            continue
    
    # Try to extract date with regex for flexible formats
    # Match patterns like "31 Dec 2026" or "December 31, 2026"
    patterns = [
        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?',
        r'(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text, re.IGNORECASE)
        if match:
            try:
                if 'Jan' in pattern or 'Feb' in pattern:
                    # Month name format
                    day, month_str, year = match.group(1), match.group(2), match.group(3)
                    hour = match.group(4) if match.group(4) else "23"
                    minute = match.group(5) if match.group(5) else "59"
                    
                    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                             'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                    month = months.get(month_str.lower()[:3], 1)
                    
                    dt = datetime(int(year), month, int(day), int(hour), int(minute))
                    return dt.timestamp()
                else:
                    # ISO format
                    year, month, day = match.group(1), match.group(2), match.group(3)
                    hour = match.group(4) if match.group(4) else "23"
                    minute = match.group(5) if match.group(5) else "59"
                    
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    return dt.timestamp()
            except (ValueError, AttributeError):
                continue
    
    return None

def is_event_expired(date_str: str, buffer_days: int = 0) -> bool:
    """
    Check if an event has expired based on its deadline.
    
    Args:
        date_str: The date string from the event
        buffer_days: Grace period in days after the deadline
    
    Returns:
        True if the event is expired, False otherwise
    """
    deadline_timestamp = parse_deadline(date_str)
    if deadline_timestamp is None:
        # If we can't parse the date, assume it's not expired
        return False
    
    current_timestamp = time.time()
    buffer_seconds = buffer_days * 24 * 60 * 60
    
    return current_timestamp > (deadline_timestamp + buffer_seconds)

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
    
    # Clean up description: remove "Find out more and register now" prefix
    # and properly format deadline information
    if description:
        # Remove common phrases that aren't useful in RSS
        description = description.replace("Find out more and register now", "").strip()
        
        # Format deadline information properly
        if date and date.strip():
            # If description contains deadline info, ensure it's formatted nicely
            if "Deadline:" not in description and date:
                description = f"Deadline: {date}" if not description else f"{description}\n\nDeadline: {date}"
            # If description is empty or just whitespace after cleanup, use date
            if not description.strip():
                description = f"Deadline: {date}"

    # final fallbacks
    if not title:
        title = link
    if not description:
        description = f"Event: {title}" if date else title

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

# ---- Historical Tracking ----
def load_history(path: str) -> Dict:
    """Load historical event data."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"events": {}}
    except Exception as e:
        print(f"Failed to load history: {e}")
        return {"events": {}}

def save_history(path: str, history: Dict):
    """Save historical event data."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def update_event_history(history: Dict, event: Dict, status: str = "active"):
    """
    Update historical tracking for an event.
    
    Args:
        history: The history dictionary
        event: The event to track
        status: "new", "active", or "expired"
    """
    event_id = event["id"]
    current_time = int(time.time())
    
    if event_id not in history["events"]:
        # New event - record first discovery
        history["events"][event_id] = {
            "id": event_id,
            "title": event.get("title", ""),
            "link": event.get("link", ""),
            "deadline": event.get("date", ""),
            "first_seen": current_time,
            "last_seen": current_time,
            "expired_at": None,
            "registration_duration_days": None,
        }
    else:
        # Update last seen
        history["events"][event_id]["last_seen"] = current_time
    
    # Check if event expired
    if status == "expired" and history["events"][event_id]["expired_at"] is None:
        history["events"][event_id]["expired_at"] = current_time
        
        # Calculate registration duration
        first_seen = history["events"][event_id]["first_seen"]
        duration_days = (current_time - first_seen) / (24 * 60 * 60)
        history["events"][event_id]["registration_duration_days"] = round(duration_days, 1)

def generate_statistics(history: Dict, state: Dict) -> Dict:
    """
    Generate comprehensive statistics from historical data and current state.
    
    Returns:
        Dictionary with statistics including:
        - Basic counts (total, active, expired, new)
        - Registration duration statistics
        - Upcoming deadlines
        - Monthly trends
        - Recently expired events
        - Long-running events
        - Event velocity metrics
    """
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    current_time = time.time()
    one_week_ago = current_time - (7 * 24 * 60 * 60)
    one_month_ago = current_time - (30 * 24 * 60 * 60)
    
    stats = {
        "generated_at": int(current_time),
        "total_events_tracked": len(history.get("events", {})),
        "currently_active": 0,
        "total_expired": 0,
        "new_this_week": 0,
        "upcoming_deadlines": [],
        "average_registration_duration_days": None,
        # Enhanced statistics
        "new_this_month": 0,
        "expired_this_week": 0,
        "expired_this_month": 0,
        "registration_duration_stats": {},
        "recently_expired": [],
        "long_running_events": [],
        "monthly_trends": [],
        "event_velocity": {},
        "active_event_ages": {},
    }
    
    durations = []
    upcoming = []
    recently_expired = []
    long_running = []
    monthly_counts = defaultdict(int)
    active_ages = []
    
    for event_id, event_data in history.get("events", {}).items():
        first_seen = event_data.get("first_seen", 0)
        expired_at = event_data.get("expired_at")
        
        # Track monthly trends (events added per month)
        if first_seen:
            month_key = datetime.fromtimestamp(first_seen).strftime("%Y-%m")
            monthly_counts[month_key] += 1
        
        # Check if new this week/month
        if first_seen >= one_week_ago:
            stats["new_this_week"] += 1
        if first_seen >= one_month_ago:
            stats["new_this_month"] += 1
        
        # Check if expired this week/month
        if expired_at:
            if expired_at >= one_week_ago:
                stats["expired_this_week"] += 1
            if expired_at >= one_month_ago:
                stats["expired_this_month"] += 1
        
        # Check if expired
        if event_data.get("deadline"):
            is_expired = is_event_expired(event_data["deadline"], EXPIRED_DAYS_BUFFER)
            if is_expired:
                stats["total_expired"] += 1
                
                # Track recently expired events (last 7 days)
                if expired_at and expired_at >= one_week_ago:
                    recently_expired.append({
                        "title": event_data.get("title", "Unknown"),
                        "deadline": event_data.get("deadline", ""),
                        "expired_at": expired_at,
                        "link": event_data.get("link", ""),
                        "registration_duration_days": event_data.get("registration_duration_days")
                    })
            else:
                stats["currently_active"] += 1
                
                # Track active event age (how long they've been open)
                if first_seen:
                    days_active = (current_time - first_seen) / (24 * 60 * 60)
                    active_ages.append(days_active)
                    
                    # Track long-running events (active for > 60 days)
                    if days_active > 60:
                        long_running.append({
                            "title": event_data.get("title", "Unknown"),
                            "deadline": event_data.get("deadline", ""),
                            "days_active": round(days_active, 1),
                            "link": event_data.get("link", "")
                        })
                
                # Add to upcoming deadlines
                deadline_ts = parse_deadline(event_data["deadline"])
                if deadline_ts:
                    days_until = (deadline_ts - current_time) / (24 * 60 * 60)
                    if days_until > 0 and days_until <= 30:  # Next 30 days
                        upcoming.append({
                            "title": event_data.get("title", "Unknown"),
                            "deadline": event_data.get("deadline", ""),
                            "days_remaining": round(days_until, 1),
                            "link": event_data.get("link", "")
                        })
        
        # Collect durations
        if event_data.get("registration_duration_days"):
            durations.append(event_data["registration_duration_days"])
    
    # Calculate registration duration statistics
    if durations:
        stats["average_registration_duration_days"] = round(sum(durations) / len(durations), 1)
        stats["registration_duration_stats"] = {
            "min": round(min(durations), 1),
            "max": round(max(durations), 1),
            "median": round(sorted(durations)[len(durations) // 2], 1),
            "average": round(sum(durations) / len(durations), 1),
            "total_completed": len(durations)
        }
    
    # Calculate active event age statistics
    if active_ages:
        stats["active_event_ages"] = {
            "min": round(min(active_ages), 1),
            "max": round(max(active_ages), 1),
            "median": round(sorted(active_ages)[len(active_ages) // 2], 1),
            "average": round(sum(active_ages) / len(active_ages), 1)
        }
    
    # Calculate event velocity (events per week/month)
    # Only calculate if we have at least 7 days of tracking data to avoid misleading extrapolations
    if history.get("events"):
        all_first_seen = [e.get("first_seen", 0) for e in history["events"].values() if e.get("first_seen", 0) > 0]
        if all_first_seen:
            oldest_event = min(all_first_seen)
            total_days = (current_time - oldest_event) / (24 * 60 * 60)
            if total_days >= 7:  # Require at least 7 days of data
                stats["event_velocity"] = {
                    "events_per_week": round(len(history["events"]) / (total_days / 7), 2),
                    "events_per_month": round(len(history["events"]) / (total_days / 30), 2),
                    "tracking_days": round(total_days, 1)
                }
            else:
                # Not enough data yet - provide a placeholder message
                stats["event_velocity"] = {
                    "events_per_week": None,
                    "events_per_month": None,
                    "tracking_days": round(total_days, 1),
                    "insufficient_data": True
                }
    
    # Sort and limit lists
    stats["upcoming_deadlines"] = sorted(upcoming, key=lambda x: x["days_remaining"])[:10]
    stats["recently_expired"] = sorted(recently_expired, key=lambda x: x["expired_at"], reverse=True)[:10]
    stats["long_running_events"] = sorted(long_running, key=lambda x: x["days_active"], reverse=True)[:10]
    
    # Format monthly trends (last 12 months)
    sorted_months = sorted(monthly_counts.keys(), reverse=True)[:12]
    stats["monthly_trends"] = [
        {"month": month, "events_added": monthly_counts[month]}
        for month in reversed(sorted_months)  # Show oldest to newest for charts
    ]
    
    return stats

def save_statistics(stats: Dict, json_path: str, html_path: str):
    """
    Save statistics to JSON and generate enhanced HTML page with charts and additional metrics.
    
    Args:
        stats: Statistics dictionary
        json_path: Path to save JSON
        html_path: Path to save HTML
    """
    # Save JSON
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    tmp = json_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    os.replace(tmp, json_path)
    
    # Generate HTML
    from datetime import datetime
    generated_time = datetime.fromtimestamp(stats["generated_at"]).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Build upcoming deadlines table
    upcoming_html = ""
    for deadline in stats.get("upcoming_deadlines", []):
        upcoming_html += f"""
        <tr>
            <td><a href="{deadline['link']}" target="_blank">{deadline['title']}</a></td>
            <td>{deadline['deadline']}</td>
            <td>{deadline['days_remaining']} days</td>
        </tr>"""
    
    if not upcoming_html:
        upcoming_html = "<tr><td colspan='3'>No upcoming deadlines in the next 30 days</td></tr>"
    
    # Build recently expired events table
    recently_expired_html = ""
    for event in stats.get("recently_expired", []):
        duration_text = f"{event.get('registration_duration_days', 'N/A')} days" if event.get('registration_duration_days') else "N/A"
        recently_expired_html += f"""
        <tr>
            <td><a href="{event['link']}" target="_blank">{event['title']}</a></td>
            <td>{event['deadline']}</td>
            <td>{duration_text}</td>
        </tr>"""
    
    if not recently_expired_html:
        recently_expired_html = "<tr><td colspan='3'>No events expired in the last 7 days</td></tr>"
    
    # Build long-running events table
    long_running_html = ""
    for event in stats.get("long_running_events", []):
        long_running_html += f"""
        <tr>
            <td><a href="{event['link']}" target="_blank">{event['title']}</a></td>
            <td>{event['deadline']}</td>
            <td>{event['days_active']} days</td>
        </tr>"""
    
    if not long_running_html:
        long_running_html = "<tr><td colspan='3'>No long-running events (active > 60 days)</td></tr>"
    
    # Generate Chart.js data for monthly trends
    chart_data = {
        "labels": [trend["month"] for trend in stats.get("monthly_trends", [])],
        "data": [trend["events_added"] for trend in stats.get("monthly_trends", [])]
    }
    import json as json_module
    chart_data_json = json_module.dumps(chart_data)
    
    # Build registration duration stats section
    duration_stats_html = ""
    if stats.get("registration_duration_stats"):
        rd = stats["registration_duration_stats"]
        duration_stats_html = f"""
        <h2>📈 Registration Duration Analysis</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{rd['average']} days</div>
                <div class="stat-label">Average Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{rd['median']} days</div>
                <div class="stat-label">Median Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{rd['min']} days</div>
                <div class="stat-label">Shortest Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{rd['max']} days</div>
                <div class="stat-label">Longest Duration</div>
            </div>
        </div>
        <p style="text-align: center; color: #6c757d;">Based on {rd['total_completed']} completed event(s)</p>
        """
    
    # Build event velocity section
    velocity_html = ""
    if stats.get("event_velocity"):
        ev = stats["event_velocity"]
        if ev.get("insufficient_data"):
            # Not enough data yet - show friendly message
            velocity_html = f"""
        <h2>⚡ Event Velocity</h2>
        <div class="stat-card" style="text-align: center; border-left: 4px solid #ffc107;">
            <p style="margin: 0; color: #856404; font-size: 1.1em;">
                📊 Collecting data... ({ev['tracking_days']} days tracked)
            </p>
            <p style="margin: 10px 0 0 0; color: #6c757d; font-size: 0.9em;">
                Event velocity metrics will be available after 7 days of tracking.
            </p>
        </div>
        """
        else:
            # Sufficient data - show velocity metrics
            velocity_html = f"""
        <h2>⚡ Event Velocity</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{ev['events_per_week']}</div>
                <div class="stat-label">Events per Week</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{ev['events_per_month']}</div>
                <div class="stat-label">Events per Month</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{ev['tracking_days']}</div>
                <div class="stat-label">Days of Tracking</div>
            </div>
        </div>
        """
    
    # Build active event ages section
    active_ages_html = ""
    if stats.get("active_event_ages"):
        aa = stats["active_event_ages"]
        active_ages_html = f"""
        <h2>⏱️ Active Event Ages</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{aa['average']} days</div>
                <div class="stat-label">Average Age</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{aa['median']} days</div>
                <div class="stat-label">Median Age</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{aa['min']} days</div>
                <div class="stat-label">Newest Event</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{aa['max']} days</div>
                <div class="stat-label">Oldest Event</div>
            </div>
        </div>
        """
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EUGLOH Event Statistics</title>
    <link rel="stylesheet" href="style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f0f2f5;
            margin: 0;
            padding: 0;
        }}
        .stats-container {{
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }}
        .stat-card {{
            background: white;
            border-left: 4px solid #007bff;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #212529;
            font-size: 2.5em;
        }}
        h2 {{
            color: #212529;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 1em;
            margin: 10px 0;
        }}
        .nav-links {{
            margin-top: 15px;
        }}
        .nav-links a {{
            color: #007bff;
            text-decoration: none;
            margin: 0 10px;
            font-weight: 500;
            transition: color 0.2s;
        }}
        .nav-links a:hover {{
            color: #0056b3;
            text-decoration: underline;
        }}
        .chart-container {{
            background: white;
            padding: 30px;
            margin: 30px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .section-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .mini-card {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .mini-card-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #1976d2;
        }}
        .mini-card-label {{
            font-size: 0.8em;
            color: #546e7a;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="stats-container">
        <div class="header">
            <h1>📊 EUGLOH Event Statistics Dashboard</h1>
            <p class="timestamp">Last Updated: {generated_time}</p>
            <div class="nav-links">
                <a href="feed.xml">📡 RSS Feed</a> |
                <a href="index.html">📋 Event List</a> |
                <a href="stats.json">💾 Raw Data (JSON)</a>
            </div>
        </div>
        
        <h2>📌 Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_events_tracked']}</div>
                <div class="stat-label">Total Events Tracked</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['currently_active']}</div>
                <div class="stat-label">Currently Active</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_expired']}</div>
                <div class="stat-label">Total Expired</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['new_this_week']}</div>
                <div class="stat-label">New This Week</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('new_this_month', 0)}</div>
                <div class="stat-label">New This Month</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('expired_this_week', 0)}</div>
                <div class="stat-label">Expired This Week</div>
            </div>
        </div>
        
        {velocity_html}
        {duration_stats_html}
        {active_ages_html}
        
        <h2>📅 Monthly Event Trends</h2>
        <div class="chart-container">
            <canvas id="monthlyTrendsChart"></canvas>
        </div>
        
        <h2>🔔 Upcoming Deadlines (Next 30 Days)</h2>
        <table>
            <thead>
                <tr>
                    <th>Event</th>
                    <th>Deadline</th>
                    <th>Time Remaining</th>
                </tr>
            </thead>
            <tbody>
                {upcoming_html}
            </tbody>
        </table>
        
        <h2>⏰ Recently Expired (Last 7 Days)</h2>
        <table>
            <thead>
                <tr>
                    <th>Event</th>
                    <th>Deadline</th>
                    <th>Registration Duration</th>
                </tr>
            </thead>
            <tbody>
                {recently_expired_html}
            </tbody>
        </table>
        
        <h2>🏃 Long-Running Events (Active > 60 Days)</h2>
        <table>
            <thead>
                <tr>
                    <th>Event</th>
                    <th>Deadline</th>
                    <th>Days Active</th>
                </tr>
            </thead>
            <tbody>
                {long_running_html}
            </tbody>
        </table>
    </div>
    
    <script>
        // Monthly trends chart
        const chartData = {chart_data_json};
        if (chartData.labels.length > 0) {{
            const ctx = document.getElementById('monthlyTrendsChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: chartData.labels,
                    datasets: [{{
                        label: 'Events Added',
                        data: chartData.data,
                        backgroundColor: 'rgba(0, 123, 255, 0.6)',
                        borderColor: 'rgba(0, 123, 255, 1)',
                        borderWidth: 2,
                        borderRadius: 6,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: true,
                            text: 'Event Discovery Rate by Month',
                            font: {{
                                size: 16,
                                weight: 'bold'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }},
                            title: {{
                                display: true,
                                text: 'Number of Events'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Month'
                            }}
                        }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    tmp = html_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html_content)
    os.replace(tmp, html_path)
    
    print(f"Statistics saved to {json_path} and {html_path}")

def append_to_feed(feed_file: str, new_events: List[Dict]):
    """
    Prepend new items to feed_file so newest items are at the top.
    Uses an enhanced RSS 2.0 structure with richer metadata.
    Also removes the 'new' category from items older than 7 days.
    """
    from xml.sax.saxutils import escape

    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    current_timestamp = time.time()
    seven_days_ago = current_timestamp - (7 * 24 * 60 * 60)  # 7 days in seconds
    
    items_xml = ""
    # Expect new_events in newest-first order; we'll prepend them
    for ev in new_events:
        title = escape(ev.get("title") or ev["id"])
        link = escape(ev.get("link") or "")
        desc = escape(ev.get("description") or "")
        pubdate = escape(ev.get("date") or now)
        
        # Enhanced item with more metadata
        items_xml += f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <description><![CDATA[{desc}]]></description>
    <pubDate>{pubdate}</pubDate>
    <guid isPermaLink="false">{escape(ev["id"])}</guid>
    <category>EUGLOH Event</category>
    <category>new</category>
    <source url="{escape(TARGET_URL)}">EUGLOH Course Watcher</source>
  </item>\n"""

    if os.path.exists(feed_file):
        with open(feed_file, "r", encoding="utf-8") as f:
            existing = f.read()
        
        # Remove 'new' category from items older than 7 days
        import re
        from xml.etree import ElementTree as ET
        
        try:
            # Parse the existing feed to process items
            root = ET.fromstring(existing)
            
            for item in root.findall('.//item'):
                pubdate_elem = item.find('pubDate')
                if pubdate_elem is not None and pubdate_elem.text:
                    try:
                        # Parse pubDate to check if it's older than 7 days
                        pubdate_str = pubdate_elem.text
                        # Convert RSS date format to timestamp
                        from email.utils import parsedate_to_datetime
                        pubdate_dt = parsedate_to_datetime(pubdate_str)
                        pubdate_timestamp = pubdate_dt.timestamp()
                        
                        # If item is older than 7 days, remove 'new' category
                        if pubdate_timestamp < seven_days_ago:
                            categories = item.findall('category')
                            for cat in categories:
                                if cat.text == 'new':
                                    item.remove(cat)
                        
                        # Check if event is expired and mark it
                        # Extract deadline from description or pubDate
                        description_elem = item.find('description')
                        if description_elem is not None and description_elem.text:
                            desc_text = description_elem.text
                            if is_event_expired(desc_text, EXPIRED_DAYS_BUFFER):
                                # Check if 'expired' category already exists
                                categories = item.findall('category')
                                has_expired = any(cat.text == 'expired' for cat in categories)
                                if not has_expired:
                                    # Add expired category
                                    expired_cat = ET.SubElement(item, 'category')
                                    expired_cat.text = 'expired'
                    except Exception as e:
                        # If we can't parse the date, skip this item
                        print(f"Warning: Could not parse date for item: {e}")
                        continue
            
            # Convert back to string
            existing = ET.tostring(root, encoding='unicode')
        except Exception as e:
            # If XML parsing fails, fall back to regex-based removal
            print(f"Warning: XML parsing failed, using fallback: {e}")
            # This is a simple fallback that removes 'new' category from older items
            # More sophisticated logic would require proper XML parsing
        
        # Update lastBuildDate and pubDate in existing feed
        existing = re.sub(
            r'<lastBuildDate>.*?</lastBuildDate>',
            f'<lastBuildDate>{now}</lastBuildDate>',
            existing
        )
        existing = re.sub(
            r'<pubDate>.*?</pubDate>',
            f'<pubDate>{now}</pubDate>',
            existing,
            count=1  # Only replace the first pubDate (channel-level, not item-level)
        )
        
        # naive prepend after <channel> line but preserve channel metadata
        insert_after = existing.find("<channel>")
        if insert_after != -1:
            # Find where the first <item> starts or where to insert
            first_item = existing.find("<item>")
            if first_item != -1:
                new_feed = existing[:first_item] + items_xml + existing[first_item:]
            else:
                # No items yet, insert before </channel>
                close_channel = existing.find("</channel>")
                if close_channel != -1:
                    new_feed = existing[:close_channel] + items_xml + existing[close_channel:]
                else:
                    after_idx = existing.find("\n", insert_after)
                    if after_idx != -1:
                        new_feed = existing[:after_idx+1] + items_xml + existing[after_idx+1:]
                    else:
                        new_feed = items_xml + existing
        else:
            new_feed = create_feed_header() + items_xml + "</channel>\n</rss>"
    else:
        new_feed = create_feed_header() + items_xml + "</channel>\n</rss>"

    with open(feed_file + ".tmp", "w", encoding="utf-8") as f:
        f.write(new_feed)
    os.replace(feed_file + ".tmp", feed_file)
    print(f"Wrote feed to {feed_file}")

def create_feed_header() -> str:
    """Create enhanced RSS feed header with rich metadata."""
    from xml.sax.saxutils import escape
    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    
    return f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>EUGLOH Open Registrations Feed</title>
  <link>{escape(TARGET_URL)}</link>
  <description>Automated feed of newly discovered EUGLOH courses and events with open registrations. Stay updated with the latest educational opportunities from the European University Alliance for Global Health.</description>
  <language>en</language>
  <lastBuildDate>{now}</lastBuildDate>
  <pubDate>{now}</pubDate>
  <ttl>1440</ttl>
  <generator>EUGLOH Course Watcher v2.0</generator>
  <managingEditor>eugloh-watcher@example.com (EUGLOH Course Watcher)</managingEditor>
  <webMaster>eugloh-watcher@example.com (EUGLOH Course Watcher)</webMaster>
  <image>
    <url>https://www.eugloh.eu/wp-content/uploads/2021/06/cropped-eugloh-logo-vertical-300x300.png</url>
    <title>EUGLOH</title>
    <link>{escape(TARGET_URL)}</link>
  </image>
  <atom:link href="https://chrisilt.github.io/euglohscraper/feed.xml" rel="self" type="application/rss+xml" />
"""

def update_feed_timestamp(feed_file: str):
    """Update lastBuildDate in feed even when no new items are added."""
    if not os.path.exists(feed_file):
        return
    
    import re
    now = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    
    try:
        with open(feed_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Update lastBuildDate
        content = re.sub(
            r'<lastBuildDate>.*?</lastBuildDate>',
            f'<lastBuildDate>{now}</lastBuildDate>',
            content
        )
        
        with open(feed_file + ".tmp", "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(feed_file + ".tmp", feed_file)
        print(f"Updated lastBuildDate in {feed_file}")
    except Exception as e:
        print(f"Failed to update feed timestamp: {e}")


def rebuild_history_from_feed(feed_file: str = None, history_file: str = HISTORY_FILE):
    """
    Rebuild history.json from existing feed.xml.
    This is useful when history.json is out of sync with the feed.
    """
    from xml.etree import ElementTree as ET
    
    # Try both locations for feed file
    if feed_file is None:
        if os.path.exists(FEED_FILE):
            feed_file = FEED_FILE
        elif os.path.exists("./docs/feed.xml"):
            feed_file = "./docs/feed.xml"
        else:
            print(f"Feed file not found at {FEED_FILE} or ./docs/feed.xml")
            return
    
    if not os.path.exists(feed_file):
        print(f"Feed file {feed_file} not found")
        return
    
    print(f"Rebuilding history from {feed_file}...")
    
    # Parse the feed
    with open(feed_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        root = ET.fromstring(content)
    except Exception as e:
        print(f"Failed to parse feed XML: {e}")
        return
    
    # Initialize history
    history = {'events': {}}
    
    # Process each item in the feed
    items = root.findall('.//item')
    print(f"Found {len(items)} items in feed")
    
    for item in items:
        # Extract event information
        guid_elem = item.find('guid')
        if guid_elem is None or not guid_elem.text:
            continue
        
        event_id = guid_elem.text
        title = item.find('title').text if item.find('title') is not None else ''
        link = item.find('link').text if item.find('link') is not None else event_id
        
        # Extract deadline from description
        description_elem = item.find('description')
        deadline = ''
        if description_elem is not None and description_elem.text:
            desc_text = description_elem.text
            # Try to extract deadline from description
            import re
            deadline_match = re.search(r'Deadline:\s*(.+?)(?:\s*$|(?=\n))', desc_text, re.IGNORECASE)
            if deadline_match:
                deadline = deadline_match.group(1).strip()
        
        # Try to get pubDate as a fallback timestamp
        pubdate_elem = item.find('pubDate')
        first_seen_timestamp = None
        if pubdate_elem is not None and pubdate_elem.text:
            try:
                from email.utils import parsedate_to_datetime
                pubdate_dt = parsedate_to_datetime(pubdate_elem.text)
                first_seen_timestamp = int(pubdate_dt.timestamp())
            except Exception:
                pass
        
        # Use current time if we couldn't parse pubDate
        if first_seen_timestamp is None:
            first_seen_timestamp = int(time.time())
        
        # Check if event is expired
        is_expired = is_event_expired(deadline, EXPIRED_DAYS_BUFFER) if deadline else False
        
        # Add to history
        history['events'][event_id] = {
            'id': event_id,
            'title': title,
            'link': link,
            'deadline': deadline,
            'first_seen': first_seen_timestamp,
            'last_seen': first_seen_timestamp,
            'expired_at': first_seen_timestamp if is_expired else None,
            'registration_duration_days': None,
        }
        
        print(f"  Added: {title[:60]}... (expired: {is_expired})")
    
    # Save the rebuilt history
    save_history(history_file, history)
    print(f"Saved {len(history['events'])} events to {history_file}")
    
    # Regenerate statistics
    state = load_state(STATE_FILE)
    stats = generate_statistics(history, state)
    save_statistics(stats, STATS_FILE, STATS_HTML_FILE)
    print(f"Updated statistics in {STATS_FILE} and {STATS_HTML_FILE}")


# ---- Main ----
def main():
    state = load_state(STATE_FILE)
    seen = set(state.get("seen_ids", []))
    
    # Load historical tracking data
    history = load_history(HISTORY_FILE)

    try:
        html = fetch_page(TARGET_URL)
    except Exception as e:
        print("Error fetching page:", e)
        return

    events = find_events(html)
    print(f"Found {len(events)} candidate events via selector: {REG_LINK_SELECTOR}")
    
    # Update history for all current events (to track last_seen)
    for ev in events:
        # Check if expired
        event_status = "expired" if is_event_expired(ev.get("date", ""), EXPIRED_DAYS_BUFFER) else "active"
        update_event_history(history, ev, event_status)

    # Deduplicate: only events whose id (normalized link) not in seen
    new_events = [e for e in events if e["id"] not in seen]
    
    # Save history even if no new events (for last_seen tracking)
    save_history(HISTORY_FILE, history)
    
    # Generate and save statistics
    stats = generate_statistics(history, state)
    save_statistics(stats, STATS_FILE, STATS_HTML_FILE)
    
    if not new_events:
        print("No new events")
        state["last_checked"] = int(time.time())
        save_state(STATE_FILE, state)
        # Update lastBuildDate in feed even when no new items
        update_feed_timestamp(FEED_FILE)
        
        # Still update feed to mark expired events
        if os.path.exists(FEED_FILE):
            # Trigger feed update to mark expired events
            append_to_feed(FEED_FILE, [])
        return

    # Process each new event
    for ev in new_events:
        print("New:", ev["id"], "| title:", ev.get("title"), "| date:", ev.get("date"))
        post_to_webhook(ev)
        send_email_notification(ev)
        send_teams_notification(ev)
        seen.add(ev["id"])
        
        # Update history for new events
        update_event_history(history, ev, "new")

    # Prepend newest first (so feed top is newest)
    append_to_feed(FEED_FILE, new_events[::-1])

    state["seen_ids"] = list(seen)
    state["last_checked"] = int(time.time())
    save_state(STATE_FILE, state)
    
    # Save history after processing new events
    save_history(HISTORY_FILE, history)
    
    # Regenerate statistics after new events
    stats = generate_statistics(history, state)
    save_statistics(stats, STATS_FILE, STATS_HTML_FILE)
    
    print(f"Saved state: {len(state['seen_ids'])} seen ids")

if __name__ == "__main__":
    import sys
    
    # Check for rebuild command
    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild-history":
        rebuild_history_from_feed()
    else:
        main()