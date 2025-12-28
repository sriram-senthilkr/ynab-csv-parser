#!/usr/bin/env python3
"""
Parse transaction CSVs from all banks and combine into a single results file.

Usage:
  python3 transactions_parser.py [--output FILE] [--data-dir DIR]

Scans data/incoming/{ocbc,posb,citi,maribank,paylah} for CSVs and parses them
using the appropriate parser. Outputs unified YNAB-format CSV.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import subprocess
from pathlib import Path
from typing import List


def find_csv_files(data_dir: str) -> List[dict]:
    """Find all CSV files in bank folders."""
    files = []
    base = Path(data_dir) / "incoming"
    
    # Map of bank name to parser script
    parsers = {
        "ocbc": "parsers/csv-parser-ocbc.py",
        "posb": "parsers/csv-parser-posb.py",
    }
    
    for bank, parser in parsers.items():
        bank_dir = base / bank
        if not bank_dir.exists():
            continue

        # Recursively find all CSVs in bank folder
        for csv_file in bank_dir.rglob("*.csv"):
            # Determine account name by the first-level subdirectory under the bank folder.
            try:
                rel_parent = csv_file.parent.relative_to(bank_dir)
                # If file is directly under bank dir, use 'default' as account name
                account = str(rel_parent).split(os.sep)[0] if str(rel_parent) not in (".", "") else "default"
                if account == "":
                    account = "default"
            except Exception:
                account = "default"

            files.append({
                "bank": bank,
                "account": account,
                "path": str(csv_file),
                "parser": parser,
            })
    
    return files


def parse_csv_with_parser(csv_path: str, parser_script: str, temp_output: str) -> bool:
    """Run parser script on CSV file."""
    try:
        result = subprocess.run(
            ["python3", parser_script, csv_path, temp_output],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running parser for {csv_path}: {e}", file=sys.stderr)
        return False


def read_ynab_csv(filepath: str) -> List[dict]:
    """Read YNAB-format CSV and return list of transaction dicts."""
    transactions = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row:
                    transactions.append(row)
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return transactions


def parse_date_value(date_str: str) -> tuple[int, int, int]:
    """Convert DD/MM/YYYY to (year, month, day) tuple for comparison."""
    try:
        parts = date_str.split("/")
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return (year, month, day)
    except Exception:
        pass
    return (9999, 12, 31)  # fallback


def get_date_range(transactions: List[dict]) -> str:
    """Extract date range from transactions (oldest to newest)."""
    if not transactions:
        return ""
    
    dates = [parse_date_value(tx.get("Date", "")) for tx in transactions]
    dates.sort()
    
    if len(dates) >= 2:
        # Format requested: MM-YYYY_MM-YYYY (month-first then year)
        oldest = dates[0]
        newest = dates[-1]
        oldest_str = f"{oldest[1]:02d}-{oldest[0]}"  # MM-YYYY
        newest_str = f"{newest[1]:02d}-{newest[0]}"  # MM-YYYY
        return f"{oldest_str}_{newest_str}"
    elif len(dates) == 1:
        date = dates[0]
        date_str = f"{date[1]:02d}-{date[0]}"  # MM-YYYY
        return date_str
    
    return ""


def parse_all_transactions(data_dir: str) -> dict:
    """Parse all bank CSVs and return grouped by (bank, account)."""
    csv_files = find_csv_files(data_dir)
    bank_transactions: dict[tuple[str, str], list] = {}  # (bank, account) -> list of transactions

    for info in csv_files:
        bank = info.get("bank")
        account = info.get("account", "default")
        print(f"Parsing {bank}/{account} CSV: {info['path']}")
        temp_output = "/tmp/ynab_temp.csv"

        if parse_csv_with_parser(info["path"], info["parser"], temp_output):
            transactions = read_ynab_csv(temp_output)
            key = (bank, account)
            if key not in bank_transactions:
                bank_transactions[key] = []
            bank_transactions[key].extend(transactions)
            print(f"  → {len(transactions)} transactions")
        else:
            print(f"  → Failed to parse", file=sys.stderr)

    return bank_transactions


def save_bank_transactions(bank_transactions: dict, output_dir: str) -> None:
    """Save transactions grouped by (bank, account), one file per account."""
    if not bank_transactions:
        print("No transactions to save.", file=sys.stderr)
        return

    fieldnames = ["Date", "Payee", "Memo", "Outflow", "Inflow"]

    for (bank, account), transactions in bank_transactions.items():
        date_range = get_date_range(transactions)
        # Sanitize account for filename
        safe_account = account.replace(" ", "_").replace(os.sep, "_")
        safe_account = "default" if not safe_account else safe_account
        filename = f"{bank}_{safe_account}_{date_range}.csv" if date_range else f"{bank}_{safe_account}.csv"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
            writer.writeheader()
            for tx in transactions:
                writer.writerow({k: tx.get(k, "") for k in fieldnames})

        print(f"Saved {len(transactions)} {bank.upper()}/{account} transactions to {filepath}")


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse all bank transaction CSVs")
    p.add_argument("--output", default="results/parsed_transactions.csv", help="Output CSV file")
    p.add_argument("--data-dir", default="data", help="Data directory root")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    
    # Create output directory if needed
    output_dir = os.path.dirname(args.output) or "results"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    bank_transactions = parse_all_transactions(args.data_dir)
    save_bank_transactions(bank_transactions, output_dir)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
