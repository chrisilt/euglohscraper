# Development Guide

Guide for developers who want to contribute to or extend the EUGLOH Course Watcher.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Code Style Guide](#code-style-guide)
- [Testing](#testing)
- [Adding New Features](#adding-new-features)
- [Debugging](#debugging)
- [Release Process](#release-process)

---

## Getting Started

### Prerequisites

- **Python 3.8+** (3.11 recommended)
- **Git** for version control
- **pip** package manager
- **Virtual environment** tool
- Text editor or IDE (VSCode, PyCharm, etc.)

### Quick Start

```bash
# Clone repository
git clone https://github.com/chrisilt/euglohscraper.git
cd euglohscraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
python test_check_events.py

# Run scraper
python check_events.py
```

---

## Development Environment Setup

### Virtual Environment

Always use a virtual environment for development:

```bash
# Create
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Deactivate
deactivate
```

### IDE Setup

#### VSCode

Recommended extensions:
- Python (Microsoft)
- Pylance
- Python Test Explorer

Workspace settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "autopep8",
    "python.testing.unittestEnabled": true,
    "python.testing.unittestArgs": [
        "-v",
        "-s",
        ".",
        "-p",
        "test*.py"
    ]
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select `.venv/bin/python`
4. Enable pytest for testing

### Git Configuration

```bash
# Configure Git
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Create feature branch
git checkout -b feature/your-feature-name
```

---

## Project Structure

```
euglohscraper/
├── .github/
│   └── workflows/
│       └── scrape-and-publish.yml    # GitHub Actions workflow
├── docs/
│   ├── ARCHITECTURE.md               # Architecture documentation
│   ├── API.md                        # API documentation
│   ├── DEPLOYMENT.md                 # Deployment guide
│   ├── TROUBLESHOOTING.md            # Troubleshooting guide
│   ├── feed.xml                      # Published RSS feed
│   ├── stats.json                    # Statistics data
│   ├── stats.html                    # Statistics dashboard
│   ├── index.html                    # Feed viewer
│   └── style.css                     # Styling
├── .env.example                      # Configuration template
├── .gitignore                        # Git ignore rules
├── check_events.py                   # Main application
├── CODE_OF_CONDUCT.md                # Code of conduct
├── CONTRIBUTING.md                   # Contribution guidelines
├── feed.xml                          # Local RSS feed
├── history.json                      # Event history
├── LICENSE                           # MIT License
├── README.md                         # Main documentation
├── requirements.txt                  # Python dependencies
├── seen.json                         # Deduplication state
└── test_check_events.py              # Unit tests
```

### Key Files

- **check_events.py**: Main application containing all logic
- **test_check_events.py**: Comprehensive test suite
- **seen.json**: Tracks seen events (deduplication)
- **history.json**: Full event lifecycle tracking
- **feed.xml**: RSS feed output
- **docs/stats.{json,html}**: Statistics outputs

---

## Code Style Guide

### General Principles

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Write clear, self-documenting code
- Add comments for complex logic
- Keep functions focused and small
- Use type hints where helpful

### Naming Conventions

```python
# Constants (uppercase with underscores)
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 15

# Functions and variables (lowercase with underscores)
def fetch_page(url: str) -> str:
    pass

# Private functions (leading underscore)
def _find_in_ancestors(el: Tag) -> Optional[Tag]:
    pass

# Classes (PascalCase)
class EventExtractor:
    pass
```

### Documentation

Add docstrings to all public functions:

```python
def parse_deadline(date_str: str) -> Optional[float]:
    """
    Parse a deadline date string and return Unix timestamp.
    
    Handles multiple date formats commonly found in EUGLOH events.
    Returns None if parsing fails.
    
    Args:
        date_str: Date string to parse (e.g., "31 Dec 2026 23:59")
    
    Returns:
        Unix timestamp as float, or None if parsing fails
    
    Examples:
        >>> parse_deadline("31 Dec 2026 23:59")
        1798761540.0
        >>> parse_deadline("invalid")
        None
    """
    pass
```

### Error Handling

```python
# Bad: Silent failure
def fetch_page(url):
    try:
        return requests.get(url).text
    except:
        return None

# Good: Explicit error handling
def fetch_page(url: str) -> str:
    """Fetch HTML content from URL."""
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.HTTPError as e:
        print(f"HTTP error fetching {url}: {e}")
        raise
    except requests.Timeout:
        print(f"Timeout fetching {url}")
        raise
```

### Code Formatting

```bash
# Install formatter
pip install autopep8

# Format code
autopep8 --in-place --aggressive check_events.py

# Or use black
pip install black
black check_events.py
```

---

## Testing

### Running Tests

```bash
# Run all tests
python test_check_events.py

# Run with verbose output
python test_check_events.py -v

# Run specific test class
python test_check_events.py TestEventExtraction

# Run specific test method
python test_check_events.py TestEventExtraction.test_extract_event_basic
```

### Writing Tests

Follow this pattern:

```python
import unittest
from check_events import your_function

class TestYourFeature(unittest.TestCase):
    """Test your new feature."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        self.test_data = {"key": "value"}
    
    def tearDown(self):
        """Clean up after each test."""
        pass
    
    def test_feature_success_case(self):
        """Test that feature works correctly."""
        result = your_function(self.test_data)
        self.assertEqual(result, expected_value)
    
    def test_feature_error_handling(self):
        """Test that feature handles errors."""
        with self.assertRaises(ValueError):
            your_function(invalid_data)
    
    def test_feature_edge_case(self):
        """Test edge case."""
        result = your_function(edge_case_data)
        self.assertIsNotNone(result)
```

### Test Coverage

Aim to test:
- ✓ Happy path (normal operation)
- ✓ Error conditions
- ✓ Edge cases (empty input, None, etc.)
- ✓ Integration points

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

class TestScraping(unittest.TestCase):
    
    @patch('check_events.requests.get')
    def test_fetch_page(self, mock_get):
        """Test page fetching with mocked HTTP."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_get.return_value = mock_response
        
        # Test
        result = fetch_page("https://example.com")
        
        # Assert
        self.assertEqual(result, "<html>Test</html>")
        mock_get.assert_called_once()
```

---

## Adding New Features

### 1. Plan Your Feature

- Document the feature in an issue
- Discuss design with maintainers
- Break down into small tasks

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Implement Feature

Follow this workflow:

1. **Write test first** (TDD approach)
   ```python
   def test_new_feature(self):
       """Test new feature works."""
       result = new_feature(input_data)
       self.assertEqual(result, expected)
   ```

2. **Implement minimal code** to pass test
   ```python
   def new_feature(input_data):
       """Implement new feature."""
       # Your implementation
       return result
   ```

3. **Refactor** for clarity and performance

4. **Add documentation**
   - Function docstrings
   - README updates
   - API documentation

### 4. Test Your Changes

```bash
# Run all tests
python test_check_events.py

# Test manually
python check_events.py
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "feat: Add support for event filtering

- Add filter_events() function
- Add EVENT_FILTER configuration
- Add tests for filtering logic
- Update documentation

Closes #123"
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# - Clear title
# - Detailed description
# - Link related issues
```

### Example: Adding Email Filtering

Let's add event category filtering:

**1. Add configuration:**
```python
# In check_events.py
EVENT_CATEGORY_FILTER = os.environ.get("EVENT_CATEGORY_FILTER", "")
```

**2. Add function:**
```python
def filter_events(events: List[Dict], category: str) -> List[Dict]:
    """
    Filter events by category.
    
    Args:
        events: List of events
        category: Category to filter by (case-insensitive)
    
    Returns:
        Filtered list of events
    """
    if not category:
        return events
    
    return [
        ev for ev in events
        if category.lower() in ev.get('description', '').lower()
    ]
```

**3. Add test:**
```python
class TestEventFiltering(unittest.TestCase):
    def test_filter_by_category(self):
        events = [
            {'id': '1', 'description': 'Workshop on Python'},
            {'id': '2', 'description': 'Seminar on Java'},
        ]
        result = filter_events(events, 'Python')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '1')
```

**4. Integrate in main:**
```python
def main():
    # ... existing code ...
    events = find_events(html)
    
    # Apply filter
    if EVENT_CATEGORY_FILTER:
        events = filter_events(events, EVENT_CATEGORY_FILTER)
    
    # ... rest of code ...
```

**5. Document:**
```bash
# Update .env.example
EVENT_CATEGORY_FILTER=""  # Optional: filter events by keyword

# Update README.md
## Configuration
...
- `EVENT_CATEGORY_FILTER` — Optional keyword filter for events
```

---

## Debugging

### Debug Logging

Add debug prints:

```python
# Temporary debugging
print(f"DEBUG: Found {len(events)} events")
print(f"DEBUG: Event data: {events[0]}")

# Better: Use logging (future enhancement)
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Found {len(events)} events")
```

### Interactive Debugging

```bash
# Run with Python debugger
python -m pdb check_events.py

# Common pdb commands:
# n - next line
# s - step into function
# c - continue
# p variable - print variable
# l - list code around current line
# q - quit
```

### Using IDE Debugger

**VSCode:**
1. Set breakpoint (click left of line number)
2. Press F5 to start debugging
3. Use debug toolbar to step through

**PyCharm:**
1. Set breakpoint (click left gutter)
2. Right-click file → Debug 'check_events'
3. Use debug toolbar

### Debug Scraping Issues

```python
# Save HTML for inspection
html = fetch_page(TARGET_URL)
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Test selectors interactively
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
links = soup.select(REG_LINK_SELECTOR)
print(f"Found {len(links)} links")

# Inspect first match
if links:
    print(links[0].prettify())
```

### Debug State Issues

```python
# Inspect state files
import json

with open('seen.json') as f:
    state = json.load(f)
print(f"Seen: {len(state['seen_ids'])} events")

with open('history.json') as f:
    history = json.load(f)
print(f"History: {len(history['events'])} events")

# Check for discrepancies
seen_set = set(state['seen_ids'])
history_set = set(history['events'].keys())
print(f"In seen but not history: {seen_set - history_set}")
print(f"In history but not seen: {history_set - seen_set}")
```

---

## Release Process

### Version Numbering

We use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Creating a Release

1. **Update version** in code/docs
2. **Update CHANGELOG** (create if needed)
3. **Run tests**
4. **Create git tag**
   ```bash
   git tag -a v1.2.0 -m "Version 1.2.0 - Add event filtering"
   git push origin v1.2.0
   ```
5. **Create GitHub release**
   - Go to Releases → Draft a new release
   - Select tag
   - Add release notes
   - Publish

### Pre-release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] No debug code or TODOs
- [ ] Dependencies up to date
- [ ] Examples work
- [ ] README accurate

---

## Best Practices

### Performance

- Use generators for large datasets
- Cache expensive operations
- Minimize file I/O
- Use atomic writes

### Security

- Never commit secrets
- Validate all inputs
- Sanitize outputs (HTML, XML)
- Use parameterized queries (if using DB)

### Maintainability

- Keep functions under 50 lines
- Limit complexity (McCabe < 10)
- Write self-documenting code
- Update documentation with code

### Git Workflow

1. Pull latest changes: `git pull origin main`
2. Create feature branch: `git checkout -b feature/name`
3. Make small, focused commits
4. Push and create PR
5. Address review feedback
6. Squash commits if needed
7. Merge when approved

---

## Resources

### Documentation
- [Python Style Guide (PEP 8)](https://www.python.org/dev/peps/pep-0008/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [BeautifulSoup Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests Docs](https://requests.readthedocs.io/)

### Tools
- [pylint](https://pylint.org/) - Code analysis
- [black](https://black.readthedocs.io/) - Code formatter
- [mypy](http://mypy-lang.org/) - Type checker
- [pytest](https://pytest.org/) - Testing framework (optional)

### Learning
- [Real Python](https://realpython.com/)
- [Python Testing with unittest](https://docs.python.org/3/library/unittest.html)
- [Web Scraping with Python](https://realpython.com/python-web-scraping-practical-introduction/)

---

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/chrisilt/euglohscraper/discussions)
- **Bugs**: Open an [Issue](https://github.com/chrisilt/euglohscraper/issues)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Code Review**: Tag maintainers in PR

Happy coding! 🚀
