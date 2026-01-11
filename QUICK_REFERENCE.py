#!/usr/bin/env python3
"""
YNAB Integration - Quick Reference Guide

This file provides quick examples and reference for the YNAB integration.
"""

# ============================================================================
# QUICK START - 3 STEPS
# ============================================================================

# Step 1: Install dependencies
# $ pip install -r requirements.txt

# Step 2: Run setup wizard (interactive)
# $ python3 setup_ynab.py

# Step 3: Upload transactions
# $ python3 ynab_uploader.py --dry-run  # Preview
# $ python3 ynab_uploader.py             # Upload for real


# ============================================================================
# API CLIENT EXAMPLES
# ============================================================================

from ynab_api import YNABClient, Transaction, YNABAuthError

# Example 1: Get all budgets
with YNABClient(api_token="your_token") as client:
    budgets = client.get_budgets()
    for budget in budgets:
        print(f"{budget['name']}: {budget['id']}")


# Example 2: Get accounts in a budget
with YNABClient(api_token="your_token") as client:
    accounts = client.get_accounts("budget_123")
    for account in accounts:
        print(f"{account['name']}: {account['id']}")


# Example 3: Create a single transaction
with YNABClient(api_token="your_token") as client:
    transaction = Transaction(
        account_id="acct_123",
        date="2026-01-15",
        amount=-50000,  # $50.00 spent (negative = outflow)
        payee_name="Coffee Shop",
        memo="Morning coffee",
        cleared="cleared",
        approved=True,
    )
    
    result = client.create_transactions(
        budget_id="budget_123",
        transactions=[transaction]
    )
    print(f"Created {len(result['transactions'])} transaction(s)")


# Example 4: Create multiple transactions
transactions = [
    Transaction(
        account_id="acct_123",
        date="2026-01-15",
        amount=-50000,
        payee_name="Store A",
        memo="Groceries",
    ),
    Transaction(
        account_id="acct_123",
        date="2026-01-14",
        amount=100000000,  # $100,000.00 income
        payee_name="Employer",
        memo="Salary",
    ),
]

with YNABClient(api_token="your_token") as client:
    result = client.create_transactions("budget_123", transactions)


# Example 5: Error handling
from ynab_api import YNABRateLimitError, YNABAPIError

try:
    with YNABClient(api_token="your_token") as client:
        result = client.create_transactions("budget_123", transactions)
except YNABAuthError as e:
    print(f"Authentication failed: {e}")
except YNABRateLimitError as e:
    print(f"Rate limited: {e}")
except YNABAPIError as e:
    print(f"API error: {e}")


# ============================================================================
# CONFIGURATION (.env) REFERENCE
# ============================================================================

"""
# YNAB API token from https://app.ynab.com/settings/developer
YNAB_API_TOKEN=your_api_token_here

# Budget ID (from API discovery)
YNAB_BUDGET_ID=your_budget_id

# Account mappings (CSV name -> YNAB account ID)
OCBC_DEFAULT=account_id_1
POSB_EVERYDAY_USE=account_id_2
POSB_MY_SAVINGS=account_id_3
"""


# ============================================================================
# AMOUNT FORMAT REFERENCE
# ============================================================================

"""
YNAB uses MILLICENTS (1/1000th of a cent)

Display   Millicents  Formula
$100.00   10000000    100 × 100,000
$10.00    1000000     10 × 100,000
$1.00     100000      1 × 100,000
$0.10     10000       0.10 × 100,000
$0.01     1000        0.01 × 100,000

SIGN CONVENTION:
- Negative = Money out (spending)
- Positive = Money in (income)

EXAMPLES:
amount = -50000    # -$0.50 spent
amount = 100000    # $1.00 earned
amount = -2000000  # -$20.00 spent
"""


# ============================================================================
# CSV TO YNAB CONVERSION
# ============================================================================

from ynab_uploader import TransactionConverter

# Example: Convert CSV row to transaction
converter = TransactionConverter(
    account_mapping={
        "ocbc_default": "acct_123",
        "posb_everyday_use": "acct_456",
    }
)

csv_row = {
    "Date": "15/01/2026",
    "Payee": "Coffee Shop",
    "Memo": "Morning coffee",
    "Outflow": "5.00",
    "Inflow": "",
}

transaction = converter.csv_row_to_transaction(csv_row, "acct_123")
print(f"Date: {transaction.date}")           # 2026-01-15
print(f"Amount: {transaction.amount}")       # -500000 (millicents)
print(f"Payee: {transaction.payee_name}")    # Coffee Shop


# ============================================================================
# COMMAND LINE USAGE
# ============================================================================

"""
# Interactive setup (discover budgets, accounts, create .env)
python3 setup_ynab.py

# Parse all bank CSVs (outputs to results/)
python3 process_ynab.py

# Upload with dry-run (preview without posting)
python3 ynab_uploader.py --dry-run

# Upload transactions to YNAB
python3 ynab_uploader.py

# Upload with specific budget
python3 ynab_uploader.py --budget-id my_budget_id

# Use custom .env file
python3 ynab_uploader.py --config config/.env.prod
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
PROBLEM: "Invalid API token"
SOLUTION:
  - Verify token from https://app.ynab.com/settings/developer
  - Check .env for typos or whitespace
  - Regenerate token if needed

PROBLEM: "Budget not found"
SOLUTION:
  - Run: python3 setup_ynab.py
  - Verify YNAB_BUDGET_ID in .env
  - Check token has access to budget

PROBLEM: "No transactions uploaded"
SOLUTION:
  - Check account mappings in .env
  - Verify CSV files exist in results/
  - Run: python3 ynab_uploader.py --dry-run
  - Check CSV format (Date, Payee, Memo, Outflow, Inflow)

PROBLEM: "Rate limit error (429)"
SOLUTION:
  - Wait 60 seconds before retrying
  - Split large uploads (max 100 per request)
  - YNAB limit: 100 requests/hour per user
"""


# ============================================================================
# SECURITY BEST PRACTICES
# ============================================================================

"""
✅ DO:
  - Store API token in .env (never in code)
  - Use .env.example as template
  - Add .env to .gitignore
  - Rotate tokens periodically
  - Use environment-specific configs

❌ DON'T:
  - Hardcode API tokens
  - Commit .env to version control
  - Share .env files
  - Use same token for multiple environments
  - Log sensitive information
"""


# ============================================================================
# EXTENDING TO NEW BANKS
# ============================================================================

"""
Step 1: Create bank parser
  File: parsers/csv-parser-newbank.py
  
  import csv
  import sys
  
  def parse(input_csv, output_csv):
      with open(input_csv) as inf, open(output_csv, 'w') as outf:
          reader = csv.DictReader(inf)
          writer = csv.DictWriter(outf, ['Date', 'Payee', 'Memo', 'Outflow', 'Inflow'])
          writer.writeheader()
          
          for row in reader:
              writer.writerow({
                  'Date': convert_to_dd_mm_yyyy(row['date']),
                  'Payee': row['merchant'],
                  'Memo': row['description'],
                  'Outflow': row['amount'] if row['type'] == 'DEBIT' else '',
                  'Inflow': row['amount'] if row['type'] == 'CREDIT' else '',
              })
  
  if __name__ == '__main__':
      parse(sys.argv[1], sys.argv[2])

Step 2: Register in transactions_parser.py
  parsers = {
      "ocbc": "parsers/csv-parser-ocbc.py",
      "posb": "parsers/csv-parser-posb.py",
      "newbank": "parsers/csv-parser-newbank.py",  # Add this
  }

Step 3: Add account mappings in .env
  NEWBANK_DEFAULT=account_id

Step 4: Place CSVs in data/incoming/newbank/

Step 5: Run!
  python3 process_ynab.py
  python3 ynab_uploader.py
"""


# ============================================================================
# USEFUL COMMANDS
# ============================================================================

"""
# List all budgets
python3 -c "
from ynab_api import YNABClient
import os
token = os.getenv('YNAB_API_TOKEN')
with YNABClient(api_token=token) as c:
    for b in c.get_budgets():
        print(f'{b[\"name\"]}: {b[\"id\"]}')"

# List all accounts
python3 -c "
from ynab_api import YNABClient
import os
token = os.getenv('YNAB_API_TOKEN')
budget_id = 'YOUR_BUDGET_ID'
with YNABClient(api_token=token) as c:
    for a in c.get_accounts(budget_id):
        print(f'{a[\"name\"]}: {a[\"id\"]}')"

# Test API connection
python3 -c "
from ynab_api import YNABClient
import os
token = os.getenv('YNAB_API_TOKEN')
try:
    with YNABClient(api_token=token) as c:
        budgets = c.get_budgets()
        print(f'✓ Connected! Found {len(budgets)} budget(s)')
except Exception as e:
    print(f'✗ Error: {e}')"

# Check CSV conversion
python3 -c "
import csv
with open('results/ocbc_default_12-2025_01-2026.csv') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 3:
            print(f'{row[\"Date\"]}: {row[\"Payee\"]} ({row[\"Outflow\"]}/{row[\"Inflow\"]})')
        else:
            break"
"""

# ============================================================================
# REFERENCES
# ============================================================================

"""
API Documentation:
  - YNAB API: https://api.ynab.com/v1
  - Transactions: https://api.ynab.com/v1#/Transactions/createTransaction
  - Rate Limits: https://api.ynab.com/v1#/api-request-limits

Tools & Libraries:
  - requests: https://requests.readthedocs.io/
  - python-dotenv: https://python-dotenv.readthedocs.io/

Project Files:
  - API Implementation: API_IMPLEMENTATION.md
  - Setup Guide: YNAB_SETUP.md
  - Summary: IMPLEMENTATION_SUMMARY.md
"""
