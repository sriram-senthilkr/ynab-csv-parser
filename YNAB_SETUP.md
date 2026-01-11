# YNAB CSV Parser & Uploader

A professional-grade Python application for parsing bank transaction CSVs and uploading them to YNAB (You Need A Budget) via their official API.

## Features

-   ✅ Parses transactions from multiple banks (OCBC, POSB, with extensibility for others)
-   ✅ Converts CSV format to YNAB API format with proper amount handling
-   ✅ RESTful API client following industry best practices
-   ✅ Secure token management via environment variables
-   ✅ Comprehensive error handling and logging
-   ✅ Dry-run mode for safe testing
-   ✅ Batch transaction upload support

## Architecture

The project follows a modular design with clear separation of concerns:

```
├── process_ynab.py           # Main orchestrator
├── transactions_parser.py    # CSV parsing logic
├── ynab_api.py              # YNAB REST API client (production-ready)
├── ynab_uploader.py         # CSV to YNAB conversion & upload
├── parsers/                 # Bank-specific CSV parsers
├── data/                    # Input data (bank CSVs)
├── results/                 # Output (parsed transactions)
└── .env                     # Configuration (create from .env.example)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get YNAB API Token

1. Go to https://app.ynab.com/settings/developer
2. Click "Generate New Token"
3. Copy your API token

### 3. Find Your Budget and Account IDs

Use the YNAB API to discover your IDs:

```bash
python3 -c "
from ynab_api import YNABClient
client = YNABClient(api_token='YOUR_TOKEN_HERE')
budgets = client.get_budgets()
for b in budgets:
    print(f\"Budget: {b['name']} (ID: {b['id']})\")"
```

Then get account IDs for a budget:

```bash
python3 -c "
from ynab_api import YNABClient
client = YNABClient(api_token='YOUR_TOKEN_HERE')
accounts = client.get_accounts('YOUR_BUDGET_ID')
for a in accounts:
    print(f\"Account: {a['name']} (ID: {a['id']})\")"
```

### 4. Configure Environment

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
YNAB_API_TOKEN=your_api_token_from_step_2
YNAB_BUDGET_ID=your_budget_id_from_step_3

# Map your bank accounts to YNAB account IDs
OCBC_DEFAULT=account_id_from_step_3
POSB_EVERYDAY_USE=account_id_from_step_3
POSB_MY_SAVINGS=account_id_from_step_3
```

### 5. Add Bank Transaction Files

Place your bank CSV files in:

```
data/incoming/
├── ocbc/
│   └── ACCT_920_01_01_2026.OFX
├── posb/
│   ├── everyday-use/
│   │   └── transactions.csv
│   └── my-savings/
│       └── transactions.csv
└── [other banks]/
```

## Usage

### Parse Transactions

```bash
python3 process_ynab.py
```

This:

1. Scans `data/incoming/` for bank CSVs
2. Parses each with bank-specific parser
3. Outputs combined results to `results/`

### Upload to YNAB

```bash
# Preview what would be uploaded (no API calls)
python3 ynab_uploader.py --dry-run

# Actually upload to YNAB
python3 ynab_uploader.py

# Upload with specific budget (override .env)
python3 ynab_uploader.py --budget-id my_budget_id

# Use different config file
python3 ynab_uploader.py --config config/.env.prod
```

### Full Workflow

```bash
# 1. Parse all bank CSVs
python3 process_ynab.py

# 2. Preview upload (dry-run)
python3 ynab_uploader.py --dry-run

# 3. Verify the preview looks correct

# 4. Actually upload
python3 ynab_uploader.py
```

## API Client Usage

The `YNABClient` is fully typed and documented, suitable for production use:

```python
from ynab_api import YNABClient, Transaction

# Initialize client
client = YNABClient(api_token="your_token")

# Get available budgets
budgets = client.get_budgets()
print(budgets[0]["name"])

# Get accounts in a budget
accounts = client.get_accounts("budget_id_123")

# Create transactions
transactions = [
    Transaction(
        account_id="acct_123",
        date="2026-01-15",
        amount=-50000,  # Amount in millicents
        payee_name="Coffee Shop",
        memo="Morning coffee",
        cleared="cleared",
        approved=True,
    )
]

result = client.create_transactions("budget_id_123", transactions)
print(f"Created {len(result['transactions'])} transactions")

client.close()
```

Or use as context manager:

```python
with YNABClient(api_token="token") as client:
    result = client.create_transactions("budget_id", transactions)
```

## Amount Format

YNAB API uses **millicents** (1/1000th of a cent):

-   $10.00 = 1,000,000 millicents
-   $0.01 = 1,000 millicents
-   Negative = outflow (spending)
-   Positive = inflow (income)

The converter handles this automatically from your CSV values.

## Error Handling

The API client includes proper error handling:

```python
from ynab_api import YNABClient, YNABAuthError, YNABRateLimitError, YNABAPIError

try:
    client = YNABClient(api_token="token")
    result = client.create_transactions("budget_id", transactions)
except YNABAuthError:
    print("Invalid API token")
except YNABRateLimitError as e:
    print(f"Rate limited: {e}")
except YNABAPIError as e:
    print(f"API error: {e}")
```

## Logging

The uploader includes detailed logging:

```bash
# See INFO level logs (default)
python3 ynab_uploader.py

# See DEBUG level logs
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG)" && python3 ynab_uploader.py
```

## Security Notes

-   🔒 Never commit `.env` to version control
-   🔒 API tokens are sensitive - treat like passwords
-   🔒 Use `.env.example` for safe configuration templates
-   🔒 Consider environment-specific configs (`.env.dev`, `.env.prod`)

## YNAB API Reference

-   [Official YNAB API Docs](https://api.ynab.com/v1)
-   [Create Transactions Endpoint](https://api.ynab.com/v1#/Transactions/createTransaction)
-   [Rate Limits](https://api.ynab.com/v1#/api-request-limits)

## Extending to Other Banks

Each bank needs a parser in `parsers/`:

```python
# parsers/csv-parser-newbank.py
import sys
import csv

def parse(input_csv, output_csv):
    # Read input CSV in bank's format
    # Write output CSV in YNAB format:
    # Date, Payee, Memo, Outflow, Inflow
    pass

if __name__ == "__main__":
    parse(sys.argv[1], sys.argv[2])
```

Then register in `transactions_parser.py`:

```python
parsers = {
    "ocbc": "parsers/csv-parser-ocbc.py",
    "posb": "parsers/csv-parser-posb.py",
    "newbank": "parsers/csv-parser-newbank.py",  # Add here
}
```

## License

[Your License Here]

## Support

For issues with:

-   **YNAB API**: See [YNAB API Docs](https://api.ynab.com/v1)
-   **Bank CSV parsing**: Check `parsers/` and your bank's export format
-   **This tool**: Check `.env` configuration and logs

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black *.py

# Lint
pylint *.py
```
