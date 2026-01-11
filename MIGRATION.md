# Refactoring Summary

## Overview

The codebase has been completely refactored to follow industry standards and best practices. The new architecture is modular, extensible, and ready for future enhancements (Telegram bot, additional features, etc.).

## Key Improvements

### 1. **Modular Package Structure**

-   Code organized under `src/ynab_parser/` following Python packaging standards
-   Clear separation of concerns with dedicated modules
-   Easier to maintain, test, and extend

### 2. **Core Modules**

```
src/ynab_parser/
├── core/                    # Core functionality
│   ├── api.py              # YNAB API client (refactored)
│   ├── config.py           # Configuration management
│   ├── exceptions.py       # Custom exception hierarchy
│   ├── logging_config.py   # Structured logging
│   └── models.py           # Type-safe data models
├── parsers/                # Bank CSV parsers
│   ├── __init__.py        # Parser interface & factory pattern
│   ├── ocbc.py            # OCBC parser (refactored)
│   └── posb.py            # POSB parser (refactored)
├── converter.py           # CSV → Transaction conversion
├── processor.py           # Pipeline orchestration
├── uploader.py            # YNAB upload handler
├── utils.py               # Type hints and validation
├── cli.py                 # Unified CLI
├── process.py             # Process command
├── upload.py              # Upload command
└── setup.py               # Setup wizard
```

### 3. **New Features**

-   **Structured Logging**: Colored output, file logging, easy to integrate with bots
-   **Type Hints**: Full type annotations for better IDE support and error prevention
-   **Exception Hierarchy**: Organized exception classes for precise error handling
-   **Data Models**: Dataclasses for type safety and validation
-   **Parser Factory**: Extensible pattern for adding new bank parsers
-   **Configuration Management**: Centralized config with environment variable support
-   **Validation**: Input validation and error reporting

### 4. **Better Error Handling**

```python
from ynab_parser.core.exceptions import (
    ConfigurationError,  # Config issues
    ValidationError,     # Data validation
    ParserError,        # CSV parsing
    APIError,           # API errors
    YNABAuthError,      # Auth failed
    YNABRateLimitError, # Rate limit
)
```

### 5. **Unified CLI**

```bash
python -m ynab_parser setup      # guided .env creator
python -m ynab_parser process    # normalize CSVs
python -m ynab_parser upload     # push to YNAB

# Optional entry points when installed in editable mode
pip install -e .
ynab-setup
ynab-process
ynab-upload
```

> Legacy scripts (`process_ynab.py`, `ynab_uploader.py`, `setup_ynab.py`,
> `transactions_parser.py`) were removed in January 2026. Update any
> automation to call the CLI commands above.

### 6. **Enhanced Configuration**

```bash
# Copy template
cp .env.example .env

# Or run setup wizard
python -m ynab_parser setup
```

### 7. **Retry Logic & Rate Limiting**

-   Automatic retries with exponential backoff
-   Smart rate limit handling (429 status)
-   Configurable timeout and max retries

## API Reference

### Configuration

```python
from ynab_parser.core.config import ConfigManager

config = ConfigManager(".env")
token = config.get_api_token()
budget_id = config.get_budget_id()
mapping = config.get_account_mapping()
```

### API Client

```python
from ynab_parser.core.api import YNABClient
from ynab_parser.core.models import Transaction

with YNABClient(api_token) as client:
    budgets = client.get_budgets()
    accounts = client.get_accounts(budget_id)
    result = client.create_transactions(budget_id, transactions)
```

### Transaction Processing

```python
from ynab_parser.processor import TransactionProcessor

# Parse all CSVs
grouped = TransactionProcessor.parse_all_transactions("data")

# Save normalized CSVs
TransactionProcessor.save_transactions(grouped, "results")
```

### Upload

```python
from ynab_parser.uploader import TransactionUploader

uploader = TransactionUploader(client, budget_id, dry_run=False)
stats = uploader.upload_all("results", account_mapping)
```

## Extending for Telegram Bot

The modular architecture supports adding a Telegram bot:

```python
# telegram_bot.py
from telegram import Update
from telegram.ext import Application, CommandHandler
from ynab_parser.processor import TransactionProcessor
from ynab_parser.uploader import TransactionUploader

async def handle_upload(update: Update, context):
    # User sends CSV via Telegram
    # → TransactionProcessor.parse_csv_file()
    # → TransactionUploader.upload_from_csv()
    # → Send confirmation
    pass

# Register in bot setup
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("upload", handle_upload))
```

## Migration Notes

### Command Mapping

| Action                 | Command                            |
| ---------------------- | ---------------------------------- |
| Run interactive setup  | `python -m ynab_parser.setup`      |
| Normalize CSVs         | `python -m ynab_parser.process`    |
| Upload results to YNAB | `python -m ynab_parser.upload`     |
| Programmatic access    | `from ynab_parser.core import ...` |

### Legacy Script Removal

The compatibility shims (`process_ynab.py`, `ynab_uploader.py`,
`setup_ynab.py`, `transactions_parser.py`, and standalone
`parsers/csv-parser-*.py`) were removed to eliminate duplicate entry points
and keep documentation focused on the supported CLI. Update cron jobs,
shortcuts, or external docs to invoke `python -m ynab_parser <command>`
directly.

## Installation Options

### Development Installation

```bash
pip install -e ".[dev]"
```

### With Telegram Support

```bash
pip install -e ".[telegram]"
```

### Production

```bash
pip install -e .
```

## Testing

Test files can be added to `tests/` directory:

```bash
pytest tests/
pytest --cov=src/ynab_parser tests/
```

## Code Quality

```bash
# Format
black src/

# Lint
flake8 src/

# Type check
mypy src/
```

## Future Enhancements

The new architecture supports:

1. **Telegram Bot Frontend**

    - File upload via Telegram
    - Transaction preview
    - Confirmation and status updates

2. **Additional Banks**

    - Just implement `BankCSVParser` interface
    - Register with `ParserFactory`

3. **Database Integration**

    - SQLAlchemy models ready to add
    - Transaction history tracking
    - Duplicate detection

4. **Scheduled Processing**

    - APScheduler integration ready
    - Automatic daily/weekly uploads
    - Error notifications

5. **Web Dashboard**
    - FastAPI/Flask ready
    - Account management
    - Upload history
    - Settings management

## File Structure After Refactoring

```
ynab-csv-parser/
├── src/
│   └── ynab_parser/           # Main package
│       ├── __init__.py
│       ├── __main__.py        # python -m ynab_parser
│       ├── cli.py             # Unified CLI
│       ├── process.py         # Process command
│       ├── upload.py          # Upload command
│       ├── setup.py           # Setup wizard
│       ├── converter.py       # CSV conversion
│       ├── processor.py       # Transaction processing
│       ├── uploader.py        # YNAB upload
│       ├── utils.py           # Utilities
│       ├── core/              # Core modules
│       │   ├── __init__.py
│       │   ├── api.py        # YNAB API client
│       │   ├── config.py     # Configuration
│       │   ├── exceptions.py # Exceptions
│       │   ├── logging_config.py
│       │   └── models.py     # Data models
│       └── parsers/           # CSV parsers
│           ├── __init__.py   # Parser interface
│           ├── ocbc.py       # OCBC parser
│           └── posb.py       # POSB parser
├── tests/                     # Test files (optional)
├── .env.example              # Config template
├── .env                      # Configuration (created by setup)
├── setup.py                  # Package setup
├── requirements.txt          # Dependencies
├── README.md                 # User guide
├── ARCHITECTURE.md           # Architecture guide
├── MIGRATION.md              # This file
├── data/
│   └── incoming/             # Input CSVs
└── results/                  # Output CSVs
```

## Recommendations

1. **Start using new CLI**: `python -m ynab_parser <command>`
2. **Update imports**: Use `src/ynab_parser/` modules directly in code
3. **Install as package**: `pip install -e .` for development
4. **Add type hints**: Use `mypy` for type checking
5. **Write tests**: Add tests in `tests/` directory
6. **Document changes**: Keep code comments updated

## Questions or Issues?

-   Review [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation
-   Check [README.md](README.md) for usage examples
-   Review module docstrings for API details
