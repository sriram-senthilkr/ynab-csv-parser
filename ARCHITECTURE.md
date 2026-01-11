# YNAB CSV Parser

A professional-grade Python package for parsing bank transaction CSVs and uploading them to YNAB.

## Features

-   ✅ Bank-agnostic CSV parsing with extensible parser interface
-   ✅ YNAB API client with automatic retries and rate-limit handling
-   ✅ Comprehensive error handling and logging
-   ✅ Type hints throughout for better IDE support
-   ✅ Configuration management with environment variables
-   ✅ Modular architecture ready for Telegram bot integration
-   ✅ Interactive setup wizard

## Supported Banks

-   OCBC (Oversea-Chinese Banking Corporation)
-   POSB (Singapore Post Office Savings Bank)

Additional banks can be added by implementing the `BankCSVParser` interface.

## Installation

### Option 1: Development Installation (Recommended)

```bash
# Clone or navigate to project directory
cd ynab-csv-parser

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Or with Telegram bot support (future)
pip install -e ".[telegram]"
```

### Option 2: Regular Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Initial Setup

```bash
python -m ynab_parser.setup
```

This wizard will:

-   Verify your YNAB API token
-   Let you select your budget
-   Map your bank accounts to YNAB accounts
-   Save configuration to `.env`

### 2. Prepare Bank CSVs

Download your transaction history from your bank and place files in:

```
data/incoming/
├── ocbc/
│   └── TransactionHistory_20260111.csv
├── posb/
│   ├── everyday-use/
│   │   └── transactions.csv
│   └── my-savings/
│       └── transactions.csv
```

### 3. Process Transactions

```bash
python -m ynab_parser.process
```

This creates normalized CSVs in `results/` directory:

```
results/
├── ocbc_default_12-2025_01-2026.csv
├── posb_everyday-use_12-2025_01-2026.csv
└── posb_my-savings_12-2025_01-2026.csv
```

### 4. Upload to YNAB

Preview (dry-run):

```bash
python -m ynab_parser.upload --dry-run
```

Upload for real:

```bash
python -m ynab_parser.upload
```

## Project Structure

```
src/ynab_parser/
├── __init__.py           # Package exports
├── core/
│   ├── api.py           # YNAB API client
│   ├── config.py        # Configuration management
│   ├── exceptions.py    # Custom exceptions
│   ├── logging_config.py # Logging setup
│   └── models.py        # Data models
├── parsers/
│   ├── __init__.py      # Parser interface & factory
│   ├── ocbc.py          # OCBC parser
│   └── posb.py          # POSB parser
├── converter.py         # CSV → Transaction conversion
├── processor.py         # Pipeline orchestration
├── uploader.py          # YNAB upload handler
├── process.py           # CLI: Process command
├── upload.py            # CLI: Upload command
└── setup.py             # CLI: Setup wizard
```

## API Reference

### Configuration

```python
from ynab_parser.core.config import ConfigManager

config = ConfigManager(".env")
api_token = config.get_api_token()
budget_id = config.get_budget_id()
account_mapping = config.get_account_mapping()
```

### API Client

```python
from ynab_parser.core.api import YNABClient

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

### Transaction Upload

```python
from ynab_parser.uploader import TransactionUploader

uploader = TransactionUploader(client, budget_id, dry_run=False)
stats = uploader.upload_all("results", account_mapping)
```

## Environment Variables

```bash
# Required
YNAB_API_TOKEN=your_token_here
YNAB_BUDGET_ID=your_budget_id

# Account mappings (get from setup wizard)
OCBC_DEFAULT=account_id_1
POSB_EVERYDAY_USE=account_id_2
POSB_MY_SAVINGS=account_id_3

# Optional
YNAB_API_TIMEOUT=30                    # Request timeout in seconds
YNAB_MAX_RETRIES=3                     # Number of retries for failed requests
DATA_DIR=data                          # Input data directory
RESULTS_DIR=results                    # Output results directory
DRY_RUN=false                          # Preview mode without posting
```

## Error Handling

The package provides structured exception hierarchy:

```python
from ynab_parser.core.exceptions import (
    YNABParserError,        # Base exception
    ConfigurationError,     # Config issues
    ValidationError,        # Data validation
    ParserError,           # CSV parsing
    APIError,              # API errors
    YNABAuthError,         # Auth failed (401)
    YNABRateLimitError,    # Rate limit (429)
)
```

## Extending with Custom Parsers

Add support for a new bank by implementing `BankCSVParser`:

```python
from ynab_parser.parsers import BankCSVParser, ParserFactory
from ynab_parser.core.models import CSVRow

class MyBankParser(BankCSVParser):
    BANK_NAME = "mybank"

    def parse_file(self, file_path: str) -> List[CSVRow]:
        # Implement CSV parsing
        pass

# Register the parser
ParserFactory.register_parser("mybank", MyBankParser)
```

## Future: Telegram Bot Integration

The modular architecture supports adding a Telegram bot frontend:

```python
from telegram import Update
from telegram.ext import Application, CommandHandler

from ynab_parser.processor import TransactionProcessor
from ynab_parser.uploader import TransactionUploader

async def handle_upload(update: Update, context):
    # User uploads file via Telegram
    # → Parse with TransactionProcessor
    # → Upload with TransactionUploader
    # → Send confirmation
    pass
```

## Development

### Running Tests

```bash
pytest tests/
pytest --cov=src/ynab_parser tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

### Building Package

```bash
pip install build
python -m build
```

## Troubleshooting

### "API token not configured"

-   Run setup wizard: `python -m ynab_parser.setup`
-   Or set `YNAB_API_TOKEN` environment variable

### "No account mappings configured"

-   Run setup wizard again: `python -m ynab_parser.setup`
-   Or manually edit `.env` file with account IDs

### "No CSV files found"

-   Check file location: `data/incoming/{bank_name}/`
-   Verify bank name is lowercase (ocbc, posb)
-   Ensure files are `.csv` format

### "Rate limit exceeded"

-   The tool automatically retries with exponential backoff
-   Default retry after 60 seconds
-   Reduce batch size if uploading many transactions

## License

MIT

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues or questions:

-   Check the [Quick Start](#quick-start) section
-   Review [Environment Variables](#environment-variables)
-   Open an issue on GitHub
