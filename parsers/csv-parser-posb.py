#!/usr/bin/env python3
"""
Simple POSB Transaction History -> YNAB CSV converter

Usage:
  python csv-parser-posb.py input.csv output.csv

If no files are provided, it will read from a default POSB CSV in the current directory
and write `ynab_import.csv`.

Output format: Date,Payee,Memo,Outflow,Inflow (Date in MM/DD/YYYY)
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from typing import Iterable


def find_transactions(reader: Iterable[Iterable[str]]):
    """Yield dict rows after locating the header row starting with 'Transaction Date'."""
    header = None
    for row in reader:
        if not row:
            continue
        first = row[0].strip() if len(row) > 0 else ""
        if first == "Transaction Date":
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
    # remove long runs of non-word separators
    s = re.sub(r"[-]{2,}", "", s)
    return s


def parse_date(d: str) -> str:
    """Convert 'DD Mon YYYY' (e.g., '20 Dec 2025') to DD/MM/YYYY."""
    d = (d or "").strip()
    if not d:
        return ""
    try:
        dt = datetime.strptime(d, "%d %b %Y")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    # try alternate formats
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(d, fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            continue
    return d


def format_amount(a: str) -> str:
    a = (a or "").strip()
    if not a:
        return ""
    # remove whitespace, thousands separators and stray currency
    a = a.replace(" ", "").replace(",", "")
    a = re.sub(r"[^0-9.\-]", "", a)
    try:
        val = float(a)
    except Exception:
        return ""
    return f"{abs(val):.2f}"


def convert(inpath: str, outpath: str) -> None:
    with open(inpath, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = list(find_transactions(reader))

    with open(outpath, "w", newline="", encoding="utf-8") as outfh:
        writer = csv.writer(outfh)
        writer.writerow(["Date", "Payee", "Memo", "Outflow", "Inflow"])
        for d in rows:
            date = parse_date(d.get("Transaction Date", ""))

            # Build payee from Reference and Transaction Ref1
            ref = clean_description(d.get("Reference", ""))
            ref1 = clean_description(d.get("Transaction Ref1", ""))
            payee = ref1 if ref1 else ref
            payee = payee[:100] if payee else "Unknown"
            memo = ""

            debit_raw = d.get("Debit Amount", "")
            credit_raw = d.get("Credit Amount", "")
            debit = format_amount(debit_raw)
            credit = format_amount(credit_raw)

            # YNAB expects positive numbers; Outflow column should have the amount paid
            if debit and debit != "0.00":
                writer.writerow([date, payee, memo, debit, ""])
            elif credit and credit != "0.00":
                writer.writerow([date, payee, memo, "", credit])
            else:
                # skip empty-amount rows
                continue


def main():
    p = argparse.ArgumentParser(description="Convert POSB transaction history CSV to YNAB import CSV")
    p.add_argument("input", nargs="?", default="posb_transactions.csv")
    p.add_argument("output", nargs="?", default="ynab_import.csv")
    args = p.parse_args()
    convert(args.input, args.output)
    print(f"Wrote YNAB CSV to {args.output}")


if __name__ == "__main__":
    main()
