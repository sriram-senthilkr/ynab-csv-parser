"""
Transaction processing pipeline.

Orchestrates CSV parsing and normalization workflow.
"""

import csv
import subprocess
from typing import Dict, List, Tuple
from pathlib import Path
import tempfile
import logging

from .parsers import ParserFactory
from .core.models import CSVRow
from .core.exceptions import ParserError

logger = logging.getLogger(__name__)


class TransactionProcessor:
    """Process and normalize transactions from multiple bank CSV files."""

    # Standard output columns for YNAB format
    OUTPUT_COLUMNS = ["Date", "Payee", "Memo", "Outflow", "Inflow"]

    @staticmethod
    def find_csv_files(data_dir: str) -> List[Dict[str, str]]:
        """
        Find all bank CSV files in data directory.

        Args:
            data_dir: Root data directory

        Returns:
            List of file info dicts with keys: bank, account, path
        """
        files = []
        base = Path(data_dir) / "incoming"

        if not base.exists():
            logger.warning(f"Data directory not found: {base}")
            return files

        # Scan for bank directories
        for bank_dir in base.iterdir():
            if not bank_dir.is_dir():
                continue

            bank_name = bank_dir.name.lower()

            # Find all CSVs in bank directory
            for csv_file in bank_dir.rglob("*.csv"):
                # Determine account from subdirectory
                try:
                    rel_path = csv_file.parent.relative_to(bank_dir)
                    account = str(rel_path).split(Path.cwd())[0] or "default"
                    # Get first-level subdirectory as account name
                    parts = str(rel_path).split("/")
                    account = parts[0] if parts[0] and parts[0] != "." else "default"
                except Exception:
                    account = "default"

                files.append({
                    "bank": bank_name,
                    "account": account,
                    "path": str(csv_file),
                })

        logger.info(f"Found {len(files)} CSV file(s)")
        return files

    @staticmethod
    def parse_csv_file(
        file_path: str,
        bank: str,
    ) -> List[CSVRow]:
        """
        Parse a single CSV file using appropriate parser.

        Args:
            file_path: Path to CSV file
            bank: Bank identifier

        Returns:
            List of CSVRow objects

        Raises:
            ParserError: If parsing fails
        """
        try:
            parser = ParserFactory.get_parser(bank)
            return parser.parse_file(file_path)
        except ParserError:
            raise
        except Exception as e:
            raise ParserError(
                message=f"Failed to parse {bank} CSV",
                error_code="PARSE_FAILED",
                details={"file": file_path, "bank": bank},
            )

    @staticmethod
    def parse_all_transactions(data_dir: str) -> Dict[Tuple[str, str], List[CSVRow]]:
        """
        Parse all bank CSVs and group by (bank, account).

        Args:
            data_dir: Data directory root

        Returns:
            Dictionary mapping (bank, account) to list of CSVRow objects
        """
        csv_files = TransactionProcessor.find_csv_files(data_dir)
        grouped_transactions = {}

        for file_info in csv_files:
            bank = file_info["bank"]
            account = file_info["account"]
            path = file_info["path"]

            logger.info(f"Parsing {bank}/{account}: {Path(path).name}")

            try:
                transactions = TransactionProcessor.parse_csv_file(path, bank)
                key = (bank, account)

                if key not in grouped_transactions:
                    grouped_transactions[key] = []

                grouped_transactions[key].extend(transactions)
                logger.info(f"  ✓ {len(transactions)} transaction(s)")

            except ParserError as e:
                logger.error(f"  ✗ Failed to parse: {e}")
                continue

        return grouped_transactions

    @staticmethod
    def save_transactions(
        grouped_transactions: Dict[Tuple[str, str], List[CSVRow]],
        output_dir: str,
    ) -> List[str]:
        """
        Save transactions grouped by (bank, account) to CSV files.

        Args:
            grouped_transactions: Grouped transaction data
            output_dir: Output directory

        Returns:
            List of saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []

        for (bank, account), transactions in grouped_transactions.items():
            if not transactions:
                continue

            # Generate filename with date range
            date_range = TransactionProcessor._get_date_range(transactions)
            safe_account = account.replace(" ", "_").replace("/", "_")
            safe_account = safe_account or "default"

            if date_range:
                filename = f"{bank}_{safe_account}_{date_range}.csv"
            else:
                filename = f"{bank}_{safe_account}.csv"

            filepath = output_path / filename

            # Write CSV
            try:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=TransactionProcessor.OUTPUT_COLUMNS,
                        restval="",
                    )
                    writer.writeheader()

                    for tx in transactions:
                        row = {
                            "Date": tx.date,
                            "Payee": tx.payee,
                            "Memo": tx.memo,
                            "Outflow": tx.outflow or "",
                            "Inflow": tx.inflow or "",
                        }
                        writer.writerow(row)

                saved_files.append(str(filepath))
                logger.info(
                    f"Saved {len(transactions)} {bank.upper()}/{account} "
                    f"transaction(s) to {filename}"
                )

            except Exception as e:
                logger.error(f"Failed to save {filename}: {e}")

        return saved_files

    @staticmethod
    def _get_date_range(transactions: List[CSVRow]) -> str:
        """
        Extract date range from transactions.

        Args:
            transactions: List of transactions

        Returns:
            Date range as MM-YYYY_MM-YYYY or empty string
        """
        if not transactions:
            return ""

        def parse_date(date_str: str) -> Tuple[int, int, int]:
            """Parse MM/DD/YYYY to (year, month, day)."""
            try:
                parts = date_str.split("/")
                if len(parts) == 3:
                    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                    return (year, month, day)
            except Exception:
                pass
            return (9999, 12, 31)

        dates = [parse_date(tx.date) for tx in transactions]
        dates.sort()

        if len(dates) >= 2:
            oldest = dates[0]
            newest = dates[-1]
            oldest_str = f"{oldest[1]:02d}-{oldest[0]}"
            newest_str = f"{newest[1]:02d}-{newest[0]}"
            return f"{oldest_str}_{newest_str}"
        elif len(dates) == 1:
            date = dates[0]
            return f"{date[1]:02d}-{date[0]}"

        return ""
