"""
Transaction processing and conversion utilities.

Handles conversion from CSV format to YNAB API format.
"""

from typing import Dict, List, Optional
import logging

from .core.models import Transaction, CSVRow
from .core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TransactionConverter:
    """Convert CSV transactions to YNAB API format."""

    # YNAB amounts are in millicents (1/1000th of a cent)
    MILLICENTS_PER_UNIT = 1000

    def __init__(self, account_mapping: Dict[str, str]):
        """
        Initialize converter.

        Args:
            account_mapping: Map of CSV account names to YNAB account IDs
        """
        self.account_mapping = account_mapping

    def csv_to_transaction(
        self,
        csv_row: CSVRow,
        account_key: str,
    ) -> Optional[Transaction]:
        """
        Convert CSV row to Transaction object.

        Args:
            csv_row: CSVRow object
            account_key: Account identifier for mapping

        Returns:
            Transaction object or None if conversion fails

        Raises:
            ValidationError: If data validation fails
        """
        try:
            # Get account ID from mapping
            account_id = self.account_mapping.get(account_key)
            if not account_id:
                logger.warning(f"No account ID mapped for {account_key}")
                return None

            return self.csv_to_transaction_for_account(csv_row, account_id)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to convert CSV row: {csv_row}, error: {e}")
            return None

    def csv_to_transaction_for_account(
        self,
        csv_row: CSVRow,
        account_id: str,
    ) -> Optional[Transaction]:
        """Convert a CSV row to a transaction for an explicit YNAB account ID."""
        try:
            # Parse amounts
            amount = self._parse_amounts(csv_row.outflow, csv_row.inflow)
            if amount == 0:
                logger.debug(f"Skipping zero-amount transaction: {csv_row}")
                return None

            # Create transaction
            transaction = Transaction(
                account_id=account_id,
                date=self._parse_date(csv_row.date),
                amount=amount,
                payee_name=csv_row.payee or None,
                memo=csv_row.memo or None,
                cleared="cleared",
                approved=True,
            )

            # Validate
            transaction.validate()

            return transaction

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to convert CSV row: {csv_row}, error: {e}")
            return None

    @staticmethod
    def _parse_amounts(outflow: Optional[str], inflow: Optional[str]) -> int:
        """
        Convert outflow/inflow to YNAB amount in millicents.

        Args:
            outflow: Outflow amount as string (expense)
            inflow: Inflow amount as string (income)

        Returns:
            Amount in millicents
        """
        try:
            if outflow and outflow.strip():
                # Outflow is negative (expense)
                amount = -float(outflow.replace(",", ""))
            elif inflow and inflow.strip():
                # Inflow is positive (income)
                amount = float(inflow.replace(",", ""))
            else:
                return 0

            # Convert to millicents
            return int(amount * TransactionConverter.MILLICENTS_PER_UNIT)

        except (ValueError, AttributeError):
            logger.warning(
                f"Failed to parse amounts: outflow={outflow}, inflow={inflow}"
            )
            return 0

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """
        Convert common CSV date formats to YYYY-MM-DD format.

        Args:
            date_str: Date as MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD

        Returns:
            Date as YYYY-MM-DD
        """
        from datetime import datetime

        value = (date_str or "").strip()
        if not value:
            logger.warning("Failed to parse date: empty value")
            return date_str

        for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        logger.warning(f"Failed to parse date: {date_str}")
        return date_str


class TransactionFilter:
    """Filter and validate transactions."""

    @staticmethod
    def is_duplicate(
        transaction: Transaction,
        existing: List[Transaction],
    ) -> bool:
        """
        Check if transaction is a duplicate.

        Args:
            transaction: Transaction to check
            existing: List of existing transactions

        Returns:
            True if duplicate found
        """
        for existing_tx in existing:
            if (
                existing_tx.date == transaction.date
                and existing_tx.amount == transaction.amount
                and existing_tx.payee_name == transaction.payee_name
                and existing_tx.account_id == transaction.account_id
            ):
                return True
        return False

    @staticmethod
    def is_valid(transaction: Transaction) -> bool:
        """
        Validate transaction data.

        Args:
            transaction: Transaction to validate

        Returns:
            True if valid
        """
        try:
            transaction.validate()
            return True
        except ValidationError:
            return False
