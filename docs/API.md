# API Documentation

This document provides detailed information about the functions, classes, and modules in the EUGLOH Course Watcher.

## Table of Contents

- [Module: check_events.py](#module-check_eventspy)
  - [Configuration](#configuration)
  - [Utility Functions](#utility-functions)
  - [Scraping Functions](#scraping-functions)
  - [Notification Functions](#notification-functions)
  - [Historical Tracking Functions](#historical-tracking-functions)
  - [Statistics Functions](#statistics-functions)
  - [Feed Management Functions](#feed-management-functions)
  - [Main Function](#main-function)

---

## Module: check_events.py

The main application module containing all scraping, processing, and notification logic.

### Configuration

Environment variables used for configuration:

#### Scraping Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET_URL` | string | EUGLOH URL | URL to scrape for events |
| `REG_LINK_SELECTOR` | string | Multiple selectors | CSS selector(s) for registration links |
| `TITLE_SELECTOR` | string | `"h5.headline"` | CSS selector for event titles |
| `DATE_SELECTOR` | string | `"time, .date"` | CSS selector for event dates |
| `USER_AGENT` | string | `"eugloh-event-checker/1.0"` | HTTP User-Agent header |
| `REQUEST_TIMEOUT` | int | `15` | HTTP request timeout in seconds |

#### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STATE_FILE` | string | `"./seen.json"` | Path to deduplication state file |
| `FEED_FILE` | string | `"./feed.xml"` | Path to output RSS feed |
| `HISTORY_FILE` | string | `"./history.json"` | Path to historical tracking data |
| `STATS_FILE` | string | `"./docs/stats.json"` | Path to statistics JSON |
| `STATS_HTML_FILE` | string | `"./docs/stats.html"` | Path to statistics dashboard |

#### Notification Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBHOOK_URL` | string | `None` | Generic webhook URL (optional) |
| `EMAIL_ENABLED` | boolean | `false` | Enable email notifications |
| `EMAIL_FROM` | string | `""` | Sender email address |
| `EMAIL_TO` | string | `""` | Recipient email address(es) |
| `EMAIL_SMTP_HOST` | string | `""` | SMTP server hostname |
| `EMAIL_SMTP_PORT` | int | `587` | SMTP server port |
| `EMAIL_SMTP_USER` | string | `""` | SMTP username |
| `EMAIL_SMTP_PASSWORD` | string | `""` | SMTP password |
| `TEAMS_WEBHOOK_URL` | string | `""` | Microsoft Teams webhook URL |

#### Behavior Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXPIRED_DAYS_BUFFER` | int | `0` | Grace period in days after deadline |

---

### Utility Functions

#### `load_state(path: str) -> Dict`

Load the deduplication state from a JSON file.

**Parameters**:
- `path` (str): Path to the state file

**Returns**:
- `Dict`: State dictionary with keys:
  - `seen_ids` (List[str]): List of seen event IDs
  - `last_checked` (int|None): Unix timestamp of last check

**Example**:
```python
state = load_state("./seen.json")
print(f"Previously seen: {len(state['seen_ids'])} events")
```

---

#### `save_state(path: str, state: Dict) -> None`

Save the deduplication state to a JSON file atomically.

**Parameters**:
- `path` (str): Path to the state file
- `state` (Dict): State dictionary to save

**Implementation Details**:
- Uses atomic write via `.tmp` file
- Ensures data integrity on failure
- UTF-8 encoding with pretty printing

**Example**:
```python
state = {"seen_ids": ["event1", "event2"], "last_checked": 1234567890}
save_state("./seen.json", state)
```

---

#### `normalize_url(url: str) -> str`

Normalize a URL to create a stable event ID by removing query parameters and fragments.

**Parameters**:
- `url` (str): URL to normalize (can be relative or absolute)

**Returns**:
- `str`: Normalized absolute URL without query params or fragments

**Example**:
```python
url = normalize_url("/event/123?ref=homepage#section")
# Returns: "https://www.eugloh.eu/event/123"
```

---

### Scraping Functions

#### `fetch_page(url: str) -> str`

Fetch HTML content from a URL with proper headers and timeout.

**Parameters**:
- `url` (str): URL to fetch

**Returns**:
- `str`: HTML content

**Raises**:
- `requests.HTTPError`: If HTTP request fails
- `requests.Timeout`: If request times out

**Example**:
```python
html = fetch_page("https://www.eugloh.eu/courses-trainings/")
```

---

#### `find_events(html: str) -> List[Dict]`

Find all events in HTML by applying the configured CSS selectors.

**Parameters**:
- `html` (str): HTML content to parse

**Returns**:
- `List[Dict]`: List of event dictionaries, each containing:
  - `id` (str): Normalized event URL
  - `title` (str): Event title
  - `date` (str): Event date/deadline
  - `link` (str): Registration URL
  - `description` (str): Event description

**Example**:
```python
html = fetch_page(TARGET_URL)
events = find_events(html)
print(f"Found {len(events)} events")
```

---

#### `extract_event_from_anchor(a_tag: Tag) -> Optional[Dict]`

Extract event details from an anchor tag and its surrounding HTML.

**Parameters**:
- `a_tag` (BeautifulSoup Tag): Anchor tag containing registration link

**Returns**:
- `Dict|None`: Event dictionary or None if extraction fails

**Extraction Strategy**:
1. Extract `href` for event ID and link
2. Search ancestors for title using `TITLE_SELECTOR`
3. Search ancestors for date using `DATE_SELECTOR`
4. Extract description from nearby `<p>` tags
5. Clean and format extracted data

**Example**:
```python
from bs4 import BeautifulSoup

html = "<div><h5 class='headline'>Event</h5><a href='/register'>Register</a></div>"
soup = BeautifulSoup(html, 'html.parser')
anchor = soup.find('a')
event = extract_event_from_anchor(anchor)
```

---

#### `_find_in_ancestors(el: Tag, css_selector: str, max_levels: int = 6) -> Optional[Tag]`

Search up the DOM tree to find an element matching a CSS selector.

**Parameters**:
- `el` (Tag): Starting element
- `css_selector` (str): CSS selector to match
- `max_levels` (int): Maximum ancestor levels to search

**Returns**:
- `Tag|None`: First matching element or None

**Example**:
```python
date_element = _find_in_ancestors(anchor, "time, .date", max_levels=6)
```

---

### Date and Expiration Functions

#### `parse_deadline(date_str: str) -> Optional[float]`

Parse a deadline date string and convert to Unix timestamp.

**Parameters**:
- `date_str` (str): Date string in various formats

**Returns**:
- `float|None`: Unix timestamp or None if parsing fails

**Supported Formats**:
- `"31 Dec 2026 23:59"`
- `"31 December 2026 23:59"`
- `"2026-12-31 23:59:00"`
- `"2026-12-31"`
- `"31/12/2026"`
- `"31.12.2026"`
- `"Deadline: 31 Dec 2026 23:59"` (with prefix)

**Example**:
```python
timestamp = parse_deadline("31 Dec 2026 23:59")
if timestamp:
    print(f"Deadline: {timestamp}")
```

---

#### `is_event_expired(date_str: str, buffer_days: int = 0) -> bool`

Check if an event has expired based on its deadline.

**Parameters**:
- `date_str` (str): Date string to check
- `buffer_days` (int): Grace period in days after deadline

**Returns**:
- `bool`: True if expired, False otherwise

**Logic**:
- Parses deadline using `parse_deadline()`
- Compares with current time + buffer
- Returns False if date cannot be parsed (fail-safe)

**Example**:
```python
if is_event_expired("1 Jan 2020 00:00", buffer_days=0):
    print("Event has expired")
```

---

### Notification Functions

#### `post_to_webhook(ev: Dict) -> None`

POST event data to a generic webhook URL (Zapier, Make, etc.).

**Parameters**:
- `ev` (Dict): Event dictionary

**Behavior**:
- Sends JSON payload via HTTP POST
- Logs success/failure
- Does not raise exceptions (fail-safe)

**Payload**:
```json
{
  "id": "https://example.com/event1",
  "title": "Event Title",
  "date": "31 Dec 2026",
  "link": "https://example.com/event1",
  "description": "Event description"
}
```

**Example**:
```python
event = {"id": "event1", "title": "Test", "link": "https://..."}
post_to_webhook(event)
```

---

#### `send_email_notification(ev: Dict) -> None`

Send email notification for a new event.

**Parameters**:
- `ev` (Dict): Event dictionary

**Behavior**:
- Sends both plain text and HTML versions
- Uses SMTP with STARTTLS
- Escapes HTML entities for security
- Logs success/failure
- Does not raise exceptions (fail-safe)

**Email Format**:
- **Subject**: `"New EUGLOH Event: {title}"`
- **Body**: Event details with clickable link

**Example**:
```python
event = {"title": "Workshop", "date": "Jan 1", "link": "https://...", "description": "..."}
send_email_notification(event)
```

---

#### `send_teams_notification(ev: Dict) -> None`

Send Microsoft Teams notification using incoming webhook.

**Parameters**:
- `ev` (Dict): Event dictionary

**Behavior**:
- Sends Adaptive Card format
- Includes action button to view event
- Logs success/failure
- Does not raise exceptions (fail-safe)

**Card Structure**:
- Title: "New EUGLOH Event Detected!"
- Activity Title: Event title
- Activity Subtitle: Event date
- Facts: Event description
- Action: "View Event" button

**Example**:
```python
event = {"title": "Seminar", "date": "Feb 1", "link": "https://...", "description": "..."}
send_teams_notification(event)
```

---

### Historical Tracking Functions

#### `load_history(path: str) -> Dict`

Load historical event tracking data from JSON file.

**Parameters**:
- `path` (str): Path to history file

**Returns**:
- `Dict`: History dictionary with key:
  - `events` (Dict[str, Dict]): Event ID → event data mapping

**Example**:
```python
history = load_history("./history.json")
print(f"Tracking {len(history['events'])} events")
```

---

#### `save_history(path: str, history: Dict) -> None`

Save historical tracking data to JSON file atomically.

**Parameters**:
- `path` (str): Path to history file
- `history` (Dict): History dictionary

**Example**:
```python
save_history("./history.json", history)
```

---

#### `update_event_history(history: Dict, event: Dict, status: str = "active") -> None`

Update historical tracking for an event.

**Parameters**:
- `history` (Dict): History dictionary to update
- `event` (Dict): Event to track
- `status` (str): Event status - "new", "active", or "expired"

**Behavior**:
- **New event**: Records `first_seen` timestamp
- **Existing event**: Updates `last_seen` timestamp
- **Expired event**: Sets `expired_at` and calculates `registration_duration_days`

**Example**:
```python
history = load_history("./history.json")
event = {"id": "event1", "title": "Test", "date": "..."}
update_event_history(history, event, "new")
save_history("./history.json", history)
```

---

#### `rebuild_history_from_feed(feed_file: str = None, history_file: str = HISTORY_FILE) -> None`

Rebuild history.json from existing feed.xml. Useful for recovery or migration.

**Parameters**:
- `feed_file` (str): Path to RSS feed file (auto-detected if None)
- `history_file` (str): Path to output history file

**Usage**:
```bash
python check_events.py --rebuild-history
```

---

### Statistics Functions

#### `generate_statistics(history: Dict, state: Dict) -> Dict`

Generate comprehensive statistics from historical data.

**Parameters**:
- `history` (Dict): Historical tracking data
- `state` (Dict): Current state data

**Returns**:
- `Dict`: Statistics dictionary containing:

**Core Metrics**:
- `total_events_tracked` (int): All events discovered
- `currently_active` (int): Events with open registration
- `total_expired` (int): Events past deadline
- `new_this_week` (int): Events discovered in last 7 days
- `new_this_month` (int): Events discovered in last 30 days
- `expired_this_week` (int): Events expired in last 7 days
- `expired_this_month` (int): Events expired in last 30 days

**Registration Duration Stats**:
- `average_registration_duration_days` (float): Mean duration
- `registration_duration_stats` (Dict):
  - `min` (float): Shortest registration period
  - `max` (float): Longest registration period
  - `median` (float): Median duration
  - `average` (float): Average duration
  - `total_completed` (int): Number of completed events

**Event Velocity**:
- `event_velocity` (Dict):
  - `events_per_week` (float): Weekly discovery rate
  - `events_per_month` (float): Monthly discovery rate
  - `tracking_days` (float): Days of tracking data
  - `insufficient_data` (bool): True if < 7 days tracked

**Active Event Ages**:
- `active_event_ages` (Dict):
  - `min` (float): Newest active event (days)
  - `max` (float): Oldest active event (days)
  - `median` (float): Median age
  - `average` (float): Average age

**Lists**:
- `upcoming_deadlines` (List[Dict]): Next 30 days, sorted by proximity
- `recently_expired` (List[Dict]): Last 7 days, sorted by recency
- `long_running_events` (List[Dict]): Active > 60 days
- `monthly_trends` (List[Dict]): Events added per month (last 12 months)

**Example**:
```python
stats = generate_statistics(history, state)
print(f"Active events: {stats['currently_active']}")
print(f"Average duration: {stats['average_registration_duration_days']} days")
```

---

#### `save_statistics(stats: Dict, json_path: str, html_path: str) -> None`

Save statistics to JSON and generate HTML dashboard.

**Parameters**:
- `stats` (Dict): Statistics dictionary from `generate_statistics()`
- `json_path` (str): Output path for JSON file
- `html_path` (str): Output path for HTML dashboard

**HTML Features**:
- Interactive charts using Chart.js
- Responsive design
- Mobile-friendly tables
- Dark mode support via CSS
- Sortable statistics cards

**Example**:
```python
stats = generate_statistics(history, state)
save_statistics(stats, "./docs/stats.json", "./docs/stats.html")
```

---

### Feed Management Functions

#### `create_feed_header() -> str`

Generate RSS 2.0 feed header with metadata.

**Returns**:
- `str`: XML string containing RSS channel metadata

**Includes**:
- Feed title and description
- Language and encoding
- Build date and TTL
- Generator info
- Atom self-link
- Channel image

---

#### `append_to_feed(feed_file: str, new_events: List[Dict]) -> None`

Prepend new items to RSS feed (newest first).

**Parameters**:
- `feed_file` (str): Path to RSS feed file
- `new_events` (List[Dict]): New events to add

**Behavior**:
1. Creates new feed if doesn't exist
2. Prepends new items to existing feed
3. Updates `lastBuildDate` timestamp
4. Removes "new" category from items > 7 days old
5. Adds "expired" category to expired items
6. Uses atomic write for safety

**Item Format**:
```xml
<item>
  <title>Event Title</title>
  <link>https://example.com/event</link>
  <description><![CDATA[Event description]]></description>
  <pubDate>Mon, 01 Jan 2025 12:00:00 +0000</pubDate>
  <guid isPermaLink="false">event-id</guid>
  <category>EUGLOH Event</category>
  <category>new</category>
  <source url="...">EUGLOH Course Watcher</source>
</item>
```

**Example**:
```python
events = [{"id": "event1", "title": "Test", ...}]
append_to_feed("./feed.xml", events)
```

---

#### `update_feed_timestamp(feed_file: str) -> None`

Update the lastBuildDate in RSS feed without adding items.

**Parameters**:
- `feed_file` (str): Path to RSS feed file

**Usage**: Called when no new events found but feed should reflect latest check time.

---

### Main Function

#### `main() -> None`

Main application entry point that orchestrates the entire scraping process.

**Flow**:
1. Load state and history
2. Fetch and parse HTML from target URL
3. Extract events from HTML
4. Update history for all events
5. Identify new events (not in seen list)
6. Send notifications for new events
7. Update RSS feed
8. Generate statistics
9. Save all state files

**Error Handling**:
- Catches fetch failures (logs and exits)
- Continues on notification failures
- Uses atomic file writes for data integrity

**Example**:
```python
if __name__ == "__main__":
    main()
```

---

## Command Line Usage

### Standard Run

```bash
python check_events.py
```

### Rebuild History

Rebuild `history.json` from existing `feed.xml`:

```bash
python check_events.py --rebuild-history
```

---

## Data Types

### Event Dictionary

```python
{
    "id": str,           # Normalized URL (stable identifier)
    "title": str,        # Event title
    "date": str,         # Date/deadline string
    "link": str,         # Registration URL
    "description": str   # Event description
}
```

### State Dictionary

```python
{
    "seen_ids": List[str],    # List of seen event IDs
    "last_checked": int|None  # Unix timestamp of last check
}
```

### History Dictionary

```python
{
    "events": {
        "event-id": {
            "id": str,
            "title": str,
            "link": str,
            "deadline": str,
            "first_seen": int,           # Unix timestamp
            "last_seen": int,            # Unix timestamp
            "expired_at": int|None,      # Unix timestamp
            "registration_duration_days": float|None
        }
    }
}
```

---

## Testing

See `test_check_events.py` for comprehensive unit tests covering all major functions.

Run tests:
```bash
python test_check_events.py
```

---

## Notes

- All file operations use atomic writes (`.tmp` file + rename)
- Notifications are best-effort (failures logged but don't stop execution)
- State is preserved even if later steps fail
- HTML content is properly escaped to prevent XSS
- UTF-8 encoding used throughout
