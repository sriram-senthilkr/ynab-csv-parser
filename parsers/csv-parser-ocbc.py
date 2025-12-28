#!/usr/bin/env python3
"""
Simple OCBC Transaction History -> YNAB CSV converter

Usage:
  python csv-parser-ocbc.py input.csv output.csv

If no files are provided, it will read `TransactionHistory_20251220200720.csv`
in the current directory and write `ynab_import.csv`.

Output format: Date,Payee,Memo,Outflow,Inflow (Date in MM/DD/YYYY)
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from typing import Iterable


def find_transactions(reader: Iterable[Iterable[str]]):
    """Yield dict rows after locating the header row starting with 'Transaction date'."""
    header = None
    for row in reader:
        if not row:
            continue
        first = row[0].strip() if len(row) > 0 else ""
        if first == "Transaction date":
            header = [c.strip() for c in row]
            break
    if header is None:
        return
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        # map header to row values (some rows may be shorter)
        d = {h: (row[i] if i < len(row) else "") for i, h in enumerate(header)}
        yield d


def clean_description(desc: str) -> str:
    if desc is None:
        return ""
    # collapse whitespace and replace newlines with space
    s = re.sub(r"\s+", " ", desc).strip()
    # remove repeating trailing dates like 13/12/25
    s = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", s).strip()
    # remove long runs of non-word separators
    s = re.sub(r"[-]{2,}", "", s)
    return s


def parse_date(d: str) -> str:
    """Convert DD/MM/YYYY (or D/M/YYYY) to DD/MM/YYYY; leave if parsing fails."""
    d = (d or "").strip()
    if not d:
        return ""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            dt = datetime.strptime(d, fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            continue
    # fallback: try splitting
    parts = d.split("/")
    if len(parts) == 3:
        day, month, year = parts
        if len(year) == 2:
            year = "20" + year
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    return d


def format_amount(a: str) -> str:
    a = (a or "").strip()
    if not a:
        return ""
    # remove thousands separators and stray currency
    a = a.replace(",", "")
    a = re.sub(r"[^0-9.\-]", "", a)
    try:
        val = float(a)
    except Exception:
        return ""
    return f"{val:.2f}"


def convert(inpath: str, outpath: str) -> None:
    with open(inpath, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = list(find_transactions(reader))

    with open(outpath, "w", newline="", encoding="utf-8") as outfh:
        writer = csv.writer(outfh)
        writer.writerow(["Date", "Payee", "Memo", "Outflow", "Inflow"])
        for d in rows:
            tdate = d.get("Transaction date", "")
            value_date = d.get("Value date", "")
            # prefer value date if available
            date = value_date or tdate
            date = parse_date(date)

            desc = clean_description(d.get("Description", ""))
            payee = desc
            memo = ""

            outflow_raw = d.get("Withdrawals(SGD)", "")
            inflow_raw = d.get("Deposits(SGD)", "")
            outflow = format_amount(outflow_raw)
            inflow = format_amount(inflow_raw)

            # YNAB expects positive numbers; Outflow column should have the amount paid (no sign)
            if outflow and outflow != "0.00":
                writer.writerow([date, payee, memo, outflow, ""])
            elif inflow and inflow != "0.00":
                writer.writerow([date, payee, memo, "", inflow])
            else:
                # skip empty-amount rows
                continue


def main():
    p = argparse.ArgumentParser(description="Convert OCBC transaction history CSV to YNAB import CSV")
    p.add_argument("input", nargs="?", default="TransactionHistory_20251220200720.csv")
    p.add_argument("output", nargs="?", default="ynab_import.csv")
    args = p.parse_args()
    convert(args.input, args.output)
    print(f"Wrote YNAB CSV to {args.output}")


if __name__ == "__main__":
    main()
