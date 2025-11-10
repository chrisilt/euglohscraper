# Troubleshooting Guide

Common issues and their solutions for the EUGLOH Course Watcher.

## Table of Contents

- [General Issues](#general-issues)
- [Scraping Issues](#scraping-issues)
- [Notification Issues](#notification-issues)
- [Feed Issues](#feed-issues)
- [GitHub Actions Issues](#github-actions-issues)
- [Statistics Issues](#statistics-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)

---

## General Issues

### Scraper Doesn't Run

**Symptoms:**
- No output when running `python check_events.py`
- Immediate exit with no messages

**Possible Causes & Solutions:**

1. **Missing dependencies**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Python version too old**
   ```bash
   # Check Python version (need 3.8+)
   python --version
   
   # Use python3 if needed
   python3 check_events.py
   ```

3. **Import errors**
   ```bash
   # Test imports
   python -c "import requests; from bs4 import BeautifulSoup"
   ```

### Permission Denied Errors

**Symptoms:**
- `PermissionError: [Errno 13] Permission denied: './seen.json'`

**Solution:**
```bash
# Check file permissions
ls -l seen.json feed.xml history.json

# Fix permissions
chmod 644 seen.json feed.xml history.json

# Check directory permissions
chmod 755 docs/
```

### File Not Found Errors

**Symptoms:**
- `FileNotFoundError: [Errno 2] No such file or directory`

**Solution:**
```bash
# Create required directories
mkdir -p docs

# Initialize state files (scraper will create them)
echo '{"seen_ids": [], "last_checked": null}' > seen.json
echo '{"events": {}}' > history.json
```

---

## Scraping Issues

### No Events Found

**Symptoms:**
- Output shows: `Found 0 candidate events via selector`

**Diagnosis:**
```bash
# Test if URL is accessible
curl -I "https://www.eugloh.eu/courses-trainings/?openRegistrations=%5Byes%5D"

# Download page and inspect
curl "https://www.eugloh.eu/courses-trainings/?openRegistrations=%5Byes%5D" > test_page.html

# Check if selectors match
python -c "
from bs4 import BeautifulSoup
with open('test_page.html') as f:
    soup = BeautifulSoup(f, 'html.parser')
    links = soup.select('div.buttons-wrap a.button')
    print(f'Found {len(links)} links')
"
```

**Solutions:**

1. **Website changed structure**
   - Inspect the page source
   - Update selectors in `.env`:
     ```bash
     REG_LINK_SELECTOR="new-selector-here"
     ```

2. **Website blocking scraper**
   - Change User-Agent:
     ```bash
     USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
     ```

3. **No events with open registration**
   - This is normal if no events are currently open
   - Check the EUGLOH website directly

### Incomplete Event Data

**Symptoms:**
- Events missing titles, dates, or descriptions
- Title shows URL instead of event name

**Diagnosis:**
```python
# Test extraction
from check_events import *
from bs4 import BeautifulSoup

html = fetch_page(TARGET_URL)
soup = BeautifulSoup(html, 'html.parser')
links = soup.select(REG_LINK_SELECTOR)

if links:
    print(f"Testing first link...")
    event = extract_event_from_anchor(links[0])
    print(f"Title: {event.get('title')}")
    print(f"Date: {event.get('date')}")
    print(f"Description: {event.get('description')}")
```

**Solutions:**

1. **Update title selector**
   ```bash
   TITLE_SELECTOR="h3, h4, h5.headline"
   ```

2. **Update date selector**
   ```bash
   DATE_SELECTOR="time, .date, .deadline, span[class*='date']"
   ```

3. **Check HTML structure**
   - Save a sample event card: Right-click → Inspect → Copy outerHTML
   - Analyze structure and update selectors accordingly

### Network Timeouts

**Symptoms:**
- `requests.exceptions.Timeout: HTTPSConnectionPool`
- `requests.exceptions.ConnectionError`

**Solutions:**

1. **Increase timeout**
   ```bash
   REQUEST_TIMEOUT="30"
   ```

2. **Check network connectivity**
   ```bash
   ping www.eugloh.eu
   curl -v https://www.eugloh.eu
   ```

3. **Check firewall/proxy**
   ```bash
   # Set proxy if needed
   export HTTP_PROXY="http://proxy:8080"
   export HTTPS_PROXY="http://proxy:8080"
   ```

---

## Notification Issues

### Email Not Sending

**Symptoms:**
- No email received
- Log shows: `Failed to send email: ...`

**Diagnosis:**
```python
# Test email configuration
python -c "
from check_events import *
test_event = {
    'id': 'test',
    'title': 'Test Event',
    'link': 'https://example.com',
    'date': '2025-12-31',
    'description': 'Test description'
}
send_email_notification(test_event)
"
```

**Common Issues & Solutions:**

1. **Wrong SMTP settings**
   ```bash
   # Gmail
   EMAIL_SMTP_HOST="smtp.gmail.com"
   EMAIL_SMTP_PORT="587"
   
   # Outlook
   EMAIL_SMTP_HOST="smtp-mail.outlook.com"
   EMAIL_SMTP_PORT="587"
   
   # Other providers - check their documentation
   ```

2. **Authentication failure**
   - For Gmail: Use [App Password](https://support.google.com/accounts/answer/185833)
   - Enable "Less secure app access" (not recommended)
   - Check 2FA settings

3. **Email not enabled**
   ```bash
   # Make sure it's enabled
   EMAIL_ENABLED="true"
   ```

4. **SMTP blocked by firewall**
   ```bash
   # Test SMTP connection
   telnet smtp.gmail.com 587
   
   # Or use netcat
   nc -zv smtp.gmail.com 587
   ```

### Webhook Not Firing

**Symptoms:**
- No POST received by webhook endpoint
- Log shows: `Failed to post webhook: ...`

**Diagnosis:**
```python
# Test webhook
python -c "
from check_events import *
test_event = {
    'id': 'test',
    'title': 'Test Event',
    'link': 'https://example.com',
    'date': '2025-12-31',
    'description': 'Test description'
}
post_to_webhook(test_event)
"
```

**Solutions:**

1. **Check webhook URL**
   ```bash
   # Verify URL is correct and accessible
   curl -X POST -H "Content-Type: application/json" \
        -d '{"test": "data"}' \
        "$WEBHOOK_URL"
   ```

2. **Check webhook service**
   - Zapier: Verify zap is on
   - Make: Check scenario is active
   - Test webhook URL in service dashboard

3. **Check payload format**
   - Some services expect specific JSON structure
   - Modify `post_to_webhook()` function if needed

### Teams Notification Not Working

**Symptoms:**
- No message in Teams channel
- Log shows: `Failed to send Teams notification: ...`

**Diagnosis:**
```python
# Test Teams webhook
python -c "
from check_events import *
test_event = {
    'id': 'test',
    'title': 'Test Event',
    'link': 'https://example.com',
    'date': '2025-12-31',
    'description': 'Test description'
}
send_teams_notification(test_event)
"
```

**Solutions:**

1. **Regenerate webhook URL**
   - Teams channel → ⋯ → Connectors
   - Remove old webhook
   - Create new webhook
   - Update `TEAMS_WEBHOOK_URL`

2. **Check message card format**
   - Teams expects specific JSON structure
   - Verify payload matches [MessageCard schema](https://docs.microsoft.com/en-us/outlook/actionable-messages/message-card-reference)

3. **Test with simple payload**
   ```bash
   curl -H "Content-Type: application/json" \
        -d '{"text":"Hello from EUGLOH Scraper"}' \
        "$TEAMS_WEBHOOK_URL"
   ```

---

## Feed Issues

### Feed Not Updating

**Symptoms:**
- `feed.xml` timestamp is old
- New events not appearing in RSS reader

**Diagnosis:**
```bash
# Check last modification
ls -l feed.xml docs/feed.xml

# Check feed content
head -20 feed.xml | grep lastBuildDate
```

**Solutions:**

1. **Scraper not running**
   - Check cron job: `crontab -l`
   - Check GitHub Actions workflow status
   - Run manually: `python check_events.py`

2. **Feed file permissions**
   ```bash
   chmod 644 feed.xml
   chmod 644 docs/feed.xml
   ```

3. **No new events**
   - This is normal - feed updates only when new events found
   - Check `seen.json` for previously seen events

### Invalid RSS Feed

**Symptoms:**
- RSS reader shows error
- Feed validation fails

**Diagnosis:**
```bash
# Validate feed structure
python -c "
import xml.etree.ElementTree as ET
try:
    ET.parse('feed.xml')
    print('Feed is valid XML')
except Exception as e:
    print(f'Feed is invalid: {e}')
"

# Check online validator
# Upload feed.xml to https://validator.w3.org/feed/
```

**Solutions:**

1. **Corrupted feed**
   ```bash
   # Backup and regenerate
   cp feed.xml feed.xml.backup
   rm feed.xml
   python check_events.py
   ```

2. **Special characters not escaped**
   - Check for unescaped `<`, `>`, `&` in event data
   - Report issue if found (should be auto-escaped)

### Feed Shows Duplicate Items

**Symptoms:**
- Same event appears multiple times in feed

**Diagnosis:**
```bash
# Check for duplicates
grep -o '<guid[^>]*>[^<]*</guid>' feed.xml | sort | uniq -d
```

**Solutions:**

1. **Clear state and rebuild**
   ```bash
   # Backup first
   cp seen.json seen.json.backup
   cp feed.xml feed.xml.backup
   
   # Clear state
   echo '{"seen_ids": [], "last_checked": null}' > seen.json
   
   # Rebuild from feed
   python check_events.py --rebuild-history
   ```

2. **URL normalization issue**
   - Event URLs have different query parameters
   - Function should strip them, but check:
     ```python
     from check_events import normalize_url
     print(normalize_url("https://example.com/event?ref=1"))
     print(normalize_url("https://example.com/event?ref=2"))
     # Should be identical
     ```

---

## GitHub Actions Issues

### Workflow Not Running

**Symptoms:**
- No automatic runs happening
- Schedule not triggering

**Solutions:**

1. **Actions disabled**
   - Check Settings → Actions → General
   - Ensure Actions are enabled

2. **Repository inactive**
   - GitHub disables Actions after 60 days of no activity
   - Push a commit to re-enable

3. **Workflow syntax error**
   ```bash
   # Validate workflow locally
   yamllint .github/workflows/scrape-and-publish.yml
   ```

4. **Schedule timing**
   - Cron in GitHub Actions uses UTC
   - Convert your timezone to UTC
   - May have up to 15-minute delay

### Workflow Fails

**Symptoms:**
- Red X on workflow run
- Error in Actions tab

**Diagnosis:**
- Go to Actions tab
- Click failed workflow run
- Check logs for error messages

**Common Errors & Solutions:**

1. **`pip install failed`**
   ```yaml
   # Update workflow to specify Python version
   - name: Set up Python
     uses: actions/setup-python@v4
     with:
       python-version: "3.11"
   ```

2. **`Permission denied` on git push**
   - Check workflow has write permissions:
     ```yaml
     permissions:
       contents: write
     ```

3. **Secrets not available**
   - Verify secrets are set in repository settings
   - Check secret names match workflow file

4. **Out of disk space**
   - Cleanup old artifacts
   - Reduce state file sizes

### GitHub Pages Not Updating

**Symptoms:**
- Feed URL returns 404
- Pages shows old content

**Solutions:**

1. **Pages not enabled**
   - Settings → Pages
   - Source: `main` branch, `/docs` folder
   - Save changes

2. **Workflow not committing files**
   ```bash
   # Check workflow commits to docs/
   git log --oneline -- docs/feed.xml
   ```

3. **Pages build failed**
   - Check Pages deployments in Actions tab
   - Look for build errors

4. **Cache issue**
   - Clear browser cache
   - Try incognito/private browsing
   - Wait a few minutes for CDN refresh

---

## Statistics Issues

### Statistics Not Generating

**Symptoms:**
- `stats.json` or `stats.html` not created/updated
- Missing statistics dashboard

**Diagnosis:**
```bash
# Check if files exist
ls -l docs/stats.json docs/stats.html

# Run manually and check for errors
python check_events.py 2>&1 | grep -i stats
```

**Solutions:**

1. **Directory doesn't exist**
   ```bash
   mkdir -p docs
   ```

2. **Permission issues**
   ```bash
   chmod 755 docs
   chmod 644 docs/stats.*
   ```

3. **Corrupted history file**
   ```bash
   # Rebuild history
   python check_events.py --rebuild-history
   ```

### Incorrect Statistics

**Symptoms:**
- Wrong counts or calculations
- Missing data in dashboard

**Diagnosis:**
```python
# Check history data
import json
with open('history.json') as f:
    history = json.load(f)
print(f"Events in history: {len(history['events'])}")

# Check for data issues
for event_id, event in history['events'].items():
    if not event.get('first_seen'):
        print(f"Missing first_seen: {event_id}")
```

**Solutions:**

1. **Rebuild history from feed**
   ```bash
   python check_events.py --rebuild-history
   ```

2. **Clear and restart**
   ```bash
   # Backup first
   cp history.json history.json.backup
   cp seen.json seen.json.backup
   
   # Fresh start
   rm history.json seen.json
   python check_events.py
   ```

### Charts Not Displaying

**Symptoms:**
- Statistics page loads but charts are blank
- JavaScript errors in browser console

**Solutions:**

1. **Chart.js not loading**
   - Check internet connection (CDN required)
   - Open browser console (F12) for errors

2. **No data for charts**
   - Charts require historical data
   - Wait for multiple scraper runs to accumulate data

3. **Browser compatibility**
   - Use modern browser (Chrome, Firefox, Edge)
   - Update browser to latest version

---

## Performance Issues

### Slow Execution

**Symptoms:**
- Scraper takes > 30 seconds to complete

**Diagnosis:**
```bash
# Time the execution
time python check_events.py
```

**Solutions:**

1. **Network latency**
   ```bash
   # Increase timeout if needed
   REQUEST_TIMEOUT="20"
   ```

2. **Large state files**
   ```bash
   # Check file sizes
   ls -lh seen.json history.json feed.xml
   
   # Archive old events if > 10MB
   ```

3. **Slow statistics generation**
   - Normal for > 1000 events
   - Consider optimizing if critical

### High Memory Usage

**Symptoms:**
- Process killed by OOM
- System slowdown during execution

**Solutions:**

1. **Large feed file**
   ```bash
   # Check feed size
   ls -lh feed.xml
   
   # Consider truncating old items
   # Keep last N items only
   ```

2. **Processing many events**
   - Normal for large datasets
   - Optimize selectors to reduce candidates

---

## Data Issues

### Lost State File

**Symptoms:**
- `seen.json` deleted or corrupted
- All events treated as new

**Solution:**
```bash
# If you have feed.xml, rebuild
python check_events.py --rebuild-history

# Otherwise, start fresh
echo '{"seen_ids": [], "last_checked": null}' > seen.json
```

### Corrupted JSON Files

**Symptoms:**
- `JSONDecodeError` when running scraper

**Diagnosis:**
```bash
# Validate JSON files
python -c "import json; json.load(open('seen.json'))"
python -c "import json; json.load(open('history.json'))"
```

**Solutions:**

1. **Restore from backup**
   ```bash
   cp backups/YYYYMMDD/seen.json .
   cp backups/YYYYMMDD/history.json .
   ```

2. **Rebuild from feed**
   ```bash
   python check_events.py --rebuild-history
   ```

3. **Start fresh** (last resort)
   ```bash
   echo '{"seen_ids": [], "last_checked": null}' > seen.json
   echo '{"events": {}}' > history.json
   ```

### Date Parsing Failures

**Symptoms:**
- Events not marked as expired
- Wrong deadline timestamps

**Diagnosis:**
```python
from check_events import parse_deadline

# Test date parsing
test_dates = [
    "31 Dec 2026 23:59",
    "December 31, 2026",
    "2026-12-31",
]

for date_str in test_dates:
    result = parse_deadline(date_str)
    print(f"{date_str} -> {result}")
```

**Solutions:**

1. **Add new date format**
   - Edit `parse_deadline()` function
   - Add format to `formats` list

2. **Report issue**
   - Provide example date string
   - Open GitHub issue with details

---

## Getting Help

If your issue isn't covered here:

1. **Check existing issues**: https://github.com/chrisilt/euglohscraper/issues
2. **Search discussions**: https://github.com/chrisilt/euglohscraper/discussions
3. **Open new issue** with:
   - Clear description of problem
   - Steps to reproduce
   - Error messages (full output)
   - Environment details (OS, Python version)
   - Configuration (remove sensitive data)

### Debug Mode

Run with verbose output:

```bash
# Python debug mode
python -v check_events.py 2>&1 | tee debug.log

# Enable all warnings
python -Wall check_events.py 2>&1 | tee debug.log
```

### Collect Diagnostic Info

```bash
#!/bin/bash
# diagnostic.sh - Collect system information

echo "=== System Info ==="
uname -a
python --version
pip --version

echo -e "\n=== Python Packages ==="
pip list | grep -E "(requests|beautifulsoup4)"

echo -e "\n=== File Status ==="
ls -lh seen.json history.json feed.xml docs/*.{json,html,xml}

echo -e "\n=== Recent Errors ==="
grep -i error scraper.log 2>/dev/null | tail -20

echo -e "\n=== Configuration ==="
env | grep -E "(TARGET_URL|EMAIL_|TEAMS_|WEBHOOK_)" | sed 's/=.*/=***/'
```

Run and share output (remove sensitive data):
```bash
bash diagnostic.sh > diagnostic.txt
```
