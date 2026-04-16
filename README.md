# YNAB CSV Parser

A comprehensive Python tool that converts bank transaction exports (OCBC, POSB) into YNAB-compatible CSV format and optionally uploads them directly to your YNAB budget via the API.

## Features

- **Multi-Bank Support**: Parse transactions from OCBC and POSB bank exports
- **YNAB Integration**: Direct upload to YNAB via API with automatic account mapping
- **Local Browser UI**: One-page upload flow with budget and account dropdowns
- **Flexible Processing**: Process multiple accounts and banks in a single run
- **Dry-Run Mode**: Preview transactions before uploading to YNAB
- **Interactive Setup**: Guided configuration wizard for API tokens and account mappings
- **Structured Logging**: Detailed logging for debugging and monitoring
- **Extensible Architecture**: Easy to add support for additional banks

## Requirements

- Python 3.8 or higher
- YNAB account with API access
- Bank transaction CSV exports

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ynab-csv-parser
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install the Package

You have two installation options:

**Option A: Editable Mode (Recommended for Development)**
```bash
pip install --upgrade pip
pip install -e .
```

**Option B: Normal Installation**
```bash
pip install --upgrade pip
pip install .
```

**Difference:**
- **Editable mode (`-e`)**: Links to your source code, so code changes are immediately available without reinstalling. Best for development.
- **Normal mode**: Copies files to site-packages. You need to reinstall after making changes. Best for production use.

Both modes work identically for running the package. The package must be installed (either way) to use `python -m ynab_parser` commands.

## Quick Start

### Step 1: Configure YNAB Integration

Run the interactive setup wizard to configure your YNAB API token and account mappings:

```bash
python -m ynab_parser setup
```

This will:
- Prompt for your YNAB API token (get it from https://app.ynab.com/settings/developer)
- Verify the token by connecting to YNAB
- Let you select your budget
- Map your bank accounts to YNAB accounts
- Save configuration to `.env` file

### Step 2: Prepare Bank CSV Files

Place your bank transaction CSV files in the appropriate directories:

```
data/incoming/
├── ocbc/
│   └── TransactionHistory_YYYYMMDDHHMMSS.csv
└── posb/
    ├── everyday-use/
    │   └── <filename>.csv
    └── my-savings/
        └── <filename>.csv
```

**Supported Banks:**
- **OCBC**: Place CSV files directly in `data/incoming/ocbc/`
- **POSB**: Place CSV files in subdirectories under `data/incoming/posb/` (e.g., `everyday-use/`, `my-savings/`)

### Step 3: Process Transactions

Parse all CSV files and generate normalized YNAB-compatible CSVs:

```bash
python -m ynab_parser process
```

This will:
- Scan `data/incoming/` recursively for CSV files
- Parse each file using the appropriate bank parser
- Group transactions by bank and account
- Generate normalized CSV files in `results/` directory

**Output Format:**
- Files are named: `{bank}_{account}_{start-date}_{end-date}.csv`
- Example: `posb_everyday-use_12-2025_01-2026.csv`

### Step 4: Preview Upload (Dry-Run)

Before uploading to YNAB, preview what will be uploaded:

```bash
python -m ynab_parser upload --dry-run
```

This shows:
- Which transactions will be uploaded
- Which YNAB accounts they'll be mapped to
- Any validation errors

### Optional: Use the Local Browser UI

Instead of the CLI flow, you can launch the one-page browser UI:

```bash
python -m ynab_parser ui
```

Then open the printed local URL in your browser. The UI lets you:

- load budgets from YNAB
- load accounts for the selected budget
- upload a bank CSV file
- preview parsed transactions on the same page
- click `Review and Upload` to send them directly to the selected account

### Step 5: Upload to YNAB

Upload transactions to your YNAB budget:

```bash
python -m ynab_parser upload
```

This will:
- Read normalized CSV files from `results/`
- Convert them to YNAB transaction format
- Upload via YNAB API
- Show upload summary with success/error counts

## Command Reference

### Setup Command

```bash
python -m ynab_parser setup
```

Interactive wizard that configures:
- YNAB API token
- Budget selection
- Account mappings (OCBC_DEFAULT, POSB_EVERYDAY_USE, POSB_MY_SAVINGS)

### Process Command

```bash
python -m ynab_parser process [--data-dir DIR] [--output-dir DIR]
```

**Options:**
- `--data-dir`: Input directory (default: `data`)
- `--output-dir`: Output directory (default: `results`)

**What it does:**
- Discovers all CSV files under `data/incoming/`
- Automatically detects bank type from directory structure
- Parses transactions and normalizes to YNAB format
- Groups by bank and account
- Saves normalized CSVs to output directory

### Upload Command

```bash
python -m ynab_parser upload [--config FILE] [--budget-id ID] [--results-dir DIR] [--dry-run]
```

**Options:**
- `--config`: Configuration file path (default: `.env`)
- `--budget-id`: Override budget ID from config
- `--results-dir`: Directory containing result CSVs (default: `results`)
- `--dry-run`: Preview without uploading

**What it does:**
- Loads normalized CSV files from results directory
- Maps account names to YNAB account IDs
- Converts to YNAB transaction format
- Uploads via YNAB API (or previews if `--dry-run`)

### UI Command

```bash
python -m ynab_parser ui [--host HOST] [--port PORT] [--config FILE]
```

**Options:**
- `--host`: Host to bind (default: `127.0.0.1`)
- `--port`: Port to bind (default: `8765`)
- `--config`: Configuration file path (default: `.env`)

**What it does:**
- Starts a local browser-based upload UI
- Fetches budgets and accounts live from YNAB
- Parses uploaded CSV files into a preview
- Uploads previewed rows directly to the chosen YNAB account

## Configuration

Configuration is stored in a `.env` file (created by the setup wizard):

```env
# YNAB API Configuration
YNAB_API_TOKEN=your_api_token_here
YNAB_BUDGET_ID=your_budget_id

# Account mappings (CSV account name -> YNAB account ID)
OCBC_DEFAULT=ynab_account_id_1
POSB_EVERYDAY_USE=ynab_account_id_2
POSB_MY_SAVINGS=ynab_account_id_3

# Optional: API settings
YNAB_API_TIMEOUT=30
YNAB_MAX_RETRIES=3
```

### Getting Your YNAB API Token

1. Log in to YNAB at https://app.ynab.com
2. Go to Settings → Developer Settings
3. Click "Generate New Token"
4. Copy the token (you won't be able to see it again)

### Finding Your Budget ID

The setup wizard will show your budget ID, or you can find it in the YNAB API URL when viewing your budget in the web app.

## Project Structure

```
ynab-csv-parser/
├── src/ynab_parser/          # Main package
│   ├── core/                 # Core functionality
│   │   ├── api.py           # YNAB API client
│   │   ├── config.py        # Configuration management
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── logging_config.py # Logging setup
│   │   └── models.py        # Data models
│   ├── parsers/             # Bank-specific parsers
│   │   ├── ocbc.py         # OCBC parser
│   │   └── posb.py         # POSB parser
│   ├── cli.py              # Command-line interface
│   ├── processor.py        # Transaction processing pipeline
│   ├── uploader.py         # YNAB upload logic
│   ├── setup.py            # Interactive setup wizard
│   ├── process.py           # Process command entry point
│   └── upload.py            # Upload command entry point
├── data/
│   └── incoming/            # Place bank CSV files here
│       ├── ocbc/
│       └── posb/
├── results/                 # Normalized CSV output
├── .env                     # Configuration (created by setup)
├── requirements.txt         # Python dependencies
└── setup.py                 # Package setup
```

## Supported Bank Formats

### OCBC

**File Location:** `data/incoming/ocbc/*.csv`

**Expected Format:**
- CSV with headers
- Date format: `DD/MM/YYYY` or `DD-MM-YYYY`
- Amount column with positive/negative values

### POSB

**File Location:** `data/incoming/posb/{account-name}/*.csv`

**Expected Format:**
- CSV with headers
- Date format: `DD MMM YYYY` (e.g., "10 Jan 2026")
- Separate debit/credit columns or signed amount

**Account Subdirectories:**
- `everyday-use/` → mapped to `POSB_EVERYDAY_USE`
- `my-savings/` → mapped to `POSB_MY_SAVINGS`
- Other subdirectories → mapped to `posb_{subdirectory-name}`

## Troubleshooting

### No Transactions Detected

**Symptoms:** Process command finds no transactions

**Solutions:**
- Verify CSV files are in correct directories (`data/incoming/{bank}/`)
- Check file encoding (should be UTF-8)
- Ensure files match expected bank format
- Check logs for parsing errors

### Date Parse Errors

**Symptoms:** Warnings about date parsing

**Solutions:**
- Ensure bank exports are unmodified
- POSB dates should be: `DD MMM YYYY` (e.g., "10 Jan 2026")
- OCBC dates should be: `DD/MM/YYYY` or `DD-MM-YYYY`
- Check for hidden characters or encoding issues

### Upload Errors

**Symptoms:** Transactions fail to upload to YNAB

**Solutions:**
- Run `python -m ynab_parser setup` to refresh API token
- Use `--dry-run` to preview transactions before uploading
- Verify account mappings in `.env` file
- Check YNAB API status and rate limits
- Review error messages in logs

### Configuration Errors

**Symptoms:** "Configuration error" messages

**Solutions:**
- Ensure `.env` file exists and is readable
- Verify `YNAB_API_TOKEN` is set correctly
- Verify `YNAB_BUDGET_ID` is set correctly
- Check account mapping variables match your CSV account names

## Development

### Installing for Development

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode with development dependencies (pytest, black, mypy, flake8).

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
```

### Type Checking

```bash
mypy src/
```

### Adding a New Bank Parser

1. Create a new parser class in `src/ynab_parser/parsers/`:
   ```python
   from . import BankCSVParser
   
   class NewBankParser(BankCSVParser):
       BANK_NAME = "newbank"
       
       def parse_file(self, file_path: str) -> List[CSVRow]:
           # Implementation
   ```

2. Register it in `src/ynab_parser/parsers/__init__.py`:
   ```python
   from .newbank import NewBankParser
   ParserFactory.register(NewBankParser)
   ```

3. Place CSV files in `data/incoming/newbank/`

## API Reference

### Core Classes

- **`ConfigManager`**: Manages configuration from `.env` files
- **`YNABClient`**: YNAB API client with retry logic
- **`TransactionProcessor`**: Processes and normalizes transactions
- **`TransactionUploader`**: Handles YNAB uploads

### Models

- **`Transaction`**: Represents a YNAB transaction
- **`Account`**: Represents a YNAB account
- **`Budget`**: Represents a YNAB budget
- **`CSVRow`**: Normalized transaction row

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or feature requests, please open an issue on the repository.
