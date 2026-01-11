# YNAB CSV Parser - Refactored Architecture Guide

## 📋 Table of Contents

-   [Overview](#overview)
-   [Project Structure](#project-structure)
-   [Core Modules](#core-modules)
-   [Usage Guide](#usage-guide)
-   [API Reference](#api-reference)
-   [Extending the System](#extending-the-system)
-   [Future Features](#future-features)

## Overview

This document describes the refactored architecture of the YNAB CSV Parser. The codebase has been reorganized to follow Python industry standards with:

-   **Modular design** for maintainability
-   **Type hints** throughout for better IDE support
-   **Comprehensive error handling** with custom exceptions
-   **Extensible architecture** ready for new features
-   **Factory patterns** for adding new banks
-   **Structured logging** for debugging and monitoring
-   **Clean separation of concerns**

### Design Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: Components receive dependencies, don't create them
3. **Factory Pattern**: Easy to add new parsers or handlers
4. **Type Safety**: Full type hints for validation and IDE support
5. **Error Handling**: Structured exception hierarchy
6. **Logging**: Comprehensive logging for debugging
7. **Configuration**: Centralized config management

## Project Structure

```
src/ynab_parser/
│
├── core/
│   ├── __init__.py
│   ├── api.py               # YNAB API client
│   ├── config.py            # Configuration management
│   ├── exceptions.py        # Custom exceptions
│   ├── logging_config.py    # Logging setup
│   └── models.py            # Data models (Transaction, Account, Budget)
│
├── parsers/
│   ├── __init__.py          # Parser interface & factory
│   ├── ocbc.py              # OCBC bank parser
│   └── posb.py              # POSB bank parser
│
├── converter.py             # CSV row to Transaction conversion
├── processor.py             # CSV parsing pipeline
├── uploader.py              # Transaction upload to YNAB
├── utils.py                 # Type hints and validation utilities
│
├── cli.py                   # Unified command-line interface
├── __init__.py              # Package exports
├── __main__.py              # python -m ynab_parser entry point
├── process.py               # Process command implementation
├── upload.py                # Upload command implementation
└── setup.py                 # Setup wizard implementation
```

## Core Modules

### 1. `core/models.py` - Data Models

Type-safe dataclasses for all entities:

```python
from ynab_parser.core.models import Transaction, Account, Budget

# Transaction: represents a single transaction
transaction = Transaction(
    account_id="account123",
    date="2026-01-11",
    amount=10000000,      # millicents (100.00)
    payee_name="Grocery Store",
    memo="Groceries",
    cleared="cleared",
    approved=True,
)
transaction.validate()  # Raises ValidationError if invalid

# Account: represents a YNAB account
account = Account(
    id="acc123",
    name="OCBC Default",
    type="checking",
    on_budget=True,
    balance=50000000,
)

# Budget: represents a YNAB budget
budget = Budget(
    id="budget123",
    name="My Budget",
    accounts=[account],
)
```

### 2. `core/exceptions.py` - Exception Hierarchy

Structured error handling:

```python
from ynab_parser.core.exceptions import (
    YNABParserError,      # Base exception
    ConfigurationError,   # Config issues
    ValidationError,      # Data validation
    ParserError,         # CSV parsing
    APIError,            # API errors
    YNABAuthError,       # Auth failed (401)
    YNABRateLimitError,  # Rate limit (429)
)

try:
    config = ConfigManager(".env")
    token = config.get_api_token()
except ConfigurationError as e:
    print(f"Config error: {e.error_code} - {e.message}")
    print(f"Details: {e.details}")
```

### 3. `core/config.py` - Configuration Management

Centralized configuration:

```python
from ynab_parser.core.config import ConfigManager

config = ConfigManager(".env")

# Get required configs
token = config.get_api_token()         # Required
budget_id = config.get_budget_id()    # Required
mapping = config.get_account_mapping()  # Recommended

# Get optional configs
timeout = config.get_api_timeout()      # Default: 30s
retries = config.get_max_retries()      # Default: 3
data_dir = config.get_data_dir()        # Default: "data"
results_dir = config.get_results_dir()  # Default: "results"
```

### 4. `core/api.py` - YNAB API Client

Professional API client with retry logic:

```python
from ynab_parser.core.api import YNABClient
from ynab_parser.core.exceptions import YNABAuthError, YNABRateLimitError

try:
    with YNABClient(api_token) as client:
        # Get budgets
        budgets = client.get_budgets()

        # Get accounts
        accounts = client.get_accounts(budget_id)

        # Create transactions
        result = client.create_transactions(budget_id, transactions)

except YNABAuthError as e:
    print("Authentication failed:", e)
except YNABRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
```

**Features:**

-   Automatic retry logic with exponential backoff
-   Rate limit handling with smart waiting
-   Comprehensive error classification
-   Context manager support
-   Type-safe transaction creation

### 5. `core/logging_config.py` - Logging Configuration

Structured logging with color support:

```python
from ynab_parser.core.logging_config import setup_logging, get_logger

# Setup main logger
logger = setup_logging(
    "ynab_parser",
    level=20,  # INFO
    log_file="logs/app.log",
    use_colors=True,
)

# Get module logger
logger = get_logger("parsers.ocbc")
logger.info("Parsing OCBC CSV...")
logger.warning("Skipping invalid row...")
logger.error("Parse failed:", exc_info=True)
```

### 6. `parsers/__init__.py` - Parser Interface & Factory

**Parser Interface:**

```python
from ynab_parser.parsers import BankCSVParser, ParserFactory
from ynab_parser.core.models import CSVRow
from typing import List

class MyBankParser(BankCSVParser):
    BANK_NAME = "mybank"

    def parse_file(self, file_path: str) -> List[CSVRow]:
        """Parse bank CSV file and return list of CSVRow objects."""
        # Implementation
        pass

# Register parser
ParserFactory.register_parser("mybank", MyBankParser)

# Use parser
parser = ParserFactory.get_parser("mybank")
rows = parser.parse_file("statement.csv")
```

**Parser Utilities:**

```python
# Clean description
description = BankCSVParser.clean_description("  Some  Description  ")
# → "Some Description"

# Parse amount
amount = BankCSVParser.parse_amount("1,234.56")
# → 1234.56

# Parse date
date = BankCSVParser.parse_date("11/01/2026", "%d/%m/%Y")
# → "01/11/2026"
```

### 7. `converter.py` - CSV to Transaction Conversion

Convert CSV rows to YNAB transactions:

```python
from ynab_parser.converter import TransactionConverter, TransactionFilter
from ynab_parser.core.models import CSVRow

converter = TransactionConverter(account_mapping={
    "ocbc_default": "account123",
})

# Convert CSV row to Transaction
csv_row = CSVRow(
    date="01/11/2026",
    payee="Grocery Store",
    memo="",
    outflow="50.00",
    inflow=None,
)

transaction = converter.csv_to_transaction(csv_row, "ocbc_default")

# Validate transaction
if TransactionFilter.is_valid(transaction):
    print("Valid transaction")
```

### 8. `processor.py` - Transaction Processing Pipeline

Orchestrate CSV parsing workflow:

```python
from ynab_parser.processor import TransactionProcessor

# Find and parse all bank CSVs
grouped = TransactionProcessor.parse_all_transactions("data")
# Returns: {("ocbc", "default"): [CSVRow, ...], ...}

# Save as normalized CSVs
saved_files = TransactionProcessor.save_transactions(grouped, "results")
```

### 9. `uploader.py` - Transaction Upload

Upload transactions to YNAB:

```python
from ynab_parser.uploader import TransactionUploader
from ynab_parser.core.api import YNABClient

with YNABClient(api_token) as client:
    uploader = TransactionUploader(
        client=client,
        budget_id=budget_id,
        dry_run=False,  # Set True to preview
    )

    # Upload all CSV files
    stats = uploader.upload_all("results", account_mapping)

    # Or upload single file
    stats = uploader.upload_from_csv(
        csv_path="results/ocbc_default.csv",
        account_id="account123",
        account_key="ocbc_default",
        account_mapping=account_mapping,
    )
```

## Usage Guide

### Command Line Usage

**Setup YNAB Integration:**

```bash
python -m ynab_parser setup
# Interactive wizard to configure API token and accounts
```

**Process Bank CSVs:**

```bash
python -m ynab_parser process [--data-dir data] [--output-dir results]
```

**Upload to YNAB:**

```bash
# Preview first (dry-run)
python -m ynab_parser upload --dry-run

# Upload for real
python -m ynab_parser upload [--config .env] [--budget-id ID]
```

**Get Help:**

```bash
python -m ynab_parser --help
python -m ynab_parser process --help
python -m ynab_parser upload --help
```

### Programmatic Usage

**Complete Workflow:**

```python
from ynab_parser.core.config import ConfigManager
from ynab_parser.core.api import YNABClient
from ynab_parser.processor import TransactionProcessor
from ynab_parser.uploader import TransactionUploader

# Load config
config = ConfigManager(".env")
api_token = config.get_api_token()
budget_id = config.get_budget_id()
account_mapping = config.get_account_mapping()

# Process CSVs
grouped = TransactionProcessor.parse_all_transactions("data")
TransactionProcessor.save_transactions(grouped, "results")

# Upload to YNAB
with YNABClient(api_token) as client:
    uploader = TransactionUploader(client, budget_id, dry_run=False)
    stats = uploader.upload_all("results", account_mapping)
    print(f"Uploaded: {stats}")
```

## API Reference

### Configuration API

```python
ConfigManager(env_file: str = ".env")
├── get_api_token() -> str
├── get_budget_id(override: str = None) -> str
├── get_account_mapping() -> Dict[str, str]
├── get_data_dir(override: str = None) -> str
├── get_results_dir(override: str = None) -> str
├── get_api_timeout() -> int
├── get_max_retries() -> int
└── is_dry_run() -> bool
```

### API Client

```python
YNABClient(api_token: str, timeout: int = 30, max_retries: int = 3)
├── get_budgets() -> List[Budget]
├── get_accounts(budget_id: str) -> List[Account]
├── create_transactions(budget_id: str, transactions: List[Transaction]) -> Dict
├── close() -> None
├── __enter__() -> YNABClient
└── __exit__(...) -> None
```

### Transaction Processing

```python
TransactionProcessor
├── find_csv_files(data_dir: str) -> List[Dict]
├── parse_csv_file(file_path: str, bank: str) -> List[CSVRow]
├── parse_all_transactions(data_dir: str) -> Dict[Tuple[str, str], List[CSVRow]]
└── save_transactions(grouped: Dict, output_dir: str) -> List[str]
```

### Transaction Upload

```python
TransactionUploader(client: YNABClient, budget_id: str, dry_run: bool = False)
├── upload_from_csv(...) -> Dict[str, int]
└── upload_all(results_dir: str, account_mapping: Dict) -> Dict[str, Dict]
```

## Extending the System

### Adding a New Bank Parser

1. **Implement the parser:**

```python
# src/ynab_parser/parsers/mybank.py
from ynab_parser.parsers import BankCSVParser, ParserFactory
from ynab_parser.core.models import CSVRow
from typing import List

class MyBankParser(BankCSVParser):
    BANK_NAME = "mybank"

    def parse_file(self, file_path: str) -> List[CSVRow]:
        # Your parsing logic
        pass

# Register it
ParserFactory.register_parser("mybank", MyBankParser)
```

2. **Use it:**

```python
parser = ParserFactory.get_parser("mybank")
rows = parser.parse_file("statement.csv")
```

### Adding a Telegram Bot Frontend

```python
# telegram_bot.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from ynab_parser.core.config import ConfigManager
from ynab_parser.core.api import YNABClient
from ynab_parser.processor import TransactionProcessor
from ynab_parser.uploader import TransactionUploader

logger = logging.getLogger(__name__)

async def handle_start(update: Update, context):
    await update.message.reply_text("Send me a bank CSV file to process")

async def handle_file(update: Update, context):
    # Download file
    file = await update.message.document.get_file()
    await file.download_to_drive("temp.csv")

    # Parse
    try:
        config = ConfigManager(".env")
        # ... process file
        await update.message.reply_text("✓ Uploaded successfully!")
    except Exception as e:
        await update.message.reply_text(f"✗ Error: {e}")

# Setup bot
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", handle_start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.run_polling()
```

## Future Features

The architecture supports:

1. **Database Integration**

    - SQLAlchemy models
    - Transaction history
    - Duplicate detection

2. **Scheduled Processing**

    - APScheduler integration
    - Daily/weekly uploads
    - Error notifications

3. **Web Dashboard**

    - FastAPI/Flask
    - Account management
    - Upload history
    - Settings

4. **Additional Banks**

    - Just implement `BankCSVParser`
    - Register with factory
    - No core changes needed

5. **Advanced Features**
    - Transaction categorization
    - Duplicate detection
    - Transaction matching
    - Budget forecasting

## Conclusion

The refactored architecture provides a solid foundation for current and future development. The modular design makes it easy to:

-   Add new banks
-   Integrate new frontend technologies
-   Extend with new features
-   Test individual components
-   Maintain and debug code

For questions or contributions, refer to the inline documentation in the code.
