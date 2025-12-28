# Bank Transaction CSV Parser

Simple parser to convert transaction CSVs from multiple banks (OCBC, POSB) into a unified YNAB-compatible format.

## Overview

This project parses bank transaction CSVs and converts them to YNAB import format:

-   **Input:** CSV files from OCBC and POSB accounts
-   **Output:** Unified YNAB-format CSV with Date, Payee, Memo, Outflow, Inflow columns

## Quick Start

### Setup

Create and activate a virtual environment:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Run Parser

```zsh
python3 process_ynab.py
```

This parses all CSVs in `data/incoming/` and produces separate output files per bank:

-   `results/ocbc_MMDD-MMDD.csv` — OCBC transactions (date range format)
-   `results/posb_MMDD-MMDD.csv` — POSB transactions (date range format)

## Individual Bank Parsing

Parse a single bank's transactions:

```zsh
# OCBC
python3 parsers/csv-parser-ocbc.py data/incoming/ocbc/TransactionHistory_*.csv output.csv

# POSB
python3 parsers/csv-parser-posb.py data/incoming/posb/everyday-use/*.csv output.csv
```

## Bank Folder Structure

Place CSV files in these directories:

```
data/incoming/
  ocbc/           # OCBC CSVs
    TransactionHistory_*.csv
  posb/           # POSB CSVs
    everyday-use/
      *.csv
    my-savings/
      *.csv
```

The parsers automatically detect the bank type and apply the correct transformation.

## Output Format

The output CSV has these columns (YNAB compatible):

-   **Date** — DD/MM/YYYY format
-   **Payee** — Transaction description/merchant
-   **Memo** — Additional notes (optional)
-   **Outflow** — Amount paid out
-   **Inflow** — Amount received

## Output Files

-   **`results/ocbc_MMDD-MMDD.csv`** — OCBC transactions with date range (e.g., ocbc_1120-1215.csv for Nov 20 to Dec 15)
-   **`results/posb_MMDD-MMDD.csv`** — POSB transactions with date range (e.g., posb_1110-1220.csv for Nov 10 to Dec 20)

## Examples

### Parse all transactions

```zsh
source .venv/bin/activate
python3 process_ynab.py
ls results/*.csv
```

Output files:

```
results/ocbc_1120-1215.csv
results/posb_1110-1220.csv
```

**File format:**

```csv
Date,Payee,Memo,Outflow,Inflow
15/12/2025,DEBIT PURCHASE xx-8237 Grab* A-8NRGFPSGWWXTAV S,,17.30,
15/12/2025,DEBIT PURCHASE xx-1393 APPLE.COM/BILL 8,,13.98,
20/12/2025,PayNow Transfer 8234745,,2.50,
19/12/2025,FAIRPRICE XTRA-AMK SI SGP 17DEC,,2.60,
```

### Parse OCBC only

```zsh
source .venv/bin/activate
python3 parsers/csv-parser-ocbc.py data/incoming/ocbc/TransactionHistory_20251220200720.csv output.csv
```

### Parse POSB only

```zsh
source .venv/bin/activate
python3 parsers/csv-parser-posb.py data/incoming/posb/everyday-use/*.csv output.csv
```

## Deactivate Virtual Environment

When done:

```zsh
deactivate
```

## Dependencies

No external dependencies required. Uses only Python standard library.

## Troubleshooting

**Error: No transactions found**

-   Check that CSVs exist in `data/incoming/ocbc/` and `data/incoming/posb/`
-   Verify CSV format matches expected structure

**Date format issues**

-   OCBC input: DD/MM/YYYY (e.g., 15/12/2025)
-   POSB input: DD Mon YYYY (e.g., 20 Dec 2025)
-   Output format: DD/MM/YYYY (e.g., 15/12/2025)
