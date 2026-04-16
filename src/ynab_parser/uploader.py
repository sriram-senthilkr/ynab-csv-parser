"""
Transaction uploader to YNAB.

Handles reading CSV files, converting transactions, and uploading to YNAB.
"""

import csv
from typing import Dict, List, Optional
from pathlib import Path
import logging

from .core.models import Transaction, CSVRow
from .core.api import YNABClient
from .core.exceptions import APIError, ValidationError, ParserError
from .converter import TransactionConverter, TransactionFilter

logger = logging.getLogger(__name__)


class TransactionUploader:
    """Upload transactions from CSV files to YNAB."""

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
            budget_id: YNAB budget ID
            dry_run: If True, don't post transactions
        """
        self.client = client
        self.budget_id = budget_id
        self.dry_run = dry_run

    def upload_from_csv(
        self,
        csv_path: str,
        account_id: str,
        account_key: str,
        account_mapping: Dict[str, str],
    ) -> Dict[str, int]:
        """
        Upload transactions from a CSV file.

        Args:
            csv_path: Path to CSV file
            account_id: YNAB account ID (for logging)
            account_key: Account key for mapping
            account_mapping: Account ID mapping

        Returns:
            Upload statistics
        """
        stats = {
            "total": 0,
            "uploaded": 0,
            "skipped": 0,
            "errors": 0,
        }

        try:
            # Read CSV
            transactions = self._read_csv_transactions(
                csv_path,
                account_key,
                account_mapping,
            )
            stats["total"] = len(transactions)

            if not transactions:
                logger.info(f"No valid transactions to upload from {csv_path}")
                return stats

            logger.info(f"Uploading {len(transactions)} transactions from {Path(csv_path).name}")

            if self.dry_run:
                logger.info("[DRY RUN] Would upload:")
                for tx in transactions[:5]:
                    logger.info(f"  {tx.to_display()}")
                if len(transactions) > 5:
                    logger.info(f"  ... and {len(transactions) - 5} more")
                stats["uploaded"] = len(transactions)
                return stats

            # Upload to YNAB
            result = self.client.create_transactions(
                budget_id=self.budget_id,
                transactions=transactions,
            )
            stats["uploaded"] = len(transactions)
            logger.info(f"✓ Successfully uploaded {len(transactions)} transactions")

            return stats

        except APIError as e:
            logger.error(f"Failed to upload transactions: {e}")
            stats["errors"] = stats["total"]
            return stats
        except Exception as e:
            logger.error(f"Unexpected error uploading transactions: {e}", exc_info=True)
            stats["errors"] = stats["total"]
            return stats

    def _read_csv_transactions(
        self,
        csv_path: str,
        account_key: str,
        account_mapping: Dict[str, str],
    ) -> List[Transaction]:
        """
        Read and convert transactions from CSV file.

        Args:
            csv_path: Path to CSV file
            account_key: Account key for mapping
            account_mapping: Account ID mapping

        Returns:
            List of Transaction objects
        """
        transactions = []
        converter = TransactionConverter(account_mapping)

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row or not any(row.values()):
                        continue

                    # Convert row to CSVRow
                    csv_row = CSVRow(
                        date=row.get("Date", ""),
                        payee=row.get("Payee", ""),
                        memo=row.get("Memo", ""),
                        outflow=row.get("Outflow"),
                        inflow=row.get("Inflow"),
                    )

                    # Convert to Transaction
                    try:
                        tx = converter.csv_to_transaction(csv_row, account_key)
                        if tx and TransactionFilter.is_valid(tx):
                            transactions.append(tx)
                    except ValidationError as e:
                        logger.warning(f"Skipping invalid transaction: {e}")
                        continue

        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read CSV {csv_path}: {e}")
            raise

        return transactions

    def upload_all(
        self,
        results_dir: str,
        account_mapping: Dict[str, str],
    ) -> Dict[str, Dict[str, int]]:
        """
        Upload all CSV files from results directory.

        Args:
            results_dir: Path to results directory
            account_mapping: Account ID mapping

        Returns:
            Upload statistics per file
        """
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

            # Extract account key from filename
            # Format: bank_account_daterange.csv (e.g., ocbc_default_12-2025_01-2026.csv)
            parts = file_name.replace(".csv", "").split("_")
            if len(parts) >= 4:
                account_key = "_".join(parts[:-2]).lower()
            else:
                account_key = file_name.replace(".csv", "").lower()

            account_id = account_mapping.get(account_key)
            if not account_id:
                logger.warning(f"No account ID configured for {account_key} in {file_name}")
                all_stats[file_name] = {"skipped": True, "reason": "No account ID configured"}
                continue

            logger.info(f"\nProcessing {file_name}...")
            stats = self.upload_from_csv(
                str(csv_file),
                account_id,
                account_key,
                account_mapping,
            )
            all_stats[file_name] = stats

        return all_stats
