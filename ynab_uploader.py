#!/usr/bin/env python3
"""
Convert parsed transaction CSVs to YNAB format and post to YNAB API.

Usage:
  python3 ynab_uploader.py [--config .env] [--budget-id BUDGET_ID] [--dry-run]

Environment:
  .env file should contain:
    YNAB_API_TOKEN=your_token
    YNAB_BUDGET_ID=your_budget_id (optional)
    OCBC_DEFAULT=account_id
    POSB_EVERYDAY_USE=account_id
    POSB_MY_SAVINGS=account_id
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from ynab_api import YNABClient, Transaction, YNABAPIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Manage configuration from .env file and environment variables."""
    
    def __init__(self, env_file: str = ".env"):
        """Load configuration from .env file."""
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Loaded configuration from {env_file}")
        else:
            logger.warning(f"Configuration file not found: {env_file}")

    @staticmethod
    def get_api_token() -> str:
        """Get YNAB API token from environment."""
        token = os.getenv("YNAB_API_TOKEN", "").strip()
        if not token or token == "your_api_token_here":
            raise ValueError(
                "YNAB_API_TOKEN not configured. "
                "Please set it in .env file or environment."
            )
        return token

    @staticmethod
    def get_budget_id(override: Optional[str] = None) -> str:
        """Get YNAB budget ID."""
        if override:
            return override
        budget_id = os.getenv("YNAB_BUDGET_ID", "").strip()
        if not budget_id:
            raise ValueError(
                "YNAB_BUDGET_ID not configured. "
                "Please set it in .env file or use --budget-id flag."
            )
        return budget_id

    @staticmethod
    def get_account_mapping() -> Dict[str, str]:
        """Get mapping of CSV account names to YNAB account IDs."""
        mapping = {}
        
        # Standard account name mappings
        mapping_vars = {
            "OCBC_DEFAULT": "ocbc_default",
            "POSB_EVERYDAY_USE": "posb_everyday-use",
            "POSB_MY_SAVINGS": "posb_my-savings",
        }
        
        for env_var, account_name in mapping_vars.items():
            account_id = os.getenv(env_var, "").strip()
            if account_id and account_id != "":
                mapping[account_name] = account_id
        
        return mapping


class TransactionConverter:
    """Convert CSV transactions to YNAB API format."""
    
    # YNAB amounts are in millicents
    MILLICENTS_PER_UNIT = 1000
    
    def __init__(self, account_mapping: Dict[str, str]):
        """
        Initialize converter.
        
        Args:
            account_mapping: Map of CSV account names to YNAB account IDs
        """
        self.account_mapping = account_mapping

    def parse_amount(self, outflow: str, inflow: str) -> int:
        """
        Convert outflow/inflow to YNAB amount format.
        
        Args:
            outflow: Outflow amount as string (negative)
            inflow: Inflow amount as string (positive)
            
        Returns:
            Amount in millicents (positive for inflow, negative for outflow)
        """
        try:
            if outflow and outflow.strip():
                # Outflow is negative
                amount = -float(outflow.replace(",", ""))
            elif inflow and inflow.strip():
                # Inflow is positive
                amount = float(inflow.replace(",", ""))
            else:
                return 0
            
            # Convert to millicents
            return int(amount * self.MILLICENTS_PER_UNIT)
        except ValueError:
            logger.warning(f"Failed to parse amount: outflow={outflow}, inflow={inflow}")
            return 0

    def parse_date(self, date_str: str) -> str:
        """
        Convert DD/MM/YYYY to YYYY-MM-DD format.
        
        Args:
            date_str: Date as DD/MM/YYYY
            
        Returns:
            Date as YYYY-MM-DD
        """
        try:
            parts = date_str.split("/")
            if len(parts) == 3:
                day, month, year = parts
                return f"{year}-{month}-{day}"
        except Exception:
            pass
        
        logger.warning(f"Failed to parse date: {date_str}")
        return date_str

    def csv_row_to_transaction(
        self,
        row: Dict[str, str],
        account_id: str,
    ) -> Optional[Transaction]:
        """
        Convert CSV row to Transaction object.
        
        Args:
            row: CSV row as dictionary
            account_id: YNAB account ID
            
        Returns:
            Transaction object or None if conversion fails
        """
        try:
            date = self.parse_date(row.get("Date", ""))
            if not date:
                logger.warning(f"Skipping transaction with invalid date: {row}")
                return None
            
            amount = self.parse_amount(
                row.get("Outflow", ""),
                row.get("Inflow", "")
            )
            
            if amount == 0:
                logger.debug(f"Skipping zero-amount transaction: {row}")
                return None
            
            payee_name = row.get("Payee", "").strip() or None
            memo = row.get("Memo", "").strip() or None
            
            return Transaction(
                account_id=account_id,
                date=date,
                amount=amount,
                memo=payee_name,
                cleared="cleared",
                approved=True,
            )
        except Exception as e:
            logger.error(f"Failed to convert CSV row: {row}, error: {e}")
            return None


class TransactionUploader:
    """Upload transactions to YNAB."""
    
    def __init__(
        self,
        client: YNABClient,
        budget_id: str,
        dry_run: bool = False,
    ):
        """
        Initialize uploader.
        
        Args:
            client: YNABClient instance
            budget_id: Budget ID
            dry_run: If True, don't actually post transactions
        """
        self.client = client
        self.budget_id = budget_id
        self.dry_run = dry_run

    def read_csv_transactions(
        self,
        csv_path: str,
        account_id: str,
        converter: TransactionConverter,
    ) -> List[Transaction]:
        """
        Read transactions from CSV file.
        
        Args:
            csv_path: Path to CSV file
            account_id: YNAB account ID for these transactions
            converter: TransactionConverter instance
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row or not any(row.values()):
                        continue
                    
                    tx = converter.csv_row_to_transaction(row, account_id)
                    if tx:
                        transactions.append(tx)
        except Exception as e:
            logger.error(f"Failed to read CSV {csv_path}: {e}")
            return []
        
        return transactions

    def upload_transactions(
        self,
        csv_path: str,
        account_id: str,
        converter: TransactionConverter,
    ) -> Dict[str, int]:
        """
        Upload transactions from a CSV file to YNAB.
        
        Args:
            csv_path: Path to CSV file
            account_id: YNAB account ID
            converter: TransactionConverter instance
            
        Returns:
            Dictionary with upload stats
        """
        stats = {
            "total": 0,
            "uploaded": 0,
            "skipped": 0,
            "errors": 0,
        }
        
        transactions = self.read_csv_transactions(csv_path, account_id, converter)
        stats["total"] = len(transactions)
        
        if not transactions:
            logger.info(f"No transactions to upload from {csv_path}")
            return stats
        
        logger.info(f"Uploading {len(transactions)} transactions from {csv_path}")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would post transactions:")
            for tx in transactions[:5]:  # Show first 5
                logger.info(f"  - {tx.date}: {tx.payee_name} {tx.amount}¢")
            if len(transactions) > 5:
                logger.info(f"  ... and {len(transactions) - 5} more")
            stats["uploaded"] = len(transactions)
            return stats
        
        try:
            result = self.client.create_transactions(
                budget_id=self.budget_id,
                transactions=transactions,
            )
            stats["uploaded"] = len(transactions)
            logger.info(f"Successfully uploaded {len(transactions)} transactions")
            return stats
        except YNABAPIError as e:
            logger.error(f"Failed to upload transactions: {e}")
            stats["errors"] = len(transactions)
            return stats

    def upload_all_results(
        self,
        results_dir: str,
        account_mapping: Dict[str, str],
    ) -> Dict[str, Dict]:
        """
        Upload all CSV files from results directory.
        
        Args:
            results_dir: Path to results directory
            account_mapping: Map of CSV account names to YNAB account IDs
            
        Returns:
            Dictionary with upload stats per file
        """
        converter = TransactionConverter(account_mapping)
        all_stats = {}
        
        results_path = Path(results_dir)
        if not results_path.exists():
            logger.error(f"Results directory not found: {results_dir}")
            return all_stats
        
        csv_files = sorted(results_path.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CSV files found in {results_dir}")
            return all_stats
        
        for csv_file in csv_files:
            file_name = csv_file.name
            
            # Extract account identifier from filename (e.g., "ocbc_default" from "ocbc_default_12-2025_01-2026.csv")
            account_key = "_".join(file_name.split("_")[:-2]).lower()
            
            account_id = account_mapping.get(account_key)
            if not account_id:
                logger.warning(f"No account ID configured for {account_key}")
                all_stats[file_name] = {"error": "No account ID configured"}
                continue
            
            logger.info(f"\nProcessing {file_name}...")
            stats = self.upload_transactions(str(csv_file), account_id, converter)
            all_stats[file_name] = stats
        
        return all_stats


def print_summary(all_stats: Dict[str, Dict]) -> int:
    """
    Print upload summary.
    
    Returns:
        Exit code (0 if all successful, 1 otherwise)
    """
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    
    total_uploaded = 0
    total_errors = 0
    
    for file_name, stats in all_stats.items():
        if "error" in stats:
            print(f"✗ {file_name}: {stats['error']}")
            total_errors += 1
        else:
            uploaded = stats.get("uploaded", 0)
            total = stats.get("total", 0)
            status = "✓" if uploaded == total else "⚠"
            print(f"{status} {file_name}: {uploaded}/{total} uploaded")
            total_uploaded += uploaded
    
    print("=" * 60)
    print(f"Total uploaded: {total_uploaded}")
    
    return 0 if total_errors == 0 else 1


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Upload parsed transactions to YNAB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 ynab_uploader.py --config .env --budget-id my_budget_id
  python3 ynab_uploader.py --dry-run  # Preview without posting
        """,
    )
    p.add_argument(
        "--config",
        default=".env",
        help="Configuration file (default: .env)"
    )
    p.add_argument(
        "--budget-id",
        help="YNAB budget ID (overrides .env)"
    )
    p.add_argument(
        "--results-dir",
        default="results",
        help="Directory containing result CSVs (default: results)"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview upload without posting to YNAB"
    )
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    
    try:
        # Load configuration
        config = ConfigManager(args.config)
        api_token = config.get_api_token()
        budget_id = config.get_budget_id(args.budget_id)
        account_mapping = config.get_account_mapping()
        
        if not account_mapping:
            logger.error("No account mappings configured. Check .env file.")
            return 1
        
        # Create client and uploader
        with YNABClient(api_token) as client:
            uploader = TransactionUploader(
                client=client,
                budget_id=budget_id,
                dry_run=args.dry_run,
            )
            
            # Upload transactions
            all_stats = uploader.upload_all_results(args.results_dir, account_mapping)
            
            # Print summary
            return print_summary(all_stats)
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except YNABAPIError as e:
        logger.error(f"API error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
