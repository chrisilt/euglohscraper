# Deployment Guide

This guide covers different deployment options for the EUGLOH Course Watcher.

## Table of Contents

- [Deployment Options](#deployment-options)
- [GitHub Actions Deployment (Recommended)](#github-actions-deployment-recommended)
- [Local Development Deployment](#local-development-deployment)
- [Server/VPS Deployment](#servervps-deployment)
- [Docker Deployment](#docker-deployment)
- [Configuration Management](#configuration-management)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Deployment Options

| Option | Best For | Pros | Cons |
|--------|----------|------|------|
| **GitHub Actions** | Public projects, automated workflows | Free, automated, built-in GitHub Pages | Requires public repo, limited execution time |
| **Local** | Development, testing | Easy setup, immediate feedback | Manual execution, local only |
| **Server/Cron** | Self-hosted, private deployments | Full control, private | Server maintenance, costs |
| **Docker** | Containerized environments | Portable, reproducible | Additional complexity |

---

## GitHub Actions Deployment (Recommended)

### Overview

GitHub Actions provides free automated execution and integrates seamlessly with GitHub Pages for hosting the RSS feed and statistics dashboard.

### Prerequisites

- GitHub account
- Repository with Actions enabled
- GitHub Pages enabled (for public feed hosting)

### Step 1: Repository Setup

1. **Fork or clone** the repository:
   ```bash
   git clone https://github.com/chrisilt/euglohscraper.git
   cd euglohscraper
   ```

2. **Push to your GitHub repository**:
   ```bash
   git remote set-url origin https://github.com/YOUR-USERNAME/euglohscraper.git
   git push -u origin main
   ```

### Step 2: Configure Secrets

Add secrets in GitHub repository settings:

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add the following secrets (as needed):

#### Required Secrets

None - the scraper works with default configuration.

#### Optional Secrets (for notifications)

**Email Notifications:**
- `EMAIL_ENABLED` = `true`
- `EMAIL_FROM` = Your sender email
- `EMAIL_TO` = Recipient email(s)
- `EMAIL_SMTP_HOST` = SMTP server (e.g., `smtp.gmail.com`)
- `EMAIL_SMTP_PORT` = `587` (or your SMTP port)
- `EMAIL_SMTP_USER` = SMTP username
- `EMAIL_SMTP_PASSWORD` = SMTP password/app password

**Teams Notifications:**
- `TEAMS_WEBHOOK_URL` = Your Teams incoming webhook URL

**Generic Webhook:**
- `WEBHOOK_URL` = Your webhook URL (Zapier, Make, etc.)

### Step 3: Enable GitHub Pages

1. Go to **Settings → Pages**
2. Under **Source**, select:
   - **Branch**: `main`
   - **Folder**: `/docs`
3. Click **Save**
4. Your feed will be available at: `https://YOUR-USERNAME.github.io/euglohscraper/feed.xml`

### Step 4: Workflow Configuration

The workflow file (`.github/workflows/scrape-and-publish.yml`) is pre-configured but can be customized:

**Default Schedule**:
```yaml
on:
  schedule:
    - cron: "0 6 * * *"  # Daily at 6 AM UTC
  workflow_dispatch: {}   # Manual trigger
```

**To change schedule**, edit the cron expression:
- `"0 */6 * * *"` - Every 6 hours
- `"0 8,16 * * *"` - Twice daily at 8 AM and 4 PM UTC
- `"0 * * * *"` - Every hour

**Cron expression format**: `minute hour day month weekday`

### Step 5: Test Deployment

1. **Manual trigger**:
   - Go to **Actions** tab
   - Select **Scrape EUGLOH and Publish Feed**
   - Click **Run workflow**
   - Select branch and click **Run workflow**

2. **Check results**:
   - Wait for workflow to complete
   - Check **Actions** tab for logs
   - Visit `https://YOUR-USERNAME.github.io/euglohscraper/` to view feed
   - Visit `https://YOUR-USERNAME.github.io/euglohscraper/stats.html` for statistics

### Step 6: Verify Outputs

After successful run, these files should be updated:
- `seen.json` - State file
- `feed.xml` - Root feed file
- `history.json` - Historical tracking
- `docs/feed.xml` - Published feed (GitHub Pages)
- `docs/stats.json` - Statistics data
- `docs/stats.html` - Statistics dashboard

### Troubleshooting GitHub Actions

**Workflow doesn't run:**
- Check that Actions are enabled (Settings → Actions)
- Verify cron schedule is correct
- Check for repository activity (Actions may be disabled after 60 days of inactivity)

**Feed not updating on GitHub Pages:**
- Verify Pages is enabled and pointing to `/docs` folder
- Check that workflow is committing files
- Wait 1-2 minutes for Pages to rebuild

**Secrets not working:**
- Verify secret names match exactly (case-sensitive)
- Check workflow file references secrets correctly: `${{ secrets.SECRET_NAME }}`

---

## Local Development Deployment

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (optional, for version control)

### Step 1: Clone Repository

```bash
git clone https://github.com/chrisilt/euglohscraper.git
cd euglohscraper
```

### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

1. **Copy example configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your settings:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Configure as needed** (email, webhooks, etc.)

### Step 5: Run Scraper

```bash
python check_events.py
```

**Expected output:**
```
Found 15 candidate events via selector: ...
New: https://example.com/event1 | title: Event Title | date: 2025-12-31
Posted event https://example.com/event1 -> 200
Email sent for event: https://example.com/event1
Wrote feed to ./feed.xml
Statistics saved to ./docs/stats.json and ./docs/stats.html
Saved state: 15 seen ids
```

### Step 6: View Results

- **RSS Feed**: Open `feed.xml` in a browser or RSS reader
- **Statistics**: Open `docs/stats.html` in a browser
- **Raw Data**: Check `seen.json` and `history.json`

### Step 7: Schedule Local Execution (Optional)

**Linux/macOS (cron):**
```bash
# Edit crontab
crontab -e

# Add line (runs daily at 6 AM):
0 6 * * * cd /path/to/euglohscraper && /path/to/.venv/bin/python check_events.py
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 6 AM
4. Action: Start a program
5. Program: `C:\path\to\.venv\Scripts\python.exe`
6. Arguments: `check_events.py`
7. Start in: `C:\path\to\euglohscraper`

---

## Server/VPS Deployment

### Prerequisites

- Linux server (Ubuntu, Debian, CentOS, etc.)
- SSH access
- Python 3.8+
- sudo privileges (for system-wide setup)

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y
```

### Step 2: Create User (Optional but recommended)

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash eugloh-scraper
sudo su - eugloh-scraper
```

### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/chrisilt/euglohscraper.git
cd euglohscraper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy and edit configuration
cp .env.example .env
nano .env
```

### Step 5: Test Execution

```bash
python check_events.py
```

### Step 6: Setup Cron Job

```bash
# Edit crontab
crontab -e

# Add entry (daily at 6 AM)
0 6 * * * cd /home/eugloh-scraper/euglohscraper && /home/eugloh-scraper/euglohscraper/.venv/bin/python check_events.py >> /home/eugloh-scraper/euglohscraper/scraper.log 2>&1
```

### Step 7: Web Server Setup (Optional)

To serve the RSS feed and statistics publicly:

**Option A: Nginx**

```bash
# Install Nginx
sudo apt install nginx -y

# Create site configuration
sudo nano /etc/nginx/sites-available/eugloh-scraper

# Add configuration:
server {
    listen 80;
    server_name your-domain.com;
    
    root /home/eugloh-scraper/euglohscraper/docs;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    location /feed.xml {
        default_type application/rss+xml;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/eugloh-scraper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Option B: Apache**

```bash
# Install Apache
sudo apt install apache2 -y

# Create site configuration
sudo nano /etc/apache2/sites-available/eugloh-scraper.conf

# Add configuration:
<VirtualHost *:80>
    ServerName your-domain.com
    DocumentRoot /home/eugloh-scraper/euglohscraper/docs
    
    <Directory /home/eugloh-scraper/euglohscraper/docs>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>
</VirtualHost>

# Enable site
sudo a2ensite eugloh-scraper
sudo systemctl restart apache2
```

### Step 8: Setup SSL (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate (Nginx)
sudo certbot --nginx -d your-domain.com

# Obtain certificate (Apache)
sudo certbot --apache -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY check_events.py .
COPY .env.example .env

# Create output directories
RUN mkdir -p docs

# Run scraper
CMD ["python", "check_events.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  scraper:
    build: .
    env_file: .env
    volumes:
      - ./seen.json:/app/seen.json
      - ./history.json:/app/history.json
      - ./feed.xml:/app/feed.xml
      - ./docs:/app/docs
    restart: unless-stopped
```

### Deployment Steps

```bash
# Build image
docker build -t eugloh-scraper .

# Run once
docker run --rm -v $(pwd):/app eugloh-scraper

# Run with compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Scheduled Execution with Docker

Use a cron job to run the container:

```bash
# Add to crontab
0 6 * * * docker run --rm -v /path/to/euglohscraper:/app eugloh-scraper >> /path/to/scraper.log 2>&1
```

---

## Configuration Management

### Environment Variables Priority

1. GitHub Actions secrets (CI/CD)
2. `.env` file (local/server)
3. System environment variables
4. Default values in code

### Best Practices

**Security:**
- Never commit `.env` file (in `.gitignore`)
- Use GitHub Secrets for sensitive data
- Rotate credentials regularly
- Use app passwords instead of account passwords

**Reliability:**
- Test configuration locally before deploying
- Monitor logs for errors
- Set up alerts for failures
- Keep backup of state files

**Performance:**
- Adjust `REQUEST_TIMEOUT` based on network
- Use appropriate cron schedule
- Monitor execution time

---

## Monitoring and Maintenance

### Log Monitoring

**GitHub Actions:**
- Check Actions tab for workflow status
- Review logs for errors
- Set up email notifications for failures

**Local/Server:**
```bash
# View recent logs
tail -f scraper.log

# Search for errors
grep -i error scraper.log

# Count successful runs
grep "Saved state" scraper.log | wc -l
```

### Health Checks

Create a monitoring script:

```bash
#!/bin/bash
# check-scraper-health.sh

# Check if feed was updated in last 25 hours
if [ $(find feed.xml -mmin -1500 2>/dev/null | wc -l) -eq 0 ]; then
    echo "WARNING: Feed not updated in 25 hours"
    # Send alert
fi

# Check for errors in recent logs
if grep -q "ERROR" scraper.log 2>/dev/null; then
    echo "ERROR: Found errors in logs"
    # Send alert
fi

echo "Health check passed"
```

### Maintenance Tasks

**Weekly:**
- Review logs for errors
- Check feed is updating
- Verify notifications are working

**Monthly:**
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Review and clean up old events in `history.json` (optional)
- Check disk space usage

**Quarterly:**
- Review EUGLOH website for changes
- Update selectors if needed
- Test all notification channels
- Review and update documentation

### Backup Strategy

```bash
# Create backup script
#!/bin/bash
# backup.sh

BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

cp seen.json "$BACKUP_DIR/"
cp history.json "$BACKUP_DIR/"
cp feed.xml "$BACKUP_DIR/"
cp -r docs/ "$BACKUP_DIR/"

echo "Backup created: $BACKUP_DIR"
```

Run weekly via cron:
```bash
0 0 * * 0 cd /path/to/euglohscraper && ./backup.sh
```

### Recovery Procedures

**Lost state file (`seen.json`):**
```bash
# Rebuild from history
python check_events.py --rebuild-history
```

**Corrupted history:**
```bash
# Restore from backup
cp backups/YYYYMMDD/history.json .
```

**Feed issues:**
```bash
# Regenerate from history
rm feed.xml
python check_events.py --rebuild-history
```

---

## Performance Tuning

### Reduce Execution Time

- Increase `REQUEST_TIMEOUT` only if needed
- Optimize selectors for faster parsing
- Consider caching if running very frequently

### Reduce Resource Usage

- Clean up old events from history periodically
- Limit feed to recent N items
- Archive old statistics

### Scale Up

For multiple sites or high frequency:
- Use queuing system (Celery, Redis)
- Implement parallel processing
- Consider database instead of JSON files

---

## Security Considerations

### Secrets Management

- Use environment variables, not hardcoded values
- Rotate credentials regularly
- Use minimal permissions for SMTP/API accounts

### Network Security

- Use HTTPS for all webhook URLs
- Validate webhook responses
- Implement rate limiting if exposing API

### Access Control

- Restrict server access via firewall
- Use SSH keys instead of passwords
- Regular security updates

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.

### Quick Checks

**Scraper not finding events:**
```bash
# Test selectors
python -c "from check_events import *; print(fetch_page(TARGET_URL)[:500])"
```

**Notifications not working:**
```bash
# Test email
python -c "from check_events import *; send_email_notification({'title': 'Test', 'link': 'http://test', 'date': '2025-01-01', 'description': 'Test'})"
```

**Feed not updating:**
```bash
# Check file permissions
ls -l feed.xml docs/feed.xml

# Check last modification
stat feed.xml
```

---

## Support

- **Issues**: https://github.com/chrisilt/euglohscraper/issues
- **Discussions**: https://github.com/chrisilt/euglohscraper/discussions
- **Documentation**: https://github.com/chrisilt/euglohscraper/blob/main/README.md
