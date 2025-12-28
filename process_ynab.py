#!/usr/bin/env python3
"""
Simple transaction parsing script.

Usage:
  python3 process_ynab.py [--data-dir DIR]

Parses all bank transaction CSVs from data/incoming/ and saves results to
results/ directory with one file per bank (named: bank_MMDD-MMDD.csv).
"""
from __future__ import annotations

import argparse
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a subprocess command."""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, timeout=60)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Error: Command timed out: {' '.join(cmd)}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Parse transaction CSVs from all banks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 process_ynab.py
  python3 process_ynab.py --data-dir data

Output:
  Each bank gets its own file in results/:
  - results/ocbc_MMDD-MMDD.csv
  - results/posb_MMDD-MMDD.csv
        """,
    )
    p.add_argument("--data-dir", default="data", help="Data directory root")
    
    args = p.parse_args(argv or sys.argv[1:])
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Parse transactions
    if not run_command(
        ["python3", "transactions_parser.py", "--data-dir", args.data_dir],
        "Parse Transaction CSVs",
    ):
        print("Error: Failed to parse transactions", file=sys.stderr)
        return 1
    
    print(f"\n{'='*60}")
    print("✓ Parsing complete!")
    print(f"{'='*60}")
    print(f"Results saved to results/ directory")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
