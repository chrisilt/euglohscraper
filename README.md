# EUGLOH Course Watcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A tiny scraper that watches EUGLOH course & event pages and builds a public RSS feed of open registrations. Designed to be simple, robust, and easy to host via GitHub Pages.

## 📑 Table of Contents

- [Live Demo](#-live-demo)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Contributing](#-contributing)
- [License](#-license)

## 🌐 Live Demo

- **RSS Feed**: https://chrisilt.github.io/euglohscraper/feed.xml
- **Web Viewer**: https://chrisilt.github.io/euglohscraper/
- **Statistics Dashboard**: https://chrisilt.github.io/euglohscraper/stats.html

## ✨ Features

- **🔍 Intelligent Scraping** — Robust CSS selectors that adapt to HTML structure changes
- **📡 RSS Feed** — Standard RSS 2.0 format with rich metadata
- **📧 Email Notifications** — SMTP-based alerts for new events
- **💬 Microsoft Teams Integration** — Native Teams webhook support
- **🔗 Generic Webhooks** — Connect to Zapier, Make, n8n, and more
- **⏰ Expired Event Handling** — Automatic deadline tracking and marking
- **📊 Statistics Dashboard** — Interactive analytics with Chart.js visualizations
- **📈 Historical Tracking** — Complete event lifecycle from discovery to expiration
- **🔄 Deduplication** — Smart state management to prevent duplicate notifications
- **🚀 GitHub Actions Ready** — Automated execution with zero infrastructure
- **📱 Mobile-Friendly** — Responsive design for all outputs

## 🚀 Quick Start

Get up and running in 2 minutes:

### Installation
```bash
git clone https://github.com/chrisilt/euglohscraper.git
cd euglohscraper
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
### Running the Scraper

```bash
python check_events.py
```

### Output Files

The scraper creates several files:

- **`seen.json`** — Internal state for deduplication
- **`feed.xml`** — RSS feed with newly discovered events
- **`history.json`** — Complete event lifecycle tracking
- **`docs/stats.json`** — Event statistics in JSON format
- **`docs/stats.html`** — Interactive analytics dashboard

## 📚 Documentation

Comprehensive documentation is available:

- **[Architecture Guide](docs/ARCHITECTURE.md)** — System design and components
- **[API Documentation](docs/API.md)** — Function reference and usage
- **[Deployment Guide](docs/DEPLOYMENT.md)** — Setup instructions for various platforms
- **[Development Guide](docs/DEVELOPMENT.md)** — Contributing and extending the project
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** — Common issues and solutions
- **[Contributing Guidelines](CONTRIBUTING.md)** — How to contribute
- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Community standards

## Configuration

## ⚙️ Configuration

All configuration is done via environment variables. You can set them directly in your shell, or create a `.env` file.

### Quick Setup

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your preferred settings
nano .env
```

### Key Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `TARGET_URL` | URL to scrape | EUGLOH registrations page |
| `EMAIL_ENABLED` | Enable email notifications | `false` |
| `EMAIL_FROM` | Sender email address | — |
| `EMAIL_TO` | Recipient email(s) | — |
| `EMAIL_SMTP_HOST` | SMTP server | — |
| `TEAMS_WEBHOOK_URL` | Teams webhook URL | — |
| `WEBHOOK_URL` | Generic webhook URL | — |
| `EXPIRED_DAYS_BUFFER` | Grace period after deadline | `0` |

See [`.env.example`](.env.example) for complete configuration options.

## 📊 Statistics Dashboard

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

## ⚙️ Configuration

All configuration is done via environment variables. You can set them directly in your shell, or create a `.env` file.

### Quick Setup

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your preferred settings
nano .env
```

### Key Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `TARGET_URL` | URL to scrape | EUGLOH registrations page |
| `EMAIL_ENABLED` | Enable email notifications | `false` |
| `EMAIL_FROM` | Sender email address | — |
| `EMAIL_TO` | Recipient email(s) | — |
| `EMAIL_SMTP_HOST` | SMTP server | — |
| `TEAMS_WEBHOOK_URL` | Teams webhook URL | — |
| `WEBHOOK_URL` | Generic webhook URL | — |
| `EXPIRED_DAYS_BUFFER` | Grace period after deadline | `0` |

See [`.env.example`](.env.example) for complete configuration options.

## 🚢 Deployment

### GitHub Actions (Recommended)

Automated execution with GitHub Actions:

1. **Fork the repository**
2. **Enable GitHub Pages**: Settings → Pages → Source: `main` branch, `/docs` folder
3. **Configure secrets** (optional): Settings → Secrets → Actions
4. **Workflow runs automatically** daily at 6 AM UTC

Your feed will be available at: `https://YOUR-USERNAME.github.io/euglohscraper/feed.xml`

### Other Deployment Options

- **Local/Cron**: Run on your own machine or server
- **Docker**: Containerized deployment
- **Cloud Functions**: Serverless execution

See the [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

## 📊 Event Lifecycle

The scraper tracks complete event lifecycles:

1. **Discovery** — Event first appears with open registration
2. **Active** — Event remains available for registration
3. **Expiration** — Deadline passes (with optional grace period)
4. **Tracking** — Duration and statistics recorded

Events are marked with categories in the RSS feed:
- `<category>new</category>` — Added in last 7 days
- `<category>expired</category>` — Past deadline

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_check_events.py
```

Tests cover:
- URL normalization
- Event extraction
- Deduplication logic
- Feed generation
- Date parsing
- Expired event handling
- Statistics calculation
- Notification delivery

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python test_check_events.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

See the [Development Guide](docs/DEVELOPMENT.md) for detailed setup instructions.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the [EUGLOH](https://www.eugloh.eu/) (European University Alliance for Global Health) community
- Powered by [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- Uses [Chart.js](https://www.chartjs.org/) for statistics visualizations

## 📞 Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/chrisilt/euglohscraper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/chrisilt/euglohscraper/discussions)

## 🔗 Related Projects

Looking for similar tools:
- [RSS Bridge](https://github.com/RSS-Bridge/rss-bridge) - RSS feed generator for various sites
- [Huginn](https://github.com/huginn/huginn) - Multi-site monitoring and automation

---

Made with ❤️ for the EUGLOH community