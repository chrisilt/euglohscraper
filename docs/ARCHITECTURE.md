# EUGLOH Course Watcher - Architecture Documentation

## Overview

The EUGLOH Course Watcher is a Python-based web scraper designed to monitor EUGLOH course and event registration pages, track new events, and deliver notifications through multiple channels (RSS, email, webhooks, Microsoft Teams).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                          │
│  (Scheduled runs: daily at 6 AM UTC or manual trigger)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  check_events.py                             │
│                  (Main Application)                          │
│                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  Scraper   │→ │  Processor   │→ │  Notification    │    │
│  │  Module    │  │  & Tracker   │  │  Dispatcher      │    │
│  └────────────┘  └──────────────┘  └──────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────┐          ┌──────────────┐
│   Storage    │          │ Outputs &    │
│              │          │ Integrations │
│ • seen.json  │          │ • feed.xml   │
│ • history.   │          │ • stats.json │
│   json       │          │ • stats.html │
│              │          │ • Email      │
│              │          │ • Webhooks   │
│              │          │ • Teams      │
└──────────────┘          └──────────────┘
         │
         ▼
┌──────────────────────┐
│   GitHub Pages       │
│   (Public Access)    │
│                      │
│ • Feed viewer        │
│ • Statistics dash    │
│ • RSS feed           │
└──────────────────────┘
```

## Core Components

### 1. Scraper Module

**Purpose**: Fetch and parse HTML from the target EUGLOH website.

**Key Functions**:
- `fetch_page(url)` - Retrieves HTML content with proper headers
- `find_events(html)` - Locates all registration links matching selectors
- `extract_event_from_anchor(a_tag)` - Extracts event details from HTML elements

**Technologies**:
- `requests` - HTTP client
- `BeautifulSoup` - HTML parsing

**Flow**:
1. Fetch HTML from `TARGET_URL`
2. Parse with BeautifulSoup
3. Apply CSS selectors to find registration links
4. Extract title, date, description from surrounding HTML
5. Normalize URLs for stable IDs

### 2. Processor & Tracker

**Purpose**: Track event history, detect changes, and manage state.

**Key Functions**:
- `normalize_url(url)` - Creates stable event IDs
- `load_state(path)` / `save_state(path, state)` - Manages seen events
- `load_history(path)` / `save_history(path, history)` - Tracks full lifecycle
- `update_event_history(history, event, status)` - Records event changes
- `is_event_expired(date_str, buffer_days)` - Checks deadline status
- `parse_deadline(date_str)` - Converts date strings to timestamps

**Data Structures**:

**seen.json** (Deduplication):
```json
{
  "seen_ids": ["https://example.com/event1", ...],
  "last_checked": 1234567890
}
```

**history.json** (Full Lifecycle Tracking):
```json
{
  "events": {
    "https://example.com/event1": {
      "id": "https://example.com/event1",
      "title": "Event Title",
      "link": "https://example.com/event1",
      "deadline": "31 Dec 2026 23:59",
      "first_seen": 1234567890,
      "last_seen": 1234567890,
      "expired_at": null,
      "registration_duration_days": null
    }
  }
}
```

### 3. Notification Dispatcher

**Purpose**: Deliver event notifications through multiple channels.

**Channels**:

1. **RSS Feed** (`feed.xml`)
   - Standard RSS 2.0 format
   - New items prepended (newest first)
   - Includes categories: "EUGLOH Event", "new", "expired"
   - Auto-removes "new" tag after 7 days
   - Auto-adds "expired" tag when deadline passes

2. **Email Notifications**
   - SMTP-based delivery
   - HTML and plain text versions
   - Configurable via environment variables
   - Supports multiple recipients

3. **Generic Webhooks**
   - POST JSON payload to any webhook URL
   - Useful for Zapier, Make, n8n integrations
   - Contains full event details

4. **Microsoft Teams**
   - Adaptive card format
   - Rich formatting with action buttons
   - Direct integration via incoming webhook

### 4. Statistics Engine

**Purpose**: Generate analytics and insights from event data.

**Key Functions**:
- `generate_statistics(history, state)` - Computes all metrics
- `save_statistics(stats, json_path, html_path)` - Outputs data and visualization

**Metrics Calculated**:
- Total events tracked
- Currently active / expired counts
- New events this week/month
- Expired events this week/month
- Average registration duration
- Event velocity (events per week/month)
- Upcoming deadlines (next 30 days)
- Recently expired events (last 7 days)
- Long-running events (active > 60 days)
- Active event age distribution
- Monthly trends (last 12 months)

**Outputs**:
- `stats.json` - Raw data API
- `stats.html` - Interactive dashboard with Chart.js visualizations

## Data Flow

### New Event Discovery Flow

```
1. Scraper runs (scheduled or manual)
   │
   ├─→ Fetch HTML from TARGET_URL
   │
   ├─→ Parse and extract events
   │
   ├─→ For each event:
   │    │
   │    ├─→ Generate normalized ID (URL without query/fragment)
   │    │
   │    ├─→ Check if in seen.json
   │    │
   │    ├─→ If NEW:
   │    │    │
   │    │    ├─→ Add to history.json (first_seen timestamp)
   │    │    ├─→ Prepend to feed.xml with "new" category
   │    │    ├─→ Send email notification (if enabled)
   │    │    ├─→ POST to webhook (if configured)
   │    │    ├─→ Send Teams notification (if configured)
   │    │    └─→ Add to seen.json
   │    │
   │    └─→ If EXISTING:
   │         │
   │         ├─→ Update last_seen in history.json
   │         └─→ Check if expired, mark accordingly
   │
   ├─→ Update statistics
   │    │
   │    ├─→ Calculate all metrics
   │    ├─→ Generate stats.json
   │    └─→ Generate stats.html
   │
   └─→ Save all state files
        │
        ├─→ seen.json
        ├─→ history.json
        ├─→ feed.xml
        ├─→ stats.json
        └─→ stats.html
```

### Expired Event Handling Flow

```
1. Event deadline check
   │
   ├─→ Parse deadline from event data
   │
   ├─→ Compare with current time + buffer
   │
   ├─→ If EXPIRED:
   │    │
   │    ├─→ Mark in history.json (expired_at timestamp)
   │    ├─→ Calculate registration_duration_days
   │    ├─→ Add "expired" category to feed.xml item
   │    └─→ Update statistics
   │
   └─→ Continue monitoring (still appears in feed)
```

## Configuration System

### Environment Variables

All configuration is done via environment variables for 12-factor app compliance.

**Configuration Sources** (in priority order):
1. GitHub Actions secrets (for CI/CD)
2. `.env` file (for local development)
3. System environment variables
4. Default values in code

**Configuration Groups**:
- **Scraping**: URL, selectors, timeouts
- **Storage**: File paths for state and output
- **Notifications**: Email, webhooks, Teams
- **Behavior**: Expiration buffers, retry logic

See `.env.example` for complete configuration reference.

## Deployment Models

### 1. GitHub Actions (Recommended)

**Characteristics**:
- Scheduled execution (cron)
- Automatic deployment via GitHub Pages
- Secrets management
- No infrastructure costs
- Audit trail in Actions logs

**Configuration**:
- Workflow file: `.github/workflows/scrape-and-publish.yml`
- Secrets stored in repository settings
- Output committed to `docs/` folder
- Pages served from `docs/` directory

### 2. Local Execution

**Characteristics**:
- On-demand execution
- Local file system storage
- Manual deployment of outputs

**Setup**:
```bash
python check_events.py  # Run once
```

### 3. Server/Cron Deployment

**Characteristics**:
- Self-hosted on VPS or server
- Cron-based scheduling
- Full control over environment

**Setup**:
```bash
# Add to crontab
0 6 * * * cd /path/to/euglohscraper && /path/to/venv/bin/python check_events.py
```

## Security Considerations

### Input Validation

- **HTML Parsing**: BeautifulSoup handles malformed HTML safely
- **URL Validation**: URLs are normalized and validated
- **Date Parsing**: Fails gracefully with None for invalid dates

### Output Sanitization

- **XML/RSS**: All user content is XML-escaped using `xml.sax.saxutils.escape`
- **Email HTML**: HTML entities are escaped using `html.escape`
- **CDATA Sections**: Used for rich content in RSS descriptions

### Secrets Management

- **No hardcoded secrets**: All sensitive data via environment variables
- **GitHub Secrets**: Used in Actions workflow
- **Local .env**: Not committed to repository (in .gitignore)

### Dependencies

- **Minimal dependencies**: Only `requests` and `beautifulsoup4`
- **No known vulnerabilities**: Keep dependencies updated
- **Requirements pinned**: Version constraints in requirements.txt

## Performance Characteristics

### Execution Time

- **Typical run**: 2-5 seconds
- **Network request**: 1-3 seconds (depends on target site)
- **Parsing**: < 1 second
- **Statistics generation**: < 1 second

### Resource Usage

- **Memory**: < 50 MB typical
- **Disk**: Minimal (state files < 1 MB)
- **Network**: Single HTTP request per run

### Scalability

- **Events**: Handles hundreds of events efficiently
- **History**: JSON storage scales to thousands of events
- **Statistics**: Computed on-demand, no database required

## Error Handling

### Graceful Degradation

1. **Network Failures**
   - Timeout after `REQUEST_TIMEOUT` seconds
   - Logs error, exits without modifying state
   - Next run will retry

2. **Parsing Failures**
   - Skips malformed events
   - Logs warnings
   - Continues processing valid events

3. **File I/O Failures**
   - Atomic writes using `.tmp` files
   - Preserves previous state on failure
   - Logs errors for investigation

4. **Notification Failures**
   - Continues even if notification fails
   - Logs error but doesn't prevent state updates
   - Events still tracked and added to feed

## Testing Strategy

### Test Categories

1. **Unit Tests** (`test_check_events.py`)
   - URL normalization
   - Event extraction
   - Deduplication
   - Feed generation
   - Date parsing
   - Expiration logic
   - Statistics calculation

2. **Integration Tests**
   - Full scraper run with mock HTML
   - State persistence
   - Feed updates

3. **Manual Testing**
   - Run against live EUGLOH site
   - Verify email delivery
   - Check webhook integration

## Extensibility

### Adding New Notification Channels

1. Create function in `check_events.py`:
   ```python
   def send_my_notification(ev: Dict):
       """Send notification via My Service."""
       if not MY_SERVICE_URL:
           return
       # Implementation
   ```

2. Call in main loop:
   ```python
   for ev in new_events:
       send_my_notification(ev)
   ```

3. Add configuration:
   - Environment variable
   - Documentation
   - Example in `.env.example`

### Customizing Event Detection

Modify CSS selectors in configuration:
- `REG_LINK_SELECTOR` - Find registration links
- `TITLE_SELECTOR` - Extract event titles
- `DATE_SELECTOR` - Extract dates

### Adding Statistics

Extend `generate_statistics()` function:
1. Add new metric calculation
2. Update `stats` dictionary
3. Update `save_statistics()` HTML template
4. Document in README

## Future Enhancements

Potential improvements:

1. **Database Backend**
   - Replace JSON files with SQLite/PostgreSQL
   - Better query performance
   - Relationship tracking

2. **Advanced Filtering**
   - Filter by event type
   - Category-based subscriptions
   - Location filtering

3. **Web UI**
   - Event search and filtering
   - Subscription management
   - Admin dashboard

4. **Multi-Site Support**
   - Scrape multiple event sources
   - Unified feed
   - Per-source configuration

5. **Machine Learning**
   - Event categorization
   - Deadline prediction
   - Personalized recommendations

## Maintenance

### Regular Tasks

- **Weekly**: Review scraper logs for errors
- **Monthly**: Check for EUGLOH website changes
- **Quarterly**: Update dependencies
- **Annually**: Review and archive old events

### Monitoring

Watch for:
- Failed GitHub Actions runs
- Empty feeds (possible scraper failure)
- Increasing state file sizes
- Notification delivery failures

### Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
