# Contributing to EUGLOH Course Watcher

Thank you for your interest in contributing to the EUGLOH Course Watcher! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear descriptive title**
- **Steps to reproduce** the behavior
- **Expected behavior** vs. actual behavior
- **Screenshots** if applicable
- **Environment details** (OS, Python version, etc.)
- **Additional context** like error messages or logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear descriptive title**
- **Detailed description** of the proposed functionality
- **Use case** explaining why this enhancement would be useful
- **Possible implementation** if you have ideas

### Pull Requests

We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs or functionality, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing style
6. Issue the pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- pip

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/chrisilt/euglohscraper.git
   cd euglohscraper
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up configuration**
   ```bash
   cp .env .env.local  # Create your local config
   # Edit .env.local with your settings
   ```

5. **Run tests**
   ```bash
   python test_check_events.py
   ```

6. **Run the scraper locally**
   ```bash
   python check_events.py
   ```

## Pull Request Process

1. **Update documentation** - Update the README.md and any relevant documentation with details of changes
2. **Add tests** - Add or update tests to cover your changes
3. **Run tests** - Ensure all tests pass: `python test_check_events.py`
4. **Update changelog** - Add a note about your changes in the PR description
5. **Code review** - Wait for maintainers to review your PR
6. **Address feedback** - Make requested changes if needed
7. **Merge** - A maintainer will merge your PR once approved

### PR Title Convention

Use clear, descriptive titles:
- `feat: Add support for filtering events by category`
- `fix: Correct date parsing for European format`
- `docs: Update installation instructions`
- `test: Add tests for email notification`
- `refactor: Simplify event extraction logic`

## Coding Standards

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use meaningful variable and function names
- Keep functions focused and small
- Add docstrings to functions and classes
- Maximum line length: 100 characters (reasonable exceptions allowed)

### Code Organization

```python
#!/usr/bin/env python3
"""
Module docstring explaining the purpose.
"""

# Standard library imports
import os
import json

# Third-party imports
import requests
from bs4 import BeautifulSoup

# Local imports (if any)
from my_module import my_function

# Constants (UPPER_CASE)
MAX_RETRIES = 3

# Functions with docstrings
def my_function(arg1: str, arg2: int) -> dict:
    """
    Brief description of what the function does.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When input is invalid
    """
    pass
```

### Commit Messages

Write clear, concise commit messages:

```
Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain what and why vs. how.

- Bullet points are okay
- Use present tense ("Add feature" not "Added feature")
- Reference issues and PRs where applicable

Fixes #123
```

## Testing

### Running Tests

```bash
# Run all tests
python test_check_events.py

# Run specific test class
python test_check_events.py TestEventExtraction

# Run with verbose output
python test_check_events.py -v
```

### Writing Tests

- Use `unittest` framework
- Place tests in `test_check_events.py`
- Name test methods descriptively: `test_<what_is_being_tested>`
- Use setup and teardown methods for common initialization
- Mock external dependencies (HTTP requests, file I/O)
- Test both success and failure cases
- Test edge cases

Example:

```python
class TestMyFeature(unittest.TestCase):
    """Test my new feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {"key": "value"}
    
    def test_feature_success(self):
        """Test that feature works correctly."""
        result = my_feature(self.test_data)
        self.assertEqual(result, expected_value)
    
    def test_feature_handles_error(self):
        """Test that feature handles errors gracefully."""
        with self.assertRaises(ValueError):
            my_feature(invalid_data)
```

### Test Coverage

Aim for high test coverage for new code:
- Core functionality: 90%+ coverage
- Edge cases and error handling: covered
- Configuration parsing: covered
- Data transformations: covered

## Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google or NumPy docstring format
- Include examples for complex functions
- Document exceptions that may be raised
- Update docstrings when code changes

### User Documentation

When changing functionality:
1. Update README.md if user-facing
2. Update relevant docs in `docs/` folder
3. Add examples if helpful
4. Update configuration documentation

### API Documentation

If adding new functions to the public API:
1. Document in `docs/API.md`
2. Include function signature
3. Describe parameters and return values
4. Provide usage examples

## Questions?

Feel free to:
- Open an issue for questions
- Start a discussion in GitHub Discussions
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
