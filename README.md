# YNAB Upload Helper

This app lets you upload bank files to YNAB through a simple local browser UI.

It supports:
- `CSV` bank statement uploads
- `OFX` uploads
- choosing your YNAB budget first
- choosing the exact YNAB account to upload into
- previewing transactions before upload

## What Happens To Your Files

- `CSV` uploads are reformatted before preview and upload:
  - `Payee` and `Memo` are swapped
- `OFX` uploads are passed through directly:
  - no payee/memo swap

## Requirements

- Python 3.8+
- A YNAB account
- A YNAB API token from [YNAB Developer Settings](https://app.ynab.com/settings/developer)

## Setup

### Option 1: Quick setup

```bash
./scripts/setup_venv.sh
source .venv/bin/activate
```

### Option 2: Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

## Configure The App

Copy the example config:

```bash
cp .env.example .env
```

Open `.env` and set at least:

```env
YNAB_API_TOKEN=your_token_here
```

`YNAB_BUDGET_ID` is optional for the browser UI, because the app will load your budgets and let you choose one.

## Run The Browser UI

```bash
python3 -m ynab_parser ui
```

Then open:

```text
http://127.0.0.1:8765
```

## How To Use It

1. Open the app in your browser.
2. Choose a budget.
3. Choose the YNAB account you want to upload into.
4. Upload a `CSV` or `OFX` file.
5. Review the preview.
6. Click `Review and Upload`.

## Supported Inputs

### CSV

Current CSV support is aimed at the formats already handled by this project:
- OCBC
- POSB / DBS

### OFX

OFX files are supported for direct upload through the browser UI.

## Troubleshooting

### Budgets or accounts do not load

Check that:
- your `YNAB_API_TOKEN` is set in `.env`
- the token is valid
- your internet connection is working

### The app says the file format is unsupported

Make sure the file is:
- a supported bank CSV
- or a valid `.ofx` file

### The server does not start

Try:

```bash
python3 -m ynab_parser ui --port 8766
```

If that works, something else is already using port `8765`.
